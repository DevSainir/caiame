from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from core.deps import CourseSvc, OptionalUser, QuestionSvc, ReviewSvc, SyllabusSvc
from models.enums import Audience
from schemas.course import CourseDetailOut, CoursePageOut
from schemas.question import QuestionListOut
from schemas.review import ReviewPageOut
from schemas.syllabus import SyllabusOut
from services.course import CourseNotFoundError

router = APIRouter(prefix="/courses", tags=["Courses"])

CourseSlug = Annotated[str, Path(max_length=120, description="Course slug.")]


def _not_found() -> HTTPException:
    """The one answer for a slug that is not a published course."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="course_not_found")


@router.get(
    "",
    response_model=CoursePageOut,
    responses={200: {"description": "One page of published courses matching the filters."}},
)
async def list_courses(
    svc: CourseSvc,
    specialization: Annotated[str | None, Query(description="Specialization slug.")] = None,
    accreditation: Annotated[str | None, Query(description="Accreditation slug.")] = None,
    audience: Annotated[Audience | None, Query(description="Who the course is for.")] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=48)] = 12,
) -> CoursePageOut:
    """List published courses for the public catalogue."""
    return await svc.list_catalog(
        specialization_slug=specialization,
        accreditation_slug=accreditation,
        audience=audience,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/{slug}",
    response_model=CourseDetailOut,
    responses={
        200: {"description": "The course behind this slug."},
        404: {"description": "No published course answers to this slug."},
    },
)
async def get_course(
    svc: CourseSvc,
    slug: CourseSlug,
) -> CourseDetailOut:
    """Return one published course for its own page."""
    try:
        return await svc.get_course(slug=slug)
    except CourseNotFoundError as error:
        raise _not_found() from error


@router.get(
    "/{slug}/syllabus",
    response_model=SyllabusOut,
    responses={
        200: {"description": "Modules and works of the course, with the caller's progress."},
        404: {"description": "No published course answers to this slug."},
    },
)
async def get_syllabus(svc: SyllabusSvc, viewer: OptionalUser, slug: CourseSlug) -> SyllabusOut:
    """Return the outline of one course; a guest sees it with nothing started."""
    try:
        return await svc.get_syllabus(slug=slug, user_id=viewer.id if viewer else None)
    except CourseNotFoundError as error:
        raise _not_found() from error


@router.get(
    "/{slug}/reviews",
    response_model=ReviewPageOut,
    responses={
        200: {"description": "One page of reviews plus the rating summary."},
        404: {"description": "No published course answers to this slug."},
    },
)
async def list_reviews(
    svc: ReviewSvc,
    slug: CourseSlug,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=20)] = 3,
) -> ReviewPageOut:
    """Return one page of reviews for a published course."""
    try:
        return await svc.list_for_course(slug=slug, page=page, size=size)
    except CourseNotFoundError as error:
        raise _not_found() from error


@router.get(
    "/{slug}/questions",
    response_model=QuestionListOut,
    responses={
        200: {"description": "Every question shown under the course."},
        404: {"description": "No published course answers to this slug."},
    },
)
async def list_questions(svc: QuestionSvc, slug: CourseSlug) -> QuestionListOut:
    """Return the questions and answers shown in the discussion block."""
    try:
        return await svc.list_for_course(slug=slug)
    except CourseNotFoundError as error:
        raise _not_found() from error
