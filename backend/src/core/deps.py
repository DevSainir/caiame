from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db_session
from core.security import decode_access_token
from integrations.redis import RedisCounterStore, get_redis
from models.user import User
from repos.benefit import BenefitRepo
from repos.course import CourseRepo
from repos.lesson import LessonRepo
from repos.question import QuestionRepo
from repos.quiz import QuizRepo
from repos.refresh_token import RefreshTokenRepo
from repos.review import ReviewRepo
from repos.syllabus import SyllabusRepo
from repos.taxonomy import AccreditationRepo, SpecializationRepo
from repos.user import UserRepo
from services.auth import AuthService
from services.course import CourseService
from services.learning import LearningService
from services.question import QuestionService
from services.quiz import QuizService
from services.rate_limit import RateLimitService
from services.review import ReviewService
from services.syllabus import SyllabusService
from services.taxonomy import TaxonomyService
from services.user import UserService

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_course_repo(session: SessionDep) -> CourseRepo:
    """Provide the course repository bound to the request session."""
    return CourseRepo(session)


def get_specialization_repo(session: SessionDep) -> SpecializationRepo:
    """Provide the specialization repository bound to the request session."""
    return SpecializationRepo(session)


def get_accreditation_repo(session: SessionDep) -> AccreditationRepo:
    """Provide the accreditation repository bound to the request session."""
    return AccreditationRepo(session)


def get_benefit_repo(session: SessionDep) -> BenefitRepo:
    """Provide the benefit repository bound to the request session."""
    return BenefitRepo(session)


def get_lesson_repo(session: SessionDep) -> LessonRepo:
    """Provide the lesson repository bound to the request session."""
    return LessonRepo(session)


def get_quiz_repo(session: SessionDep) -> QuizRepo:
    """Provide the quiz repository bound to the request session."""
    return QuizRepo(session)


def get_syllabus_repo(session: SessionDep) -> SyllabusRepo:
    """Provide the syllabus repository bound to the request session."""
    return SyllabusRepo(session)


def get_review_repo(session: SessionDep) -> ReviewRepo:
    """Provide the review repository bound to the request session."""
    return ReviewRepo(session)


def get_question_repo(session: SessionDep) -> QuestionRepo:
    """Provide the question repository bound to the request session."""
    return QuestionRepo(session)


def get_user_repo(session: SessionDep) -> UserRepo:
    """Provide the user repository bound to the request session."""
    return UserRepo(session)


def get_refresh_token_repo(session: SessionDep) -> RefreshTokenRepo:
    """Provide the refresh-token repository bound to the request session."""
    return RefreshTokenRepo(session)


def get_course_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    benefit_repo: Annotated[BenefitRepo, Depends(get_benefit_repo)],
) -> CourseService:
    """Provide the course service with the repositories the catalogue and the page need."""
    return CourseService(course_repo=course_repo, benefit_repo=benefit_repo)


def get_syllabus_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
) -> SyllabusService:
    """Provide the syllabus service with the course, outline and lesson repositories."""
    return SyllabusService(
        course_repo=course_repo, syllabus_repo=syllabus_repo, lesson_repo=lesson_repo
    )


def get_learning_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
) -> LearningService:
    """Provide the learning service with the course, outline and lesson repositories."""
    return LearningService(
        course_repo=course_repo, unit_repo=syllabus_repo, lesson_repo=lesson_repo
    )


def get_quiz_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    quiz_repo: Annotated[QuizRepo, Depends(get_quiz_repo)],
) -> QuizService:
    """Provide the quiz service; the outline repository is also where progress is written."""
    return QuizService(
        course_repo=course_repo,
        unit_repo=syllabus_repo,
        quiz_repo=quiz_repo,
        progress_repo=syllabus_repo,
    )


def get_review_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    review_repo: Annotated[ReviewRepo, Depends(get_review_repo)],
) -> ReviewService:
    """Provide the review service with the course and review repositories injected."""
    return ReviewService(course_repo=course_repo, review_repo=review_repo)


def get_question_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    question_repo: Annotated[QuestionRepo, Depends(get_question_repo)],
) -> QuestionService:
    """Provide the question service with the course and question repositories injected."""
    return QuestionService(course_repo=course_repo, question_repo=question_repo)


def get_taxonomy_service(
    specialization_repo: Annotated[SpecializationRepo, Depends(get_specialization_repo)],
    accreditation_repo: Annotated[AccreditationRepo, Depends(get_accreditation_repo)],
) -> TaxonomyService:
    """Provide the taxonomy service with both lookup repositories injected."""
    return TaxonomyService(
        specialization_repo=specialization_repo, accreditation_repo=accreditation_repo
    )


def get_rate_limit_service() -> RateLimitService:
    """Provide the rate limiter backed by Redis."""
    return RateLimitService(store=RedisCounterStore(get_redis()))


def get_auth_service(
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    refresh_repo: Annotated[RefreshTokenRepo, Depends(get_refresh_token_repo)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> AuthService:
    """Provide the auth service with the repositories and the limiter a session needs."""
    return AuthService(user_repo=user_repo, refresh_repo=refresh_repo, rate_limiter=rate_limiter)


def get_client_ip(request: Request) -> str:
    """
    The caller's address, as the server sees it.

    Deliberately not read from X-Forwarded-For here: that header is attacker-controlled and
    trusting it turns every rate limit into a suggestion. Behind Nginx, uvicorn must run
    with --proxy-headers and --forwarded-allow-ips so this value is already the real client.
    """
    return request.client.host if request.client else "unknown"


def get_user_service(repo: Annotated[UserRepo, Depends(get_user_repo)]) -> UserService:
    """Provide the user service with its repository injected."""
    return UserService(user_repo=repo)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
) -> User:
    """
    Resolve the bearer token to an account.

    Closed by default: anything short of a valid token for a live account is a 401, and
    every branch answers the same way so the token cannot be probed for detail.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid_credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as error:
        raise unauthorized from error

    user = await user_repo.get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
) -> User | None:
    """
    The account behind the token, or nobody.

    For pages that are public but show more to a signed-in student. A broken or expired
    token means «nobody» here rather than 401: the course page has to render for a guest,
    and refusing it would turn an expired session into a broken catalogue.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        return None
    user = await user_repo.get_by_id(UUID(payload["sub"]))
    return user if user is not None and user.is_active else None


CourseSvc = Annotated[CourseService, Depends(get_course_service)]
SyllabusSvc = Annotated[SyllabusService, Depends(get_syllabus_service)]
ReviewSvc = Annotated[ReviewService, Depends(get_review_service)]
QuestionSvc = Annotated[QuestionService, Depends(get_question_service)]
LearningSvc = Annotated[LearningService, Depends(get_learning_service)]
QuizSvc = Annotated[QuizService, Depends(get_quiz_service)]
TaxonomySvc = Annotated[TaxonomyService, Depends(get_taxonomy_service)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
ClientIp = Annotated[str, Depends(get_client_ip)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
