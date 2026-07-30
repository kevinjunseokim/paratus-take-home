from __future__ import annotations

from app.afsc.catalog import AfscCatalog, FamilySpec, get_catalog
from app.afsc.models import ResolvedAFSC
from app.afsc.parser import matching_families, normalize_code, parse_for_resolution
from app.enums import PersonnelType
from app.exceptions import AfscResolutionError, AfscValidationError


class _Breakdown:
    def __init__(
        self,
        labels: list[str],
        level_label: str | None = None,
        specialization: str | None = None,
    ) -> None:
        self.labels = labels
        self.level_label = level_label
        self.specialization = specialization


def _family_breakdown(
    catalog: AfscCatalog,
    family: FamilySpec,
    *,
    level_code: str | None = None,
    suffix: str | None = None,
) -> _Breakdown:
    group_label = catalog.career_groups.get(family.career_group, "Unknown")
    field_label = catalog.career_fields.get(family.career_field, family.career_field)

    labels: list[str] = [group_label, field_label]
    if family.subdivision_title and family.subdivision_title != field_label:
        labels.append(family.subdivision_title)

    level_label: str | None = None
    if level_code:
        level_label = family.levels.get(level_code)
        if level_label is None:
            raise AfscResolutionError(f"Unknown level {level_code} for {family.pattern}")

    specialization: str | None = None
    if suffix:
        specialization = family.suffixes.get(suffix) or f"Specialty {suffix}"

    title_parts = [family.title]
    if level_label:
        title_parts.append(level_label)
    labels.append(" ".join(title_parts))
    if specialization:
        labels.append(specialization)

    return _Breakdown(labels=labels, level_label=level_label, specialization=specialization)


def resolve(code: str, catalog: AfscCatalog | None = None) -> ResolvedAFSC:
    catalog = catalog or get_catalog()
    try:
        parsed = parse_for_resolution(code, catalog)
    except AfscValidationError as exc:
        raise AfscResolutionError(str(exc)) from exc

    family = catalog.get_family(parsed.family_pattern)
    if family is None:
        raise AfscResolutionError(f"Unknown family {parsed.family_pattern}")

    breakdown = _family_breakdown(
        catalog,
        family,
        level_code=parsed.skill_or_qualification_level,
        suffix=parsed.suffix,
    )

    return ResolvedAFSC(
        code=parsed.normalized,
        canonical_code=parsed.canonical_code or parsed.normalized,
        personnel_type=parsed.personnel_type,
        family=family.pattern,
        family_title=family.title,
        level=breakdown.level_label,
        level_code=parsed.skill_or_qualification_level,
        specialization=breakdown.specialization,
        specialization_code=parsed.suffix,
        full_label=", ".join(breakdown.labels),
        ruleset_version=catalog.version,
        breakdown=breakdown.labels,
    )


def search_highlight_labels(pattern: str, catalog: AfscCatalog | None = None) -> list[str]:
    catalog = catalog or get_catalog()
    try:
        return list(resolve(pattern, catalog).breakdown)
    except AfscResolutionError:
        pass

    normalized = normalize_code(pattern)
    if len(normalized) < 2:
        return []

    matches = matching_families(normalized, catalog)
    if not matches:
        return []

    level_code: str | None = None
    suffix: str | None = None
    if matches[0].personnel_type == PersonnelType.ENLISTED:
        if len(normalized) >= 4 and normalized[3] != "X":
            level_code = normalized[3]
        if len(normalized) > 5 and "X" not in normalized[5:]:
            suffix = normalized[5:]
    else:
        if len(normalized) >= 4 and normalized[3] != "X":
            level_code = normalized[3]
        if len(normalized) > 4 and "X" not in normalized[4:]:
            suffix = normalized[4:]

    breakdowns: list[list[str]] = []
    for family in matches:
        try:
            use_level = level_code if level_code and level_code in family.levels else None
            use_suffix = suffix  # unknown shredouts still label as Specialty X
            breakdowns.append(
                _family_breakdown(
                    catalog,
                    family,
                    level_code=use_level,
                    suffix=use_suffix,
                ).labels
            )
        except AfscResolutionError:
            continue

    if not breakdowns:
        return []

    shared: list[str] = []
    for index, label in enumerate(breakdowns[0]):
        if all(len(b) > index and b[index] == label for b in breakdowns[1:]):
            shared.append(label)
        else:
            break
    return shared


def classify(code_or_pattern: str, catalog: AfscCatalog | None = None) -> PersonnelType:
    from app.afsc.parser import validate_search_pattern

    catalog = catalog or get_catalog()
    normalized = normalize_code(code_or_pattern)
    if "X" in normalized:
        validate_search_pattern(normalized)
        matches = matching_families(normalized, catalog)
        if not matches:
            raise AfscValidationError(f"Unsupported AFSC pattern {normalized}")
        types = {m.personnel_type for m in matches}
        if len(types) > 1:
            raise AfscValidationError(
                f"Ambiguous AFSC pattern {normalized}; spans enlisted and officer families"
            )
        return next(iter(types))
    return parse_for_resolution(code_or_pattern, catalog).personnel_type
