from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import Audience


class SpecializationOut(BaseModel):
    """A field of practice, as offered in the catalogue filters."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    audience: Audience


class AccreditationOut(BaseModel):
    """A credit scheme, as offered in the catalogue filters."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    short_code: str


class CatalogFiltersOut(BaseModel):
    """
    Everything the catalogue filter bar needs, in one response.

    Three separate requests for three dropdowns would render the same bar three times.
    Audiences ship as machine-readable values: their Russian labels belong to the
    frontend, not to the API.
    """

    specializations: list[SpecializationOut]
    accreditations: list[AccreditationOut]
    audiences: list[Audience]
