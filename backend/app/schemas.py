from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.enums import IssueSeverity, PersonnelType, UploadStatus

if TYPE_CHECKING:
    from app.afsc.models import ResolvedAFSC


class IssueOut(BaseModel):
    row: int | None = None
    field: str | None = None
    value: str | None = None
    reason: str
    severity: IssueSeverity


class UploadOut(BaseModel):
    upload_id: uuid.UUID
    filename: str
    uploaded_at: datetime | None = None
    status: UploadStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    ruleset_version: str
    is_active: bool
    issues: list[IssueOut] = Field(default_factory=list)


class PreviewRowOut(BaseModel):
    row: int | None = None
    status: str  # success | failure
    dodid: str | None = None
    display_name: str | None = None
    afsc: str | None = None
    normalized_afsc: str | None = None
    personnel_type: PersonnelType | None = None
    reason: str | None = None
    severity: IssueSeverity | None = None


class PreviewOut(BaseModel):
    upload_id: uuid.UUID
    filename: str
    ruleset_version: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    can_commit: bool
    successes: list[PreviewRowOut] = Field(default_factory=list)
    failures: list[PreviewRowOut] = Field(default_factory=list)


class MemberOut(BaseModel):
    id: uuid.UUID
    dodid: str
    display_name: str
    rank: str | None
    personnel_type: PersonnelType | None
    afsc: str
    normalized_afsc: str
    afsc_label: str | None = None
    afsc_labels: list[str] = Field(default_factory=list)
    afsc_family: str | None = None
    afsc_level: str | None = None
    afsc_specialization: str | None = None
    created_at: datetime | None = None


class MembersPageOut(BaseModel):
    members: list[MemberOut]
    total: int
    limit: int
    offset: int


class TeamRequirementIn(BaseModel):
    afsc: str = Field(min_length=1)
    personnel_type: PersonnelType | None = None
    needed: int = Field(default=1, ge=1, le=100)


class TeamRequirementResultOut(BaseModel):
    afsc: str
    personnel_type: PersonnelType | None = None
    needed: int
    eligible: int
    assigned: int
    shortfall: int
    can_fill: bool
    labels: list[str] = Field(default_factory=list)
    error: str | None = None


class TeamCheckIn(BaseModel):
    requirements: list[TeamRequirementIn] = Field(min_length=1, max_length=12)


class TeamCheckOut(BaseModel):
    can_form: bool
    results: list[TeamRequirementResultOut]


class SearchLabelsOut(BaseModel):
    pattern: str
    labels: list[str] = Field(default_factory=list)


class ResolveOut(BaseModel):
    code: str
    canonical_code: str
    personnel_type: PersonnelType
    family: str
    family_title: str
    level: str | None
    specialization: str | None
    full_label: str
    labels: list[str] = Field(default_factory=list)
    ruleset_version: str

    @classmethod
    def from_resolved(cls, resolved: ResolvedAFSC) -> ResolveOut:
        return cls(
            code=resolved.code,
            canonical_code=resolved.canonical_code,
            personnel_type=resolved.personnel_type,
            family=resolved.family,
            family_title=resolved.family_title,
            level=resolved.level,
            specialization=resolved.specialization,
            full_label=resolved.full_label,
            labels=list(resolved.breakdown),
            ruleset_version=resolved.ruleset_version,
        )


class CatalogCodeLabel(BaseModel):
    code: str
    label: str


class CatalogFamilyOut(BaseModel):
    pattern: str
    personnel_type: PersonnelType
    career_group: str
    career_field: str
    title: str
    wildcard_role: str
    levels: dict[str, str]
    suffixes: dict[str, str]
    subdivision: str | None = None
    subdivision_title: str | None = None
    specialty_char: str | None = None
    utilization: str | None = None


class CatalogOut(BaseModel):
    version: str
    sources: list[str]
    career_groups: list[CatalogCodeLabel]
    career_fields: list[CatalogCodeLabel]
    families: list[CatalogFamilyOut]


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class ChatResponse(BaseModel):
    reply: str
    tool_traces: list[dict] = Field(default_factory=list)
