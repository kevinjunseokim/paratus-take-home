from __future__ import annotations

import re

from app.afsc.catalog import AfscCatalog, FamilySpec, get_catalog
from app.afsc.models import ParsedAFSC
from app.enums import PersonnelType
from app.exceptions import AfscValidationError

_MEMBER_RE = re.compile(r"^[A-Z0-9]+$")
_SEARCH_RE = re.compile(r"^[A-Z0-9X]+$")


def normalize_code(value: str) -> str:
    return value.strip().upper()


def validate_search_pattern(pattern: str) -> str:
    normalized = normalize_code(pattern)
    if len(normalized) < 2:
        raise AfscValidationError("Search pattern must be at least 2 characters")
    if "X" in normalized[:2]:
        raise AfscValidationError("Search pattern cannot contain X in the first two characters")
    if not _SEARCH_RE.fullmatch(normalized):
        raise AfscValidationError("Search pattern may only contain letters, digits, and X")
    return normalized


def _enlisted_families_for(normalized: str, catalog: AfscCatalog) -> list[FamilySpec]:
    if len(normalized) < 5:
        return [
            family
            for family in catalog.families.values()
            if family.personnel_type == PersonnelType.ENLISTED
            and _prefix_matches_family(normalized, family)
        ]

    specialty = normalized[4]
    matches: list[FamilySpec] = []
    for family in catalog.families.values():
        if family.personnel_type != PersonnelType.ENLISTED:
            continue
        if family.specialty_char and specialty not in (family.specialty_char, "X"):
            continue
        template_prefix = f"{family.career_field}{family.subdivision or ''}"
        if len(normalized) < len(template_prefix):
            continue
        if not all(
            t == "X" or n == "X" or t == n
            for t, n in zip(template_prefix, normalized, strict=False)
        ):
            continue
        matches.append(family)
    return matches


def _officer_families_for(normalized: str, catalog: AfscCatalog) -> list[FamilySpec]:
    if len(normalized) < 3:
        return [
            family
            for family in catalog.families.values()
            if family.personnel_type == PersonnelType.OFFICER
            and normalized.startswith(family.career_field)
        ]

    utilization = normalized[2]
    matches: list[FamilySpec] = []
    for family in catalog.families.values():
        if family.personnel_type != PersonnelType.OFFICER:
            continue
        if family.utilization and utilization not in (family.utilization, "X"):
            continue
        if not normalized.startswith(family.career_field):
            continue
        matches.append(family)
    return matches


def _prefix_matches_family(normalized: str, family: FamilySpec) -> bool:
    template = family.pattern
    if len(normalized) > len(template):
        return False
    return all(
        t == "X" or n == "X" or t == n
        for t, n in zip(template[: len(normalized)], normalized, strict=False)
    )


def matching_families(
    normalized: str, catalog: AfscCatalog | None = None
) -> list[FamilySpec]:
    catalog = catalog or get_catalog()
    if normalized in catalog.shorthands:
        family = catalog.get_family(catalog.shorthands[normalized]["family"])
        return [family] if family else []

    if len(normalized) >= 2 and normalized[0].isdigit() and normalized[1].isalpha():
        return _enlisted_families_for(normalized, catalog)

    if len(normalized) >= 2 and normalized[0].isdigit() and normalized[1].isdigit():
        return _officer_families_for(normalized, catalog)

    return []


def identify_family(normalized: str, catalog: AfscCatalog | None = None) -> FamilySpec | None:
    matches = matching_families(normalized, catalog)
    if not matches:
        return None
    if len(matches) > 1:
        patterns = ", ".join(sorted(f.pattern for f in matches))
        raise AfscValidationError(
            f"Ambiguous AFSC pattern {normalized}; matches multiple families: {patterns}"
        )
    return matches[0]


def parse_member_afsc(raw: str, catalog: AfscCatalog | None = None) -> ParsedAFSC:
    catalog = catalog or get_catalog()
    normalized = normalize_code(raw)
    if not normalized:
        raise AfscValidationError("AFSC is required")
    if "X" in normalized:
        raise AfscValidationError("Member AFSCs cannot contain wildcard notation")
    if not _MEMBER_RE.fullmatch(normalized):
        raise AfscValidationError("Member AFSC may only contain letters and digits")
    if normalized in catalog.shorthands:
        raise AfscValidationError(
            f"{normalized} is a resolution shorthand, not a valid member AFSC"
        )

    family = identify_family(normalized, catalog)
    if family is None:
        raise AfscValidationError(f"Unsupported AFSC family for code {normalized}")

    level: str | None = None
    suffix: str | None = None

    if family.personnel_type == PersonnelType.ENLISTED:
        if len(normalized) < 5:
            raise AfscValidationError(f"Enlisted AFSC {normalized} is too short")
        level = normalized[3]
        if level not in family.levels:
            raise AfscValidationError(f"Unknown skill level {level} for {family.pattern}")
        if family.specialty_char and normalized[4] != family.specialty_char:
            raise AfscValidationError(
                f"AFSC {normalized} does not match family {family.pattern}"
            )
        if len(normalized) > 5:
            suffix = normalized[5:]
            if len(suffix) != 1 or not suffix.isalnum():
                raise AfscValidationError(
                    f"Invalid specialty shredout '{suffix}' for {family.pattern}"
                )
    else:
        if len(normalized) < 4:
            raise AfscValidationError(f"Officer AFSC {normalized} is too short")
        level = normalized[3]
        if level not in family.levels:
            raise AfscValidationError(
                f"Unknown qualification level {level} for {family.pattern}"
            )
        if len(normalized) > 4:
            suffix = normalized[4:]
            if len(suffix) != 1 or not suffix.isalnum():
                raise AfscValidationError(
                    f"Invalid specialty shredout '{suffix}' for {family.pattern}"
                )

    return ParsedAFSC(
        raw=raw,
        normalized=normalized,
        personnel_type=family.personnel_type,
        family_pattern=family.pattern,
        skill_or_qualification_level=level,
        suffix=suffix,
        canonical_code=normalized,
    )


def parse_for_resolution(raw: str, catalog: AfscCatalog | None = None) -> ParsedAFSC:
    catalog = catalog or get_catalog()
    normalized = normalize_code(raw)
    if not normalized:
        raise AfscValidationError("AFSC is required")

    if normalized in catalog.shorthands:
        meta = catalog.shorthands[normalized]
        family = catalog.get_family(meta["family"])
        if family is None:
            raise AfscValidationError(f"Shorthand {normalized} references unknown family")
        return ParsedAFSC(
            raw=raw,
            normalized=normalized,
            personnel_type=family.personnel_type,
            family_pattern=family.pattern,
            skill_or_qualification_level=None,
            suffix=meta.get("suffix"),
            is_shorthand=True,
            canonical_code=meta["canonical_pattern"],
        )

    if "X" in normalized:
        validate_search_pattern(normalized)
        family = identify_family(normalized, catalog)
        if family is None:
            raise AfscValidationError(f"Unsupported AFSC pattern {normalized}")
        level = None
        suffix = None
        if family.personnel_type == PersonnelType.ENLISTED and len(normalized) >= 4:
            if normalized[3] != "X":
                level = normalized[3]
            if len(normalized) > 5 and "X" not in normalized[5:]:
                suffix = normalized[5:]
        elif family.personnel_type == PersonnelType.OFFICER and len(normalized) >= 4:
            if normalized[3] != "X":
                level = normalized[3]
            if len(normalized) > 4 and "X" not in normalized[4:]:
                suffix = normalized[4:]
        return ParsedAFSC(
            raw=raw,
            normalized=normalized,
            personnel_type=family.personnel_type,
            family_pattern=family.pattern,
            skill_or_qualification_level=level,
            suffix=suffix,
            canonical_code=normalized,
        )

    return parse_member_afsc(normalized, catalog)
