from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.enums import PersonnelType


CATALOG_PATH = Path(__file__).with_name("catalog.yaml")


@dataclass(frozen=True)
class FamilySpec:
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


@dataclass(frozen=True)
class AfscCatalog:
    version: str
    sources: tuple[str, ...]
    career_groups: dict[str, str]
    career_fields: dict[str, str]
    families: dict[str, FamilySpec]
    shorthands: dict[str, dict[str, str]]

    def get_family(self, pattern: str) -> FamilySpec | None:
        return self.families.get(pattern)


def _parse_family(pattern: str, raw: dict[str, Any]) -> FamilySpec:
    levels_key = "skill_levels" if raw.get("wildcard_role") == "skill_level" else "qualification_levels"
    return FamilySpec(
        pattern=pattern,
        personnel_type=PersonnelType(raw["personnel_type"]),
        career_group=str(raw["career_group"]),
        career_field=str(raw["career_field"]),
        title=raw["title"],
        wildcard_role=raw["wildcard_role"],
        levels={str(k): v for k, v in raw.get(levels_key, {}).items()},
        suffixes={str(k): v for k, v in raw.get("suffixes", {}).items()},
        subdivision=str(raw["subdivision"]) if raw.get("subdivision") is not None else None,
        subdivision_title=raw.get("subdivision_title"),
        specialty_char=str(raw["specialty_char"]) if raw.get("specialty_char") is not None else None,
        utilization=str(raw["utilization"]) if raw.get("utilization") is not None else None,
    )


def load_catalog(path: Path | None = None) -> AfscCatalog:
    catalog_path = path or CATALOG_PATH
    with catalog_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    families = {
        pattern: _parse_family(pattern, spec)
        for pattern, spec in data.get("families", {}).items()
    }
    return AfscCatalog(
        version=str(data["version"]),
        sources=tuple(data.get("sources", [])),
        career_groups={str(k): v for k, v in data.get("career_groups", {}).items()},
        career_fields={str(k): v for k, v in data.get("career_fields", {}).items()},
        families=families,
        shorthands={str(k).upper(): v for k, v in data.get("shorthands", {}).items()},
    )


@lru_cache
def get_catalog() -> AfscCatalog:
    return load_catalog()
