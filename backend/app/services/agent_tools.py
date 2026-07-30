from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.afsc import AfscEngine
from app.enums import PersonnelType
from app.exceptions import AfscResolutionError, AfscValidationError
from app.schemas import ResolveOut, TeamRequirementIn
from app.services.member_service import MemberService

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "resolve_afsc",
            "description": "Resolve an AFSC code or pattern into a human-readable label.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_members",
            "description": "Search the active roster. Never invent members. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dodid": {
                        "type": "string",
                        "description": "Exact DODID match only.",
                    },
                    "afsc_pattern": {"type": "string"},
                    "personnel_type": {"type": "string", "enum": ["enlisted", "officer"]},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_members",
            "description": "Count members on the active roster. Always use for headcounts. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dodid": {
                        "type": "string",
                        "description": "Exact DODID match only.",
                    },
                    "afsc_pattern": {"type": "string"},
                    "personnel_type": {"type": "string", "enum": ["enlisted", "officer"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_team",
            "description": (
                "Check whether the active roster can form a team given role requirements. "
                "Each requirement is an AFSC pattern, optional personnel type, and count needed. "
                "Uses distinct-member assignment (one person fills at most one seat). "
                "Returns eligible pool sizes, assigned counts, and shortfalls — does not name people. "
                "Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 12,
                        "items": {
                            "type": "object",
                            "properties": {
                                "afsc_pattern": {"type": "string"},
                                "personnel_type": {
                                    "type": "string",
                                    "enum": ["enlisted", "officer"],
                                },
                                "needed": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100,
                                    "default": 1,
                                },
                            },
                            "required": ["afsc_pattern", "needed"],
                        },
                    },
                },
                "required": ["requirements"],
            },
        },
    },
]


def _empty_personnel_type(value: Any) -> Any:
    if value == "" or value is None:
        return None
    return value


class ResolveAfscArgs(BaseModel):
    code: str = Field(min_length=1)


class MemberQueryArgs(BaseModel):
    name: str | None = None
    dodid: str | None = None
    afsc_pattern: str | None = None
    personnel_type: PersonnelType | None = None

    @field_validator("personnel_type", mode="before")
    @classmethod
    def _coerce_type(cls, value: Any) -> Any:
        return _empty_personnel_type(value)


class FindMembersArgs(MemberQueryArgs):
    limit: int = Field(default=20, ge=1, le=50)


class CountMembersArgs(MemberQueryArgs):
    pass


class TeamRequirementArgs(BaseModel):
    afsc_pattern: str = Field(min_length=1)
    personnel_type: PersonnelType | None = None
    needed: int = Field(default=1, ge=1, le=100)

    @field_validator("personnel_type", mode="before")
    @classmethod
    def _coerce_type(cls, value: Any) -> Any:
        return _empty_personnel_type(value)


class CheckTeamArgs(BaseModel):
    requirements: list[TeamRequirementArgs] = Field(min_length=1, max_length=12)


class AgentToolExecutor:
    def __init__(self, members: MemberService, afsc: AfscEngine) -> None:
        self._members = members
        self._afsc = afsc

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "resolve_afsc":
                return self._resolve(ResolveAfscArgs.model_validate(arguments))
            if name == "find_members":
                return self._find(FindMembersArgs.model_validate(arguments))
            if name == "count_members":
                return self._count(CountMembersArgs.model_validate(arguments))
            if name == "check_team":
                return self._check_team(CheckTeamArgs.model_validate(arguments))
            return {"ok": False, "error": f"Unknown tool: {name}"}
        except ValidationError as exc:
            return {"ok": False, "error": "Invalid tool arguments", "details": exc.errors()}
        except (AfscValidationError, AfscResolutionError) as exc:
            return {"ok": False, "error": str(exc)}

    def _resolve(self, args: ResolveAfscArgs) -> dict[str, Any]:
        out = ResolveOut.from_resolved(self._afsc.resolve(args.code))
        return {"ok": True, **out.model_dump(mode="json")}

    def _find(self, args: FindMembersArgs) -> dict[str, Any]:
        count = self._members.count_members(
            name=args.name,
            dodid=args.dodid,
            afsc_pattern=args.afsc_pattern,
            personnel_type=args.personnel_type,
        )
        members = self._members.list_members(
            name=args.name,
            dodid=args.dodid,
            afsc_pattern=args.afsc_pattern,
            personnel_type=args.personnel_type,
            limit=args.limit,
            offset=0,
        )
        return {
            "ok": True,
            "count": count,
            "returned": len(members),
            "members": [
                {
                    "id": str(m.id),
                    "dodid": m.dodid,
                    "display_name": m.display_name,
                    "rank": m.rank,
                    "personnel_type": m.personnel_type.value if m.personnel_type else None,
                    "afsc": m.normalized_afsc,
                    "afsc_label": m.afsc_label,
                }
                for m in members
            ],
        }

    def _count(self, args: CountMembersArgs) -> dict[str, Any]:
        return {
            "ok": True,
            "count": self._members.count_members(
                name=args.name,
                dodid=args.dodid,
                afsc_pattern=args.afsc_pattern,
                personnel_type=args.personnel_type,
            ),
        }

    def _check_team(self, args: CheckTeamArgs) -> dict[str, Any]:
        out = self._members.check_team(
            [
                TeamRequirementIn(
                    afsc=req.afsc_pattern,
                    personnel_type=req.personnel_type,
                    needed=req.needed,
                )
                for req in args.requirements
            ]
        )
        return {
            "ok": True,
            "can_form": out.can_form,
            "requirements": [
                {
                    "afsc_pattern": r.afsc,
                    "personnel_type": (
                        r.personnel_type.value if r.personnel_type else None
                    ),
                    "needed": r.needed,
                    "eligible": r.eligible,
                    "assigned": r.assigned,
                    "shortfall": r.shortfall,
                    "can_fill": r.can_fill,
                    "labels": r.labels,
                    **({"error": r.error} if r.error else {}),
                }
                for r in out.results
            ],
        }
