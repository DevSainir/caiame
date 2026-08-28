from fastapi import APIRouter

from core.deps import TaxonomySvc
from schemas.taxonomy import CatalogFiltersOut

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get(
    "/filters",
    response_model=CatalogFiltersOut,
    responses={200: {"description": "Every value the catalogue filter bar offers."}},
)
async def get_catalog_filters(svc: TaxonomySvc) -> CatalogFiltersOut:
    """Return specializations, accreditation schemes and difficulty levels in one response."""
    return await svc.get_filters()
