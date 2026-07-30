from __future__ import annotations

from app.afsc.catalog import AfscCatalog, get_catalog
from app.afsc.models import ParsedAFSC, ResolvedAFSC
from app.afsc.parser import parse_member_afsc, validate_search_pattern
from app.afsc.resolver import resolve, search_highlight_labels


class AfscEngine:
    def __init__(self, catalog: AfscCatalog | None = None) -> None:
        self._catalog = catalog or get_catalog()

    @property
    def ruleset_version(self) -> str:
        return self._catalog.version

    @property
    def catalog(self) -> AfscCatalog:
        return self._catalog

    def validate_member_afsc(self, code: str) -> ParsedAFSC:
        return parse_member_afsc(code, self._catalog)

    def validate_search(self, pattern: str) -> str:
        return validate_search_pattern(pattern)

    def resolve(self, code: str) -> ResolvedAFSC:
        return resolve(code, self._catalog)

    def search_labels(self, pattern: str) -> list[str]:
        normalized = validate_search_pattern(pattern)
        return search_highlight_labels(normalized, self._catalog)


_engine: AfscEngine | None = None


def get_afsc_engine() -> AfscEngine:
    global _engine
    if _engine is None:
        _engine = AfscEngine()
    return _engine
