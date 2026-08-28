from typing import Annotated

from fastapi import APIRouter, Query

from core.deps import CourseSvc
from models.enums import DifficultyLevel
from schemas.course import CoursePageOut

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get(
    "",
    response_model=CoursePageOut,
    responses={200: {"description": "One page of published courses matching the filters."}},
)
async def list_courses(
    svc: CourseSvc,
    specialization: Annotated[str | None, Query(description="Specialization slug.")] = None,
    accreditation: Annotated[str | None, Query(description="Accreditation slug.")] = None,
    difficulty: Annotated[DifficultyLevel | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=48)] = 12,
) -> CoursePageOut:
    """List published courses for the public catalogue."""
    return await svc.list_catalog(
        specialization_slug=specialization,
        accreditation_slug=accreditation,
        difficulty=difficulty,
        search=search,
        page=page,
        size=size,
    )
