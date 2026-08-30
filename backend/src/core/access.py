"""
The access ladder, in one place.

Roles are never read in a router. A route names the rung it needs, and the rung is a
dependency: that way a new route inherits the control instead of inventing its own, and
the answer to «who may call this» is visible in the signature.

Only the two rungs the administration needs live here so far. `CourseAccess` — the right
to open a paid course — belongs to `services/billing.py::has_access` and arrives with the
payment domain; until then the material is behind a session and nothing else.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from core.deps import CurrentUser
from models.enums import UserRole
from models.user import User

STAFF_ROLES = (UserRole.ADMIN, UserRole.INSTRUCTOR)


def _forbidden() -> HTTPException:
    """
    The refusal for a signed-in account that stands on a lower rung.

    403 and not 404 on purpose: the caller is known and the route itself is no secret —
    hiding it would only make «why does nothing work» harder to answer. Existence of a
    particular course or work is a different question, and there the answer is 404.
    """
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def require_admin(current_user: CurrentUser) -> User:
    """The administration: courses, lessons, questions, access grants, accounts."""
    if current_user.role is not UserRole.ADMIN:
        raise _forbidden()
    return current_user


def require_staff(current_user: CurrentUser) -> User:
    """
    Anyone who works here: an administrator or a teacher.

    A teacher standing on this rung still sees only their own courses — that narrowing is
    the resource's own business and is checked where the resource is fetched, not here.
    """
    if current_user.role not in STAFF_ROLES:
        raise _forbidden()
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
StaffUser = Annotated[User, Depends(require_staff)]
