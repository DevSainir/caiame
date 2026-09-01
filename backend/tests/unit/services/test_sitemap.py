"""
The sitemap says which pages exist for a search engine — and, by omission, which do not.

Both tests here are about the omission: an address that should not be crawled and a course
that should not be advertised.
"""

from datetime import UTC, datetime

from services.sitemap import SitemapService


class FakeCatalogue:
    """The catalogue, already filtered the way the repository filters it."""

    def __init__(self, courses: list[tuple[str, datetime]]) -> None:
        self.courses = courses

    async def list_published_slugs(self) -> list[tuple[str, datetime]]:
        """Published courses only, which is what the real query returns."""
        return self.courses


async def test_the_sitemap_lists_the_home_page_and_every_published_course() -> None:
    """What a visitor can open without an account is exactly what belongs here."""
    service = SitemapService(
        course_repo=FakeCatalogue(
            [
                ("therapy", datetime(2026, 8, 30, tzinfo=UTC)),
                ("surgery", datetime(2026, 8, 31, tzinfo=UTC)),
            ]
        ),
        site_url="https://caiame.org",
    )

    sitemap = await service.build()

    assert "<loc>https://caiame.org/</loc>" in sitemap
    assert "<loc>https://caiame.org/courses/therapy</loc>" in sitemap
    assert "<lastmod>2026-08-31</lastmod>" in sitemap


async def test_pages_behind_a_session_are_not_offered_for_crawling() -> None:
    """
    Lectures, the profile and the administration have no business in a sitemap.

    Half of them would answer a crawler with a refusal, and the other half would advertise
    addresses that only make sense to somebody already signed in.
    """
    service = SitemapService(
        course_repo=FakeCatalogue([("therapy", datetime(2026, 8, 30, tzinfo=UTC))]),
        site_url="https://caiame.org",
    )

    sitemap = await service.build()

    for path in ("/lessons/", "/modules/", "/profile", "/admin"):
        assert path not in sitemap


async def test_a_trailing_slash_in_the_configured_address_does_not_double() -> None:
    """A copy-pasted address with a slash at the end must not produce «//courses/…»."""
    service = SitemapService(
        course_repo=FakeCatalogue([("therapy", datetime(2026, 8, 30, tzinfo=UTC))]),
        site_url="https://caiame.org/",
    )

    sitemap = await service.build()

    assert "https://caiame.org//" not in sitemap
