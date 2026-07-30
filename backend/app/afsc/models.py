from __future__ import annotations

from pydantic import BaseModel, Field

from app.enums import PersonnelType


class ParsedAFSC(BaseModel):
    raw: str
    normalized: str
    personnel_type: PersonnelType
    family_pattern: str
    skill_or_qualification_level: str | None = None
    suffix: str | None = None
    is_shorthand: bool = False
    canonical_code: str | None = None


class ResolvedAFSC(BaseModel):
    code: str
    canonical_code: str
    personnel_type: PersonnelType
    family: str
    family_title: str
    level: str | None = None
    level_code: str | None = None
    specialization: str | None = None
    specialization_code: str | None = None
    full_label: str
    ruleset_version: str
    breakdown: list[str] = Field(default_factory=list)
