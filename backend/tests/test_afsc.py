import pytest
from sqlalchemy.orm import Session

from app.afsc import get_afsc_engine
from app.afsc.matcher import afsc_pattern_to_sql_like
from app.afsc.parser import parse_member_afsc, validate_search_pattern
from app.afsc.resolver import resolve
from app.db.repositories.roster import RosterRepository
from app.enums import PersonnelType
from app.exceptions import AfscResolutionError, AfscValidationError
from app.services.member_service import MemberService


def test_search_validation():
    assert validate_search_pattern("1A") == "1A"
    assert validate_search_pattern("1A1XX") == "1A1XX"
    with pytest.raises(AfscValidationError):
        validate_search_pattern("")
    with pytest.raises(AfscValidationError):
        validate_search_pattern("1X")
    with pytest.raises(AfscValidationError):
        validate_search_pattern("XX")


def test_member_validation():
    assert parse_member_afsc("1A152D").normalized == "1A152D"
    assert parse_member_afsc("11M3K").personnel_type == PersonnelType.OFFICER
    with pytest.raises(AfscValidationError):
        parse_member_afsc("1A1X2")
    with pytest.raises(AfscValidationError):
        parse_member_afsc("11MK")


def test_resolve_examples():
    resolved = resolve("1A152D")
    assert resolved.level == "Journeyman"
    assert resolved.specialization == "C-130J Loadmaster"
    assert "Mobility Force Aviator Journeyman" in resolved.full_label
    assert resolved.personnel_type == PersonnelType.ENLISTED

    assert resolve("11MX").personnel_type == PersonnelType.OFFICER
    assert resolve("1A1X2").personnel_type == PersonnelType.ENLISTED

    shorthand = resolve("11MK")
    assert shorthand.canonical_code == "11MXK"
    assert shorthand.specialization == "C-17"
    assert shorthand.family_title == "Mobility Pilot"

    with pytest.raises(AfscResolutionError, match="Ambiguous"):
        resolve("1A1XX")
    with pytest.raises(AfscResolutionError, match="Ambiguous"):
        resolve("11XX")


def test_sql_like_pattern_mapping():
    assert afsc_pattern_to_sql_like("1A1XX") == "1A1__%"
    assert afsc_pattern_to_sql_like("1A152D") == "1A152D%"
    assert afsc_pattern_to_sql_like("11MX") == "11M_%"
    with pytest.raises(AfscValidationError):
        afsc_pattern_to_sql_like("1X")


def test_member_search_uses_sql_like_patterns(db: Session):
    repo = RosterRepository(db)
    upload = repo.create_pending(filename="r.xlsx", ruleset_version="v1")
    for dodid, name, ptype, code in [
        ("1", "Loadmaster", PersonnelType.ENLISTED, "1A112G"),
        ("2", "Loadmaster2", PersonnelType.ENLISTED, "1A112"),
        ("3", "Special", PersonnelType.ENLISTED, "1A152D"),
        ("4", "Pilot", PersonnelType.OFFICER, "11M3K"),
        ("5", "Other", PersonnelType.OFFICER, "11S3F"),
    ]:
        repo.add_member(
            upload,
            dodid=dodid,
            display_name=name,
            rank=None,
            personnel_type=ptype,
            afsc=code,
            normalized_afsc=code,
            source_row_number=int(dodid) + 1,
        )
    repo.activate_succeeded(upload, total_rows=5, accepted_rows=5, rejected_rows=0)
    db.commit()

    members = MemberService(db)
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="1A1XX")} == {
        "1A112G",
        "1A112",
        "1A152D",
    }
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="1A1X2")} == {
        "1A112G",
        "1A112",
        "1A152D",
    }
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="11MX")} == {"11M3K"}
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="11SX")} == {"11S3F"}
    assert members.list_members(afsc_pattern="11MX", personnel_type=PersonnelType.ENLISTED) == []
    assert members.count_members(afsc_pattern="1A") == 3
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="1A112G")} == {"1A112G"}
    assert {m.normalized_afsc for m in members.list_members(afsc_pattern="1A152D")} == {"1A152D"}


def test_engine_facade():
    engine = get_afsc_engine()
    assert engine.validate_search("1A1XX") == "1A1XX"
    assert engine.resolve("1A152D").personnel_type == PersonnelType.ENLISTED
    assert engine.search_labels("1A152D")
    assert engine.ruleset_version
