from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.deps import AuthSvc, ClientIp, CurrentUser
from schemas.auth import LoginIn, RegisterIn, SessionOut
from schemas.user import UserOut
from services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    IssuedSession,
    TokenReuseDetectedError,
)
from services.rate_limit import RateLimitExceededError

router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_COOKIE = "refresh_token"
# A readable hint, never a credential: it only says "a session cookie exists", so the SPA
# can skip the refresh call entirely for a visitor who has never signed in.
SESSION_HINT_COOKIE = "has_session"
_settings = get_settings()


def _too_many_requests(error: RateLimitExceededError) -> HTTPException:
    """Refuse with 429 and say when it is worth trying again."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="too_many_attempts",
        headers={"Retry-After": str(error.retry_after)},
    )


def _refusal(code: str) -> JSONResponse:
    """Refuse with 401 and clear the cookie without aborting the transaction."""
    refusal = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": code})
    refusal.delete_cookie(REFRESH_COOKIE, path=_settings.refresh_cookie_path)
    refusal.delete_cookie(SESSION_HINT_COOKIE, path="/")
    return refusal


def _attach_session(response: Response, issued: IssuedSession) -> SessionOut:
    """
    Put the refresh token in an HttpOnly cookie and return the part the page may hold.

    The access token goes to memory in the client; the refresh token must never be
    readable by page scripts, which is the whole reason it travels this way.
    """
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=issued.refresh_token,
        httponly=True,
        secure=_settings.cookie_secure,
        samesite="lax",
        path=_settings.refresh_cookie_path,
        expires=issued.refresh_expires_at,
    )
    response.set_cookie(
        key=SESSION_HINT_COOKIE,
        value="1",
        httponly=False,
        secure=_settings.cookie_secure,
        samesite="lax",
        path="/",
        expires=issued.refresh_expires_at,
    )
    return issued.session


@router.post(
    "/register",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Account created and signed in."},
        409: {"description": "This address already has an account."},
        422: {"description": "Malformed address or a password shorter than 8 characters."},
        429: {"description": "Too many sign-up attempts from this address."},
    },
)
async def register(
    payload: RegisterIn, response: Response, svc: AuthSvc, client_ip: ClientIp
) -> SessionOut:
    """Create a student account and start a session for it."""
    try:
        issued = await svc.register(
            email=payload.email, password=payload.password, client_ip=client_ip
        )
    except RateLimitExceededError as error:
        raise _too_many_requests(error) from error
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email_already_registered"
        ) from error
    return _attach_session(response, issued)


@router.post(
    "/login",
    response_model=SessionOut,
    responses={
        200: {"description": "Signed in."},
        401: {"description": "Wrong address or password — the two are not distinguished."},
        429: {"description": "Too many attempts for this address or from this host."},
    },
)
async def login(
    payload: LoginIn, response: Response, svc: AuthSvc, client_ip: ClientIp
) -> SessionOut:
    """Sign in with an address and a password."""
    try:
        issued = await svc.login(
            email=payload.email, password=payload.password, client_ip=client_ip
        )
    except RateLimitExceededError as error:
        raise _too_many_requests(error) from error
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        ) from error
    return _attach_session(response, issued)


@router.post(
    "/refresh",
    response_model=SessionOut,
    responses={
        200: {"description": "A new pair was issued and the presented token was spent."},
        401: {
            "description": "Token unknown, expired, or replayed — in the last case the "
            "whole family was revoked."
        },
    },
)
async def refresh(request: Request, response: Response, svc: AuthSvc) -> SessionOut | JSONResponse:
    """Rotate the refresh token and issue a new access token."""
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no_refresh_token")
    try:
        issued = await svc.refresh(raw_token)
    except TokenReuseDetectedError:
        # Returned, not raised, and that is the whole point: detecting a replay revokes the
        # token family, and that revocation is a write. The session dependency rolls the
        # transaction back on an exception, so raising here would refuse the request and
        # quietly undo the revocation, leaving the stolen session alive.
        return _refusal("refresh_token_reused")
    except InvalidRefreshTokenError:
        return _refusal("invalid_refresh_token")
    return _attach_session(response, issued)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Session ended. Answers the same way without a cookie."}},
)
async def logout(request: Request, response: Response, svc: AuthSvc) -> None:
    """End the session this cookie belongs to."""
    await svc.logout(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(REFRESH_COOKIE, path=_settings.refresh_cookie_path)
    response.delete_cookie(SESSION_HINT_COOKIE, path="/")


@router.get(
    "/me",
    response_model=UserOut,
    responses={
        200: {"description": "The signed-in account."},
        401: {"description": "No valid access token."},
    },
)
async def me(current_user: CurrentUser) -> UserOut:
    """Return the account behind the presented access token."""
    return UserOut.model_validate(current_user)
