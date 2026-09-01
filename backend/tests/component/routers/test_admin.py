"""
The administration: who is let in, and what an identifier from another course does.

Two questions, and both of them are the whole reason this tier exists. The editing rules
themselves live in the service and are tested there.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core import deps
from main import app
from models.enums import UserRole
from services.rate_limit import RateLimitService
from tests.support.factories import make_user
from tests.support.fakes import (
    FakeAdminRepo,
    FakeCounterStore,
    FakeLessonRepo,
    FakeMediaRepo,
    FakeRefreshTokenRepo,
    FakeSyllabusRepo,
    FakeUserRepo,
)

PASSWORD = "correct-horse-battery"
ADMIN_PATHS = ("/api/v1/admin/courses",)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """The app with three accounts, one per rung of the ladder."""
    users = FakeUserRepo(
        [
            make_user(email="student@example.org", password=PASSWORD, role=UserRole.STUDENT),
            make_user(email="teacher@example.org", password=PASSWORD, role=UserRole.INSTRUCTOR),
            make_user(email="admin@example.org", password=PASSWORD, role=UserRole.ADMIN),
        ]
    )
    app.dependency_overrides[deps.get_user_repo] = lambda: users
    app.dependency_overrides[deps.get_refresh_token_repo] = lambda: FakeRefreshTokenRepo()
    app.dependency_overrides[deps.get_rate_limit_service] = lambda: RateLimitService(
        store=FakeCounterStore()
    )
    # The repositories are stood in for as well, or the route behind the rung reaches a
    # real database. On a laptop that goes unnoticed — there is a database next door and it
    # is migrated — and on a clean machine the test fails with a 500 that looks like a
    # broken access ladder, which is not what is broken.
    app.dependency_overrides[deps.get_admin_repo] = lambda: FakeAdminRepo()
    app.dependency_overrides[deps.get_syllabus_repo] = lambda: FakeSyllabusRepo([])
    app.dependency_overrides[deps.get_lesson_repo] = lambda: FakeLessonRepo()
    app.dependency_overrides[deps.get_media_repo] = lambda: FakeMediaRepo()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def token_for(client: TestClient, email: str) -> str:
    """Sign one of the fixtures in."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    access_token: str = response.json()["access_token"]
    return access_token


async def test_a_visitor_without_a_token_is_not_told_what_is_there(client: TestClient) -> None:
    """401 before anything else: the administration does not answer strangers at all."""
    for path in ADMIN_PATHS:
        assert client.get(path).status_code == 401


async def test_a_student_is_refused(client: TestClient) -> None:
    """
    403 and not 404 for a known account on a lower rung.

    The route is no secret — hiding it would only make «why does nothing work» harder to
    answer. What is hidden is the existence of a particular course, and that is a 404.
    """
    headers = {"Authorization": f"Bearer {token_for(client, 'student@example.org')}"}
    for path in ADMIN_PATHS:
        assert client.get(path, headers=headers).status_code == 403


async def test_a_teacher_is_refused_too(client: TestClient) -> None:
    """Teaching is not administering: courses, lessons and access are the admin's rung."""
    headers = {"Authorization": f"Bearer {token_for(client, 'teacher@example.org')}"}
    for path in ADMIN_PATHS:
        assert client.get(path, headers=headers).status_code == 403


async def test_an_administrator_is_let_in(client: TestClient) -> None:
    """The rung exists to let somebody through, not only to refuse."""
    headers = {"Authorization": f"Bearer {token_for(client, 'admin@example.org')}"}

    response = client.get("/api/v1/admin/courses", headers=headers)

    assert response.status_code == 200
