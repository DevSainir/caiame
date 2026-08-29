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
from repos.course import CourseRepo
from repos.refresh_token import RefreshTokenRepo
from repos.taxonomy import AccreditationRepo, SpecializationRepo
from repos.user import UserRepo
from services.auth import AuthService
from services.course import CourseService
from services.rate_limit import RateLimitService
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


def get_user_repo(session: SessionDep) -> UserRepo:
    """Provide the user repository bound to the request session."""
    return UserRepo(session)


def get_refresh_token_repo(session: SessionDep) -> RefreshTokenRepo:
    """Provide the refresh-token repository bound to the request session."""
    return RefreshTokenRepo(session)


def get_course_service(repo: Annotated[CourseRepo, Depends(get_course_repo)]) -> CourseService:
    """Provide the course service with its repository injected."""
    return CourseService(course_repo=repo)


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


CourseSvc = Annotated[CourseService, Depends(get_course_service)]
TaxonomySvc = Annotated[TaxonomyService, Depends(get_taxonomy_service)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
ClientIp = Annotated[str, Depends(get_client_ip)]
CurrentUser = Annotated[User, Depends(get_current_user)]
