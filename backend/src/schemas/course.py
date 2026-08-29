from uuid import UUID

from pydantic import BaseModel, ConfigDict

from schemas.taxonomy import AccreditationOut, SpecializationOut


class CourseOut(BaseModel):
    """A course as the catalogue shows it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    summary: str
    cover_url: str | None
    price_minor: int
    currency: str
    credit_hours: int
    duration_hours: int
    specialization: SpecializationOut
    accreditation: AccreditationOut | None


class BenefitOut(BaseModel):
    """One reason to take the course."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    text: str


class CourseDetailOut(CourseOut):
    """
    One course as its own page shows it.

    Separate from `CourseOut` because of what the card does not need: a page of description
    and the reasons to take the course. Shipping those with every card in the catalogue
    would send twelve copies of them per request.
    """

    description: str
    benefits: list[BenefitOut]


class CoursePageOut(BaseModel):
    """One page of catalogue results plus the total, so the client can show a pager."""

    items: list[CourseOut]
    total: int
    page: int
    size: int
