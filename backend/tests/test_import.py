import io

import pytest
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.afsc import AfscEngine
from app.schemas import PreviewOut, UploadOut
from app.services.import_service import ImportService
from app.services.member_service import MemberService


def _workbook_bytes(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _activate(service: ImportService, *, filename: str, content: bytes) -> UploadOut:
    preview = service.preview_workbook(filename=filename, content=content)
    assert preview.can_commit, (
        f"expected committable preview for {filename}: "
        f"accepted={preview.accepted_rows} rejected={preview.rejected_rows}"
    )
    return service.commit_upload(preview.upload_id)


def _preview(service: ImportService, *, filename: str, content: bytes) -> PreviewOut:
    return service.preview_workbook(filename=filename, content=content)


def _active(service: ImportService) -> UploadOut | None:
    return next((u for u in service.list_uploads() if u.is_active), None)


def test_import_accepts_first_last_name_columns(db: Session):
    service = ImportService(db, AfscEngine())
    summary = _activate(
        service,
        filename="split.xlsx",
        content=_workbook_bytes(
            [
                ["First Name", "Last Name", "DODID", "AFSC"],
                ["Jane", "Doe", "1001", "1A152D"],
                ["John", "Pilot", "1002", "11M3K"],
            ]
        ),
    )
    assert summary.accepted_rows == 2
    assert summary.is_active
    members = MemberService(db, AfscEngine()).list_members(limit=50)
    names = {m.display_name for m in members}
    assert names == {"Jane Doe", "John Pilot"}


def test_import_accepts_valid_rows_and_records_issues(db: Session):
    content = _workbook_bytes(
        [
            ["DODID", "Name", "Rank", "AFSC", "Type"],
            ["1001", "Jane Doe", "SSgt", "1A152D", "enlisted"],
            ["1002", "Bad Wild", "Amn", "1A1X2", "enlisted"],
            ["1003", "John Pilot", "Capt", "11M3K", "officer"],
            ["1004", "Mismatch", "Lt", "11M3K", "enlisted"],
        ]
    )
    service = ImportService(db, AfscEngine())
    summary = _activate(service, filename="input.xlsx", content=content)

    assert summary.accepted_rows == 2
    assert summary.rejected_rows == 2
    assert summary.is_active is True
    assert summary.status.value == "succeeded"
    assert len(summary.issues) >= 2

    members = MemberService(db, AfscEngine()).list_members(afsc_pattern="1A1X2")
    assert len(members) == 1
    assert members[0].display_name == "Jane Doe"
    assert members[0].dodid == "1001"
    assert members[0].afsc_label is not None
    assert "C-130J Loadmaster" in members[0].afsc_label


def test_failed_parse_preserves_prior_active_roster(db: Session):
    good = _workbook_bytes([["DODID", "Name", "AFSC"], ["1001", "Alpha", "11M3K"]])
    service = ImportService(db, AfscEngine())
    first = _activate(service, filename="good.xlsx", content=good)
    assert first.is_active

    preview = _preview(service, filename="bad.xlsx", content=b"not-excel")
    assert preview.can_commit is False
    failed = next(u for u in service.list_uploads() if u.upload_id == preview.upload_id)
    assert failed.status.value == "failed"
    assert failed.is_active is False

    active = _active(service)
    assert active is not None
    assert active.upload_id == first.upload_id


def test_empty_or_all_invalid_upload_keeps_prior_roster(db: Session):
    service = ImportService(db, AfscEngine())
    first = _activate(
        service,
        filename="good.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                ["1001", "Jane Doe", "1A152D"],
                ["1002", "John Pilot", "11M3K"],
            ]
        ),
    )
    assert first.is_active

    empty = _preview(
        service,
        filename="empty.xlsx",
        content=_workbook_bytes([["DODID", "Name", "AFSC"]]),
    )
    assert empty.can_commit is False
    empty_upload = next(u for u in service.list_uploads() if u.upload_id == empty.upload_id)
    assert empty_upload.status.value == "failed"
    assert empty_upload.is_active is False
    assert _active(service).upload_id == first.upload_id
    assert MemberService(db, AfscEngine()).count_members() == 2

    all_bad = _preview(
        service,
        filename="bad.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                ["1001", "Jane Doe", "1A1X2"],
                ["1002", None, None],
            ]
        ),
    )
    assert all_bad.can_commit is False
    members = MemberService(db, AfscEngine()).list_members(limit=50)
    assert {m.dodid: m.normalized_afsc for m in members} == {
        "1001": "1A152D",
        "1002": "11M3K",
    }


def test_overlay_keeps_prior_when_new_row_invalid_and_updates_valid(db: Session):
    service = ImportService(db, AfscEngine())
    _activate(
        service,
        filename="v1.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                ["1001", "Jane Doe", "1A152D"],
                ["1002", "John Pilot", "11M3K"],
            ]
        ),
    )

    second = _activate(
        service,
        filename="v2.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                ["1001", "Jane Doe", "1A1X2"],
                ["1002", "John Pilot", "11S3A"],
                ["1003", "New Enlisted", "1A152A"],
            ]
        ),
    )
    assert second.is_active
    assert second.accepted_rows == 2
    assert second.rejected_rows == 1

    members = {
        m.dodid: m
        for m in MemberService(db, AfscEngine()).list_members(limit=50)
    }
    assert members["1001"].normalized_afsc == "1A152D"
    assert members["1002"].normalized_afsc == "11S3A"
    assert members["1003"].display_name == "New Enlisted"
    assert len(members) == 3


def test_excel_numeric_afsc_and_dodid_coercion(db: Session):
    service = ImportService(db, AfscEngine())
    bad = _preview(
        service,
        filename="nums.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                [1001.0, "Numeric", 11],
            ]
        ),
    )
    assert bad.can_commit is False
    assert bad.accepted_rows == 0

    summary = _activate(
        service,
        filename="ok.xlsx",
        content=_workbook_bytes(
            [
                ["DODID", "Name", "AFSC"],
                [1001, "Officer", "11M3K"],
            ]
        ),
    )
    assert summary.accepted_rows == 1
    members = MemberService(db, AfscEngine()).list_members()
    assert members[0].dodid == "1001"


def test_unexpected_import_error_does_not_return_soft_failure(db: Session, monkeypatch):
    service = ImportService(db, AfscEngine())

    def boom(*_args, **_kwargs):
        raise RuntimeError("disk exploded")

    monkeypatch.setattr(service, "_process_upload", boom)
    with pytest.raises(RuntimeError, match="disk exploded"):
        service.preview_workbook(
            filename="x.xlsx",
            content=_workbook_bytes([["DODID", "Name", "AFSC"], ["1", "A", "11M3K"]]),
        )
    assert _active(service) is None
