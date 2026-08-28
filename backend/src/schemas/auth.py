from pydantic import BaseModel, ConfigDict, EmailStr, Field

from schemas.user import UserOut


class RegisterIn(BaseModel):
    """Registration payload: an address and a password, nothing else."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    """Sign-in payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class SessionOut(BaseModel):
    """
    The half of a session that may live in memory.

    The refresh token is deliberately absent: it travels in an HttpOnly cookie and must
    never be readable by page scripts.
    """

    access_token: str
    # S105 reads "bearer" as a credential; it is the OAuth token type name.
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    user: UserOut
