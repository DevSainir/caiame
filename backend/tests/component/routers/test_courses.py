"""The catalogue endpoints, with the database replaced and everything else real."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core import deps
from main import app
from tests.support.factories import make_accreditation, make_course, make_specialization
from tests.support.fakes import FakeAccreditationRepo, FakeCourseRepo, FakeSpecializationRepo


@pytest.fixture
def client() -> Iterator[TestClient]:
    """The app with in-memory repositories in place of the database."""
    specialization = make_specialization()
    accreditation = make_accreditation()
    courses = [
        make_course(
            slug="acs",
            title="Acute coronary syndrome",
            specialization=specialization,
            accreditation=accreditation,
        ),
        make_course(
            slug="stroke",
            title="Ischemic stroke",
            specialization=make_specialization(slug="neurology", name="Neurology"),
            accreditation=accreditation,
        ),
    ]

    app.dependency_overrides[deps.get_course_repo] = lambda: FakeCourseRepo(courses)
    app.dependency_overrides[deps.get_specialization_repo] = lambda: FakeSpecializationRepo(
        [specialization]
    )
    app.dependency_overrides[deps.get_accreditation_repo] = lambda: FakeAccreditationRepo(
        [accreditation]
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


async def test_catalog_returns_published_courses(client: TestClient) -> None:
    """The happy path of the main page: a list with both taxonomies expanded."""
    response = client.get("/api/v1/courses")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["specialization"]["slug"] == "cardiology"


async def test_catalog_filters_by_specialization(client: TestClient) -> None:
    """A filter in the query string narrows the list rather than being ignored."""
    response = client.get("/api/v1/courses", params={"specialization": "neurology"})

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["stroke"]


async def test_unknown_difficulty_is_rejected(client: TestClient) -> None:
    """A value outside the enum is a bad request, not an empty catalogue."""
    response = client.get("/api/v1/courses", params={"difficulty": "impossible"})

    assert response.status_code == 422


async def test_page_size_above_the_cap_is_rejected(client: TestClient) -> None:
    """The cap is declared on the route, so it is enforced before any query runs."""
    response = client.get("/api/v1/courses", params={"size": 1000})

    assert response.status_code == 422


async def test_filters_endpoint_lists_every_control(client: TestClient) -> None:
    """One request feeds the whole filter bar."""
    response = client.get("/api/v1/catalog/filters")

    assert response.status_code == 200
    payload = response.json()
    assert [item["slug"] for item in payload["specializations"]] == ["cardiology"]
    assert payload["difficulties"] == ["beginner", "intermediate", "advanced"]
