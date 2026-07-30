from __future__ import annotations

from app.afsc.parser import validate_search_pattern


def afsc_pattern_to_sql_like(pattern: str) -> str:
    normalized = validate_search_pattern(pattern)
    return f"{normalized.replace('X', '_')}%"
