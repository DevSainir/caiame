"""
Where every repository and service is put together.

Separated from `deps` when that file crossed the size at which nobody reads it top to
bottom any more. The split is by kind, not by feature: this module is the wiring — which
repository a service gets, which service a route gets — and `deps` is what the routes name
in their signatures.

Nothing here decides anything. A provider that starts making decisions belongs in a service.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db import get_db_session
from integrations.redis import RedisCounterStore, get_redis
from integrations.storage import ObjectStorage
from repos.admin import AdminRepo
from repos.assignment import AssignmentRepo
from repos.benefit import BenefitRepo
from repos.course import CourseRepo
from repos.enrollment import EnrollmentRepo
from repos.entitlement import EntitlementRepo
from repos.health import HealthRepo
from repos.lesson import LessonRepo
from repos.media import MediaRepo
from repos.question import QuestionRepo
from repos.quiz import QuizRepo
from repos.refresh_token import RefreshTokenRepo
from repos.review import ReviewRepo
from repos.reviewer import ReviewerRepo
from repos.syllabus import SyllabusRepo
from repos.taxonomy import AccreditationRepo, SpecializationRepo
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
from services.rate_limit import RateLimitService
from services.review import ReviewService
from services.reviewers import ReviewerService
from services.sitemap import SitemapService
from services.syllabus import SyllabusService
from services.taxonomy import TaxonomyService
from services.user import UserService

# One request, one transaction: the dependency owns the boundary, and every repository here
# is handed the same session.
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Everything here is meant to be imported by name: `deps` re-exports the factories that
# component tests replace, and a strict type checker treats a re-export as accidental
# unless the module says otherwise.
__all__ = [
    "SessionDep",
    "get_access_service",
    "get_accreditation_repo",
    "get_admin_repo",
    "get_administration_service",
    "get_assignment_repo",
    "get_assignment_service",
    "get_auth_service",
    "get_benefit_repo",
    "get_billing_service",
    "get_course_repo",
    "get_course_service",
    "get_enrollment_repo",
    "get_enrollment_service",
    "get_entitlement_repo",
    "get_faq_service",
    "get_grading_service",
    "get_health_service",
    "get_learning_service",
    "get_lesson_repo",
    "get_media_repo",
    "get_media_service",
    "get_object_storage",
    "get_programme_service",
    "get_question_bank_service",
    "get_question_repo",
    "get_question_service",
    "get_quiz_repo",
    "get_quiz_service",
    "get_rate_limit_service",
    "get_refresh_token_repo",
    "get_review_repo",
    "get_review_service",
    "get_reviewer_repo",
    "get_reviewer_service",
    "get_sitemap_service",
    "get_specialization_repo",
    "get_syllabus_repo",
    "get_syllabus_service",
    "get_taxonomy_service",
    "get_user_repo",
    "get_user_service",
]


def get_course_repo(session: SessionDep) -> CourseRepo:
    """Provide the course repository bound to the request session."""
    return CourseRepo(session)


def get_specialization_repo(session: SessionDep) -> SpecializationRepo:
    """Provide the specialization repository bound to the request session."""
    return SpecializationRepo(session)


def get_accreditation_repo(session: SessionDep) -> AccreditationRepo:
    """Provide the accreditation repository bound to the request session."""
    return AccreditationRepo(session)


def get_admin_repo(session: SessionDep) -> AdminRepo:
    """Provide the administration repository bound to the request session."""
    return AdminRepo(session)


def get_benefit_repo(session: SessionDep) -> BenefitRepo:
    """Provide the benefit repository bound to the request session."""
    return BenefitRepo(session)


def get_lesson_repo(session: SessionDep) -> LessonRepo:
    """Provide the lesson repository bound to the request session."""
    return LessonRepo(session)


def get_media_repo(session: SessionDep) -> MediaRepo:
    """Provide the media repository bound to the request session."""
    return MediaRepo(session)


def get_entitlement_repo(session: SessionDep) -> EntitlementRepo:
    """Provide the entitlement repository bound to the request session."""
    return EntitlementRepo(session)


def get_enrollment_repo(session: SessionDep) -> EnrollmentRepo:
    """Provide the enrollment repository bound to the request session."""
    return EnrollmentRepo(session)


def get_health_service(session: SessionDep) -> HealthService:
    """Provide the readiness check with the two dependencies it asks about."""
    return HealthService(database=HealthRepo(session), cache=get_redis())


def get_object_storage() -> ObjectStorage:
    """Provide the storage client. It holds keys and no connection, so it is cheap to build."""
    return ObjectStorage(get_settings())


def get_rate_limit_service() -> RateLimitService:
    """Provide the rate limiter backed by Redis."""
    return RateLimitService(store=RedisCounterStore(get_redis()))


def get_media_service(
    media_repo: Annotated[MediaRepo, Depends(get_media_repo)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> MediaService:
    """Provide the media service with its repository, the storage and the limiter."""
    return MediaService(
        media_repo=media_repo,
        storage=storage,
        settings=get_settings(),
        rate_limiter=rate_limiter,
    )


def get_assignment_repo(session: SessionDep) -> AssignmentRepo:
    """Provide the assignment repository bound to the request session."""
    return AssignmentRepo(session)


def get_billing_service(
    entitlement_repo: Annotated[EntitlementRepo, Depends(get_entitlement_repo)],
) -> BillingService:
    """Provide the one service that decides whether an account may open a course."""
    return BillingService(entitlement_repo=entitlement_repo)


def get_quiz_repo(session: SessionDep) -> QuizRepo:
    """Provide the quiz repository bound to the request session."""
    return QuizRepo(session)


def get_syllabus_repo(session: SessionDep) -> SyllabusRepo:
    """Provide the syllabus repository bound to the request session."""
    return SyllabusRepo(session)


def get_enrollment_service(
    enrollment_repo: Annotated[EnrollmentRepo, Depends(get_enrollment_repo)],
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
) -> EnrollmentService:
    """Provide the student's own list of courses."""
    return EnrollmentService(
        enrollment_repo=enrollment_repo,
        course_repo=course_repo,
        lesson_repo=lesson_repo,
        unit_repo=syllabus_repo,
        billing=billing,
    )


def get_review_repo(session: SessionDep) -> ReviewRepo:
    """Provide the review repository bound to the request session."""
    return ReviewRepo(session)


def get_question_repo(session: SessionDep) -> QuestionRepo:
    """Provide the question repository bound to the request session."""
    return QuestionRepo(session)


def get_user_repo(session: SessionDep) -> UserRepo:
    """Provide the user repository bound to the request session."""
    return UserRepo(session)


def get_reviewer_repo(session: SessionDep) -> ReviewerRepo:
    """Provide the repository of «who checks which course» bound to the request session."""
    return ReviewerRepo(session)


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
    billing: Annotated[BillingService, Depends(get_billing_service)],
) -> SyllabusService:
    """Provide the syllabus service with its repositories and the access check."""
    return SyllabusService(
        course_repo=course_repo,
        syllabus_repo=syllabus_repo,
        lesson_repo=lesson_repo,
        billing=billing,
    )


def get_administration_service(
    admin_repo: Annotated[AdminRepo, Depends(get_admin_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
    media_repo: Annotated[MediaRepo, Depends(get_media_repo)],
) -> AdministrationService:
    """Provide the administration service with the repositories the editor needs."""
    return AdministrationService(
        admin_repo=admin_repo,
        unit_repo=syllabus_repo,
        lesson_repo=lesson_repo,
        media_repo=media_repo,
    )


def get_programme_service(
    admin_repo: Annotated[AdminRepo, Depends(get_admin_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
    media_repo: Annotated[MediaRepo, Depends(get_media_repo)],
) -> ProgrammeService:
    """Provide the editor of one course's outline."""
    return ProgrammeService(
        admin_repo=admin_repo,
        unit_repo=syllabus_repo,
        lesson_repo=lesson_repo,
        media_repo=media_repo,
    )


def get_access_service(
    entitlement_repo: Annotated[EntitlementRepo, Depends(get_entitlement_repo)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
) -> AccessService:
    """Provide the administration view of access; the rights themselves belong to billing."""
    return AccessService(
        entitlement_repo=entitlement_repo,
        billing=billing,
        user_repo=user_repo,
        lesson_repo=lesson_repo,
        unit_repo=syllabus_repo,
    )


def get_learning_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    lesson_repo: Annotated[LessonRepo, Depends(get_lesson_repo)],
    media_repo: Annotated[MediaRepo, Depends(get_media_repo)],
    media_service: Annotated[MediaService, Depends(get_media_service)],
    enrollment_repo: Annotated[EnrollmentRepo, Depends(get_enrollment_repo)],
    completion: Annotated[EnrollmentService, Depends(get_enrollment_service)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
) -> LearningService:
    """Provide the learning service, including the two things a lecture page needs: the
    right to open it and a link to its file."""
    return LearningService(
        course_repo=course_repo,
        unit_repo=syllabus_repo,
        lesson_repo=lesson_repo,
        media_repo=media_repo,
        playback_repo=lesson_repo,
        media_service=media_service,
        enrollment_repo=enrollment_repo,
        completion=completion,
        billing=billing,
    )


def get_quiz_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    quiz_repo: Annotated[QuizRepo, Depends(get_quiz_repo)],
    completion: Annotated[EnrollmentService, Depends(get_enrollment_service)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
) -> QuizService:
    """Provide the quiz service; the outline repository is also where progress is written."""
    return QuizService(
        course_repo=course_repo,
        unit_repo=syllabus_repo,
        quiz_repo=quiz_repo,
        progress_repo=syllabus_repo,
        completion=completion,
        billing=billing,
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


def get_question_bank_service(
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    quiz_repo: Annotated[QuizRepo, Depends(get_quiz_repo)],
) -> QuestionBankService:
    """Provide the administration's side of a test: its settings and its questions."""
    return QuestionBankService(unit_repo=syllabus_repo, quiz_repo=quiz_repo)


def get_assignment_service(
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
    assignment_repo: Annotated[AssignmentRepo, Depends(get_assignment_repo)],
    enrollment_repo: Annotated[EnrollmentRepo, Depends(get_enrollment_repo)],
    media_repo: Annotated[MediaRepo, Depends(get_media_repo)],
    media_service: Annotated[MediaService, Depends(get_media_service)],
    billing: Annotated[BillingService, Depends(get_billing_service)],
) -> AssignmentService:
    """Provide the student's side of an assignment."""
    return AssignmentService(
        unit_repo=syllabus_repo,
        course_repo=course_repo,
        assignment_repo=assignment_repo,
        enrollment_repo=enrollment_repo,
        media_repo=media_repo,
        media_service=media_service,
        billing=billing,
    )


def get_grading_service(
    assignment_repo: Annotated[AssignmentRepo, Depends(get_assignment_repo)],
    syllabus_repo: Annotated[SyllabusRepo, Depends(get_syllabus_repo)],
    media_service: Annotated[MediaService, Depends(get_media_service)],
    completion: Annotated[EnrollmentService, Depends(get_enrollment_service)],
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    reviewer_repo: Annotated[ReviewerRepo, Depends(get_reviewer_repo)],
) -> GradingService:
    """Provide the reviewer's side; the outline repository is where unit progress is written."""
    return GradingService(
        assignment_repo=assignment_repo,
        progress_repo=syllabus_repo,
        completion=completion,
        media_service=media_service,
        students=user_repo,
        reviewers=reviewer_repo,
    )


def get_reviewer_service(
    admin_repo: Annotated[AdminRepo, Depends(get_admin_repo)],
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    reviewer_repo: Annotated[ReviewerRepo, Depends(get_reviewer_repo)],
) -> ReviewerService:
    """Provide the administration side of «who checks which course»."""
    return ReviewerService(course_repo=admin_repo, people=user_repo, assignments=reviewer_repo)


def get_sitemap_service(
    course_repo: Annotated[CourseRepo, Depends(get_course_repo)],
) -> SitemapService:
    """Provide the sitemap builder with the catalogue and the address of the site."""
    return SitemapService(course_repo=course_repo, site_url=get_settings().site_url)


def get_faq_service(
    admin_repo: Annotated[AdminRepo, Depends(get_admin_repo)],
    question_repo: Annotated[QuestionRepo, Depends(get_question_repo)],
) -> FaqService:
    """Provide the editor of the questions shown under a course."""
    return FaqService(course_repo=admin_repo, question_repo=question_repo)


def get_taxonomy_service(
    specialization_repo: Annotated[SpecializationRepo, Depends(get_specialization_repo)],
    accreditation_repo: Annotated[AccreditationRepo, Depends(get_accreditation_repo)],
) -> TaxonomyService:
    """Provide the taxonomy service with both lookup repositories injected."""
    return TaxonomyService(
        specialization_repo=specialization_repo, accreditation_repo=accreditation_repo
    )


def get_auth_service(
    user_repo: Annotated[UserRepo, Depends(get_user_repo)],
    refresh_repo: Annotated[RefreshTokenRepo, Depends(get_refresh_token_repo)],
    rate_limiter: Annotated[RateLimitService, Depends(get_rate_limit_service)],
) -> AuthService:
    """Provide the auth service with the repositories and the limiter a session needs."""
    return AuthService(user_repo=user_repo, refresh_repo=refresh_repo, rate_limiter=rate_limiter)


def get_user_service(repo: Annotated[UserRepo, Depends(get_user_repo)]) -> UserService:
    """Provide the user service with its repository injected."""
    return UserService(user_repo=repo)
