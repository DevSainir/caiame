from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models.enums import UserRole


class UserOut(BaseModel):
    """A user as the client may see them. The password hash never appears here."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole


class UserUpdateIn(BaseModel):
    """What the profile screen may change about an account."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=200)
