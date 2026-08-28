from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.enums import DifficultyLevel
from schemas.taxonomy import AccreditationOut, SpecializationOut


class CourseOut(BaseModel):
    """A course as the catalogue shows it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    summary: str
    cover_url: str | None
    difficulty: DifficultyLevel
    price_minor: int
    currency: str
    credit_hours: int
    duration_hours: int
    specialization: SpecializationOut
    accreditation: AccreditationOut | None


class CoursePageOut(BaseModel):
    """One page of catalogue results plus the total, so the client can show a pager."""

    items: list[CourseOut]
    total: int
    page: int
    size: int
