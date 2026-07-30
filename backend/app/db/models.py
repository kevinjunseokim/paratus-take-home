from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.enums import IssueSeverity, PersonnelType, UploadStatus


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class RosterUploadRecord(Base):
    __tablename__ = "roster_uploads"
    __table_args__ = (
        Index(
            "uq_roster_uploads_one_active",
            "is_active",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active IS TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(
            UploadStatus,
            name="upload_status",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=UploadStatus.PENDING,
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    members: Mapped[list[MemberRecord]] = relationship(
        back_populates="upload",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list[ImportIssueRecord]] = relationship(
        back_populates="upload",
        cascade="all, delete-orphan",
    )


class MemberRecord(Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_upload_id", "upload_id"),
        Index("ix_members_normalized_afsc", "normalized_afsc"),
        Index("ix_members_upload_name_afsc", "upload_id", "display_name", "normalized_afsc"),
        Index("uq_members_upload_dodid", "upload_id", "dodid", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roster_uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    dodid: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    rank: Mapped[str | None] = mapped_column(String(64), nullable=True)
    personnel_type: Mapped[PersonnelType | None] = mapped_column(
        Enum(
            PersonnelType,
            name="personnel_type",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    afsc: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_afsc: Mapped[str] = mapped_column(String(32), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    upload: Mapped[RosterUploadRecord] = relationship(back_populates="members")


class ImportIssueRecord(Base):
    __tablename__ = "import_issues"
    __table_args__ = (Index("ix_import_issues_upload_id", "upload_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roster_uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(
            IssueSeverity,
            name="issue_severity",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=IssueSeverity.ERROR,
    )

    upload: Mapped[RosterUploadRecord] = relationship(back_populates="issues")
