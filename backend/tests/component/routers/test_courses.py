"""The catalogue endpoints, with the database replaced and everything else real."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core import deps
from main import app
from models.enums import Audience, CourseUnitKind
from tests.support.factories import (
    make_accreditation,
    make_benefit,
    make_course,
    make_question,
    make_review,
    make_specialization,
    make_unit,
)
from tests.support.fakes import (
    FakeAccreditationRepo,
    FakeBenefitRepo,
    FakeCourseRepo,
    FakeQuestionRepo,
    FakeReviewRepo,
    FakeSpecializationRepo,
    FakeSyllabusRepo,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """The app with in-memory repositories in place of the database."""
    specialization = make_specialization()
    accreditation = make_accreditation()
    courses = [
        make_course(
            slug="therapy",
            title="Therapy",
            specialization=specialization,
            accreditation=accreditation,
        ),
        make_course(
            slug="palliative-care",
            title="Palliative care",
            specialization=make_specialization(
                slug="palliative-care", name="Palliative care", audience=Audience.NURSE
            ),
            accreditation=accreditation,
        ),
    ]

    units = [
        make_unit(title="Приём терапевта", course_id=courses[0].id),
        make_unit(title="Итоговое тестирование", kind=CourseUnitKind.TEST, course_id=courses[0].id),
    ]

    app.dependency_overrides[deps.get_course_repo] = lambda: FakeCourseRepo(courses)
    app.dependency_overrides[deps.get_benefit_repo] = lambda: FakeBenefitRepo(
        [make_benefit(title="Удобный формат")]
    )
    app.dependency_overrides[deps.get_syllabus_repo] = lambda: FakeSyllabusRepo(units)
    app.dependency_overrides[deps.get_review_repo] = lambda: FakeReviewRepo(
        [make_review(rating=5), make_review(rating=4)]
    )
    app.dependency_overrides[deps.get_question_repo] = lambda: FakeQuestionRepo([make_question()])
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
    assert payload["items"][0]["specialization"]["slug"] == "therapy"


async def test_catalog_filters_by_specialization(client: TestClient) -> None:
    """A filter in the query string narrows the list rather than being ignored."""
    response = client.get("/api/v1/courses", params={"specialization": "palliative-care"})

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["palliative-care"]


async def test_catalog_filters_by_audience(client: TestClient) -> None:
    """A nurse asking for her own courses must not be shown the ones meant for doctors."""
    response = client.get("/api/v1/courses", params={"audience": "nurse"})

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["palliative-care"]


async def test_unknown_audience_is_rejected(client: TestClient) -> None:
    """A value outside the enum is a bad request, not an empty catalogue."""
    response = client.get("/api/v1/courses", params={"audience": "impossible"})

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
    assert [item["slug"] for item in payload["specializations"]] == ["therapy"]
    assert payload["audiences"] == ["doctor", "nurse"]


async def test_a_course_page_answers_by_slug(client: TestClient) -> None:
    """The course page asks for one course and gets it with its taxonomies expanded."""
    response = client.get("/api/v1/courses/therapy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Therapy"
    assert payload["specialization"]["audience"] == "doctor"
    assert payload["description"]
    assert [item["title"] for item in payload["benefits"]] == ["Удобный формат"]


async def test_an_unknown_course_is_a_404(client: TestClient) -> None:
    """A slug nobody published answers 404, not an empty page."""
    response = client.get("/api/v1/courses/does-not-exist")

    assert response.status_code == 404


async def test_the_outline_is_public_but_the_progress_is_not(client: TestClient) -> None:
    """A visitor without a token gets the modules with nothing started, not a 401."""
    response = client.get("/api/v1/courses/therapy/syllabus")

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["modules"]] == ["Приём терапевта"]
    assert [item["title"] for item in payload["activities"]] == ["Итоговое тестирование"]
    assert payload["progress_percent"] == 0


async def test_reviews_come_with_their_summary(client: TestClient) -> None:
    """One request feeds the whole block: the list, the average and the histogram."""
    response = client.get("/api/v1/courses/therapy/reviews", params={"size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["total"] == 2
    assert payload["summary"]["average"] == 4.5


async def test_questions_answer_by_slug(client: TestClient) -> None:
    """The discussion block asks once and gets every question of the course."""
    response = client.get("/api/v1/courses/therapy/questions")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


async def test_the_outline_of_an_unknown_course_is_a_404(client: TestClient) -> None:
    """Every route under a slug answers the same way when the slug is not a course."""
    for path in ("syllabus", "reviews", "questions"):
        assert client.get(f"/api/v1/courses/does-not-exist/{path}").status_code == 404
