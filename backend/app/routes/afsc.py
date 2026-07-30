from fastapi import APIRouter, Depends, Query

from app.afsc import AfscEngine
from app.deps import get_afsc
from app.schemas import CatalogCodeLabel, CatalogFamilyOut, CatalogOut, ResolveOut, SearchLabelsOut

router = APIRouter(prefix="/api/afsc", tags=["afsc"])


@router.get("/catalog", response_model=CatalogOut)
def get_afsc_catalog(engine: AfscEngine = Depends(get_afsc)) -> CatalogOut:
    catalog = engine.catalog
    return CatalogOut(
        version=catalog.version,
        sources=list(catalog.sources),
        career_groups=[
            CatalogCodeLabel(code=code, label=label)
            for code, label in sorted(catalog.career_groups.items())
        ],
        career_fields=[
            CatalogCodeLabel(code=code, label=label)
            for code, label in sorted(catalog.career_fields.items())
        ],
        families=[
            CatalogFamilyOut(
                pattern=family.pattern,
                personnel_type=family.personnel_type,
                career_group=family.career_group,
                career_field=family.career_field,
                title=family.title,
                wildcard_role=family.wildcard_role,
                levels=dict(family.levels),
                suffixes=dict(family.suffixes),
                subdivision=family.subdivision,
                subdivision_title=family.subdivision_title,
                specialty_char=family.specialty_char,
                utilization=family.utilization,
            )
            for family in catalog.families.values()
        ],
    )


@router.get("/search-labels", response_model=SearchLabelsOut)
def get_search_labels(
    pattern: str = Query(..., min_length=1),
    engine: AfscEngine = Depends(get_afsc),
) -> SearchLabelsOut:
    normalized = engine.validate_search(pattern)
    return SearchLabelsOut(pattern=normalized, labels=engine.search_labels(normalized))


@router.get("/resolve", response_model=ResolveOut, include_in_schema=False)
def resolve_afsc(
    code: str = Query(..., min_length=1),
    engine: AfscEngine = Depends(get_afsc),
) -> ResolveOut:
    return ResolveOut.from_resolved(engine.resolve(code))
