from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from models.enums import UserRole


class UserOut(BaseModel):
    """A user as the client may see them. The password hash never appears here."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
