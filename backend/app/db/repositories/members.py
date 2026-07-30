from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import MemberRecord, RosterUploadRecord
from app.enums import PersonnelType


def escape_like_metacharacters(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MemberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def active_upload_id(self) -> uuid.UUID | None:
        upload = self._session.scalar(
            select(RosterUploadRecord).where(RosterUploadRecord.is_active.is_(True))
        )
        return upload.id if upload else None

    def list_active(
        self,
        *,
        name_query: str | None = None,
        dodid: str | None = None,
        personnel_type: PersonnelType | None = None,
        afsc_like: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MemberRecord]:
        upload_id = self.active_upload_id()
        if upload_id is None:
            return []

        stmt = self._filtered_stmt(
            upload_id,
            name_query=name_query,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
        ).order_by(MemberRecord.display_name.asc())
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._session.scalars(stmt).all())

    def count_active(
        self,
        *,
        name_query: str | None = None,
        dodid: str | None = None,
        personnel_type: PersonnelType | None = None,
        afsc_like: str | None = None,
    ) -> int:
        upload_id = self.active_upload_id()
        if upload_id is None:
            return 0

        stmt = (
            select(func.count())
            .select_from(MemberRecord)
            .where(MemberRecord.upload_id == upload_id)
        )
        stmt = self._apply_filters(
            stmt,
            name_query=name_query,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
        )
        return self._session.scalar(stmt) or 0

    def list_active_ids(
        self,
        *,
        name_query: str | None = None,
        dodid: str | None = None,
        personnel_type: PersonnelType | None = None,
        afsc_like: str | None = None,
    ) -> list[uuid.UUID]:
        upload_id = self.active_upload_id()
        if upload_id is None:
            return []

        stmt = (
            select(MemberRecord.id)
            .where(MemberRecord.upload_id == upload_id)
        )
        stmt = self._apply_filters(
            stmt,
            name_query=name_query,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
        )
        return list(self._session.scalars(stmt).all())

    def _filtered_stmt(
        self,
        upload_id: uuid.UUID,
        *,
        name_query: str | None,
        dodid: str | None,
        personnel_type: PersonnelType | None,
        afsc_like: str | None,
    ):
        stmt = select(MemberRecord).where(MemberRecord.upload_id == upload_id)
        return self._apply_filters(
            stmt,
            name_query=name_query,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
        )

    @staticmethod
    def _apply_filters(stmt, *, name_query, dodid, personnel_type, afsc_like):
        if name_query:
            escaped = escape_like_metacharacters(name_query.strip())
            stmt = stmt.where(MemberRecord.display_name.ilike(f"%{escaped}%", escape="\\"))
        if dodid:
            stmt = stmt.where(MemberRecord.dodid == dodid.strip())
        if personnel_type is not None:
            stmt = stmt.where(MemberRecord.personnel_type == personnel_type)
        if afsc_like:
            stmt = stmt.where(MemberRecord.normalized_afsc.like(afsc_like))
        return stmt
