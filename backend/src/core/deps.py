"""
What a route names in its signature.

The wiring itself — which repository a service gets — lives in `core.providers`; this module
is the vocabulary: the session, who is asking, and one alias per service. Routes import from
here and nothing else, so a change in the wiring never reaches them.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.db import get_db_session
from core.providers import (
    SessionDep,
    get_access_service,
    get_accreditation_repo,
    get_admin_repo,
    get_administration_service,
    get_assignment_repo,
    get_assignment_service,
    get_auth_service,
    get_benefit_repo,
    get_billing_service,
    get_course_repo,
    get_course_service,
    get_enrollment_repo,
    get_enrollment_service,
    get_entitlement_repo,
    get_faq_service,
    get_grading_service,
    get_health_service,
    get_learning_service,
    get_lesson_repo,
    get_media_repo,
    get_media_service,
    get_programme_service,
    get_question_bank_service,
    get_question_repo,
    get_question_service,
    get_quiz_repo,
    get_quiz_service,
    get_rate_limit_service,
    get_refresh_token_repo,
    get_review_repo,
    get_review_service,
    get_reviewer_repo,
    get_reviewer_service,
    get_sitemap_service,
    get_specialization_repo,
    get_syllabus_repo,
    get_syllabus_service,
    get_taxonomy_service,
    get_user_repo,
    get_user_service,
)
from core.security import decode_access_token
from models.user import User
from repos.user import UserRepo
from services.access import AccessService
from services.administration import AdministrationService
from services.assignment import AssignmentService
from services.auth import AuthService
from services.billing import BillingService
from services.course import CourseService
from services.enrollment import EnrollmentService
from services.faq import FaqService
from services.grading import GradingService
from services.health import HealthService
from services.learning import LearningService
from services.media import MediaService
from services.programme import ProgrammeService
from services.question import QuestionService
from services.question_bank import QuestionBankService
from services.quiz import QuizService
from services.review import ReviewService
from services.reviewers import ReviewerService
from services.sitemap import SitemapService
from services.syllabus import SyllabusService
from services.taxonomy import TaxonomyService
from services.user import UserService

# The repository and limiter factories are re-exported on purpose. Component tests replace
# them by name through this module — `deps.get_admin_repo` — and moving the definitions to
# `providers` must not change what a test has to import. Listed in `__all__` so the linter
# knows these names are the interface and not leftovers.
__all__ = [
    "AccessSvc",
    "AdministrationSvc",
    "AssignmentSvc",
    "AuthSvc",
    "BillingSvc",
    "ClientIp",
    "CourseSvc",
    "CurrentUser",
    "EnrollmentSvc",
    "FaqSvc",
    "GradingSvc",
    "HealthSvc",
    "LearningSvc",
    "MediaSvc",
    "OptionalUser",
    "ProgrammeSvc",
    "QuestionBankSvc",
    "QuestionSvc",
    "QuizSvc",
    "ReviewSvc",
    "ReviewerSvc",
    "SessionDep",
    "SitemapSvc",
    "SyllabusSvc",
    "TaxonomySvc",
    "UserSvc",
    "get_accreditation_repo",
    "get_admin_repo",
    "get_assignment_repo",
    "get_benefit_repo",
    "get_billing_service",
    "get_course_repo",
    "get_current_user",
    "get_db_session",
    "get_enrollment_repo",
    "get_enrollment_service",
    "get_entitlement_repo",
    "get_health_service",
    "get_lesson_repo",
    "get_media_repo",
    "get_media_service",
    "get_optional_user",
    "get_question_repo",
    "get_quiz_repo",
    "get_rate_limit_service",
    "get_refresh_token_repo",
    "get_review_repo",
    "get_reviewer_repo",
    "get_specialization_repo",
    "get_syllabus_repo",
    "get_user_repo",
]

bearer_scheme = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    """
    The caller's address, as the server sees it.

    Deliberately not read from X-Forwarded-For here: that header is attacker-controlled and
    trusting it turns every rate limit into a suggestion. Behind Nginx, uvicorn must run
    with --proxy-headers and --forwarded-allow-ips so this value is already the real client.
    """
    return request.client.host if request.client else "unknown"


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
AdministrationSvc = Annotated[AdministrationService, Depends(get_administration_service)]
ProgrammeSvc = Annotated[ProgrammeService, Depends(get_programme_service)]
AccessSvc = Annotated[AccessService, Depends(get_access_service)]
MediaSvc = Annotated[MediaService, Depends(get_media_service)]
BillingSvc = Annotated[BillingService, Depends(get_billing_service)]
HealthSvc = Annotated[HealthService, Depends(get_health_service)]
TaxonomySvc = Annotated[TaxonomyService, Depends(get_taxonomy_service)]
SitemapSvc = Annotated[SitemapService, Depends(get_sitemap_service)]
FaqSvc = Annotated[FaqService, Depends(get_faq_service)]
ReviewerSvc = Annotated[ReviewerService, Depends(get_reviewer_service)]
QuestionBankSvc = Annotated[QuestionBankService, Depends(get_question_bank_service)]
AssignmentSvc = Annotated[AssignmentService, Depends(get_assignment_service)]
GradingSvc = Annotated[GradingService, Depends(get_grading_service)]
EnrollmentSvc = Annotated[EnrollmentService, Depends(get_enrollment_service)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
ClientIp = Annotated[str, Depends(get_client_ip)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
