from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import DifficultyLevel


class SpecializationOut(BaseModel):
    """A medical field, as offered in the catalogue filters."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str


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
    Difficulty levels ship as machine-readable values: their Russian labels belong to the
    frontend, not to the API.
    """

    specializations: list[SpecializationOut]
    accreditations: list[AccreditationOut]
    difficulties: list[DifficultyLevel]
