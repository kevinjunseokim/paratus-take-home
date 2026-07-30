from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ImportIssueRecord, MemberRecord
from app.db.repositories.roster import RosterRepository
from app.db.session import normalize_database_url
from app.enums import IssueSeverity, PersonnelType, UploadStatus


def test_normalize_railway_postgres_url():
    assert normalize_database_url("postgres://u:p@h:5432/db") == (
        "postgresql+psycopg://u:p@h:5432/db"
    )
    assert normalize_database_url("postgresql://u:p@h:5432/db") == (
        "postgresql+psycopg://u:p@h:5432/db"
    )
    assert normalize_database_url("sqlite:///./data/paratus.db") == "sqlite:///./data/paratus.db"


def test_versioned_upload_activation(db: Session):
    repo = RosterRepository(db)

    first = repo.create_pending(filename="a.xlsx", ruleset_version="v1")
    repo.add_member(
        first,
        dodid="1001",
        display_name="Alpha",
        rank=None,
        personnel_type=PersonnelType.OFFICER,
        afsc="11M3K",
        normalized_afsc="11M3K",
        source_row_number=2,
    )
    repo.activate_succeeded(first, total_rows=1, accepted_rows=1, rejected_rows=0)
    db.commit()

    second = repo.create_pending(filename="b.xlsx", ruleset_version="v1")
    repo.add_member(
        second,
        dodid="1002",
        display_name="Bravo",
        rank=None,
        personnel_type=PersonnelType.ENLISTED,
        afsc="1A152D",
        normalized_afsc="1A152D",
        source_row_number=2,
    )
    repo.activate_succeeded(second, total_rows=1, accepted_rows=1, rejected_rows=0)
    db.commit()

    db.refresh(first)
    db.refresh(second)
    assert first.is_active is False
    assert second.is_active is True
    assert repo.get_active().id == second.id

    repo.add_issue(
        first,
        row_number=9,
        field="afsc",
        raw_value="1A1X2",
        reason="wildcard",
        severity=IssueSeverity.ERROR,
    )
    db.commit()
    issues = db.scalars(
        select(ImportIssueRecord).where(ImportIssueRecord.upload_id == first.id)
    ).all()
    assert len(issues) == 1


def test_failed_upload_does_not_become_active(db: Session):
    repo = RosterRepository(db)
    good = repo.create_pending(filename="good.xlsx", ruleset_version="v1")
    repo.activate_succeeded(good, total_rows=0, accepted_rows=0, rejected_rows=0)
    db.commit()

    bad = repo.create_pending(filename="bad.xlsx", ruleset_version="v1")
    repo.mark_failed(bad, total_rows=0, accepted_rows=0, rejected_rows=0)
    db.commit()

    db.refresh(good)
    db.refresh(bad)
    assert good.is_active is True
    assert bad.is_active is False
    assert bad.status == UploadStatus.FAILED


def test_member_has_no_afsc_name_column():
    assert "afsc_name" not in MemberRecord.__table__.c
    assert "dodid" in MemberRecord.__table__.c
