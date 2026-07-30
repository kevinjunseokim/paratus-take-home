from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import ImportIssueRecord, MemberRecord, RosterUploadRecord
from app.enums import IssueSeverity, PersonnelType, UploadStatus


class RosterRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_pending(self, *, filename: str, ruleset_version: str) -> RosterUploadRecord:
        upload = RosterUploadRecord(
            filename=filename,
            status=UploadStatus.PENDING,
            ruleset_version=ruleset_version,
            is_active=False,
        )
        self._session.add(upload)
        self._session.flush()
        return upload

    def get(self, upload_id: uuid.UUID) -> RosterUploadRecord | None:
        return self._session.scalar(
            select(RosterUploadRecord)
            .where(RosterUploadRecord.id == upload_id)
            .options(selectinload(RosterUploadRecord.issues))
        )

    def get_active(self) -> RosterUploadRecord | None:
        return self._session.scalar(
            select(RosterUploadRecord)
            .where(RosterUploadRecord.is_active.is_(True))
            .options(selectinload(RosterUploadRecord.issues))
        )

    def list_all(self) -> list[RosterUploadRecord]:
        return list(
            self._session.scalars(
                select(RosterUploadRecord)
                .options(selectinload(RosterUploadRecord.issues))
                .order_by(RosterUploadRecord.uploaded_at.desc())
            ).all()
        )

    def list_members_for_upload(self, upload_id: uuid.UUID) -> list[MemberRecord]:
        return list(
            self._session.scalars(
                select(MemberRecord)
                .where(MemberRecord.upload_id == upload_id)
                .order_by(MemberRecord.display_name.asc())
            ).all()
        )

    def add_member(
        self,
        upload: RosterUploadRecord,
        *,
        dodid: str,
        display_name: str,
        rank: str | None,
        personnel_type: PersonnelType | None,
        afsc: str,
        normalized_afsc: str,
        source_row_number: int,
    ) -> MemberRecord:
        record = MemberRecord(
            upload_id=upload.id,
            dodid=dodid,
            display_name=display_name,
            rank=rank,
            personnel_type=personnel_type,
            afsc=afsc,
            normalized_afsc=normalized_afsc,
            source_row_number=source_row_number,
        )
        self._session.add(record)
        return record

    def add_issue(
        self,
        upload: RosterUploadRecord,
        *,
        row_number: int | None,
        field: str | None,
        raw_value: str | None,
        reason: str,
        severity: IssueSeverity = IssueSeverity.ERROR,
    ) -> ImportIssueRecord:
        record = ImportIssueRecord(
            upload_id=upload.id,
            row_number=row_number,
            field=field,
            raw_value=raw_value,
            reason=reason,
            severity=severity,
        )
        self._session.add(record)
        return record

    def mark_failed(
        self,
        upload: RosterUploadRecord,
        *,
        total_rows: int,
        accepted_rows: int,
        rejected_rows: int,
    ) -> RosterUploadRecord:
        upload.status = UploadStatus.FAILED
        upload.total_rows = total_rows
        upload.accepted_rows = accepted_rows
        upload.rejected_rows = rejected_rows
        upload.is_active = False
        self._session.add(upload)
        self._session.flush()
        return upload

    def stage_pending(
        self,
        upload: RosterUploadRecord,
        *,
        total_rows: int,
        accepted_rows: int,
        rejected_rows: int,
    ) -> RosterUploadRecord:
        upload.status = UploadStatus.PENDING
        upload.total_rows = total_rows
        upload.accepted_rows = accepted_rows
        upload.rejected_rows = rejected_rows
        upload.is_active = False
        self._session.add(upload)
        self._session.flush()
        return upload

    def activate_succeeded(
        self,
        upload: RosterUploadRecord,
        *,
        total_rows: int,
        accepted_rows: int,
        rejected_rows: int,
    ) -> RosterUploadRecord:
        upload.status = UploadStatus.SUCCEEDED
        upload.total_rows = total_rows
        upload.accepted_rows = accepted_rows
        upload.rejected_rows = rejected_rows
        self._session.execute(
            update(RosterUploadRecord)
            .where(RosterUploadRecord.is_active.is_(True))
            .values(is_active=False)
        )
        upload.is_active = True
        self._session.add(upload)
        self._session.flush()
        return upload

    def delete_upload(self, upload: RosterUploadRecord) -> None:
        self._session.delete(upload)
        self._session.flush()
