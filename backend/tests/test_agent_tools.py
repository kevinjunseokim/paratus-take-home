from sqlalchemy.orm import Session

from app.afsc import AfscEngine
from app.db.repositories.roster import RosterRepository
from app.enums import PersonnelType
from app.services.agent_tools import AgentToolExecutor
from app.services.member_service import MemberService


def test_tools_validate_and_query_active_roster(db: Session):
    repo = RosterRepository(db)
    upload = repo.create_pending(filename="r.xlsx", ruleset_version="v1")
    repo.add_member(
        upload,
        dodid="1001",
        display_name="John Doe",
        rank="SSgt",
        personnel_type=PersonnelType.ENLISTED,
        afsc="1A152D",
        normalized_afsc="1A152D",
        source_row_number=2,
    )
    repo.add_member(
        upload,
        dodid="1002",
        display_name="Sara Pilot",
        rank="Capt",
        personnel_type=PersonnelType.OFFICER,
        afsc="11M3K",
        normalized_afsc="11M3K",
        source_row_number=3,
    )
    repo.activate_succeeded(upload, total_rows=2, accepted_rows=2, rejected_rows=0)
    db.commit()

    afsc = AfscEngine()
    tools = AgentToolExecutor(MemberService(db, afsc), afsc)

    resolved = tools.execute("resolve_afsc", {"code": "11MK"})
    assert resolved["ok"] is True
    assert resolved["canonical_code"] == "11MXK"
    assert resolved["family_title"] == "Mobility Pilot"

    counted = tools.execute(
        "count_members",
        {"afsc_pattern": "11MX", "personnel_type": "officer"},
    )
    assert counted == {"ok": True, "count": 1}

    found = tools.execute("find_members", {"name": "John"})
    assert found["ok"] is True
    assert found["count"] == 1
    assert found["members"][0]["afsc"] == "1A152D"
    assert found["members"][0]["dodid"] == "1001"

    invalid = tools.execute("count_members", {"afsc_pattern": "1X"})
    assert invalid["ok"] is False

    team = tools.execute(
        "check_team",
        {
            "requirements": [
                {"afsc_pattern": "11MX", "personnel_type": "officer", "needed": 1},
                {"afsc_pattern": "1A1XX", "personnel_type": "enlisted", "needed": 2},
            ]
        },
    )
    assert team["ok"] is True
    assert team["can_form"] is False
    assert team["requirements"][0]["eligible"] == 1
    assert team["requirements"][0]["assigned"] == 1
    assert team["requirements"][0]["can_fill"] is True
    assert team["requirements"][1]["eligible"] == 1
    assert team["requirements"][1]["assigned"] == 1
    assert team["requirements"][1]["shortfall"] == 1

    unknown = tools.execute("nope", {})
    assert unknown["ok"] is False


def test_check_team_uses_distinct_members(db: Session):
    repo = RosterRepository(db)
    upload = repo.create_pending(filename="r.xlsx", ruleset_version="v1")
    repo.add_member(
        upload,
        dodid="2001",
        display_name="Multi Match",
        rank="SSgt",
        personnel_type=PersonnelType.ENLISTED,
        afsc="1A152D",
        normalized_afsc="1A152D",
        source_row_number=2,
    )
    repo.activate_succeeded(upload, total_rows=1, accepted_rows=1, rejected_rows=0)
    db.commit()

    afsc = AfscEngine()
    tools = AgentToolExecutor(MemberService(db, afsc), afsc)
    team = tools.execute(
        "check_team",
        {
            "requirements": [
                {"afsc_pattern": "1A1XX", "personnel_type": "enlisted", "needed": 1},
                {"afsc_pattern": "1A152", "personnel_type": "enlisted", "needed": 1},
            ]
        },
    )
    assert team["ok"] is True
    assert team["can_form"] is False
    assert team["requirements"][0]["eligible"] == 1
    assert team["requirements"][1]["eligible"] == 1
    assert sum(r["assigned"] for r in team["requirements"]) == 1
