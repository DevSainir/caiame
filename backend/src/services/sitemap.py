"""
The list of addresses worth showing a search engine.

Built from the catalogue rather than written by hand: courses are created and unpublished
from the administration now, and a hand-written list would start lying the first time
somebody does either.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from xml.sax.saxutils import escape

SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


class PublishedCourses(Protocol):
    """The one thing a sitemap needs from the catalogue."""

    async def list_published_slugs(self) -> Sequence[tuple[str, datetime]]:
        """Address and last change date of every course a visitor may open."""
        ...


class SitemapService:
    """Assembles the sitemap out of what is actually published."""

    def __init__(self, *, course_repo: PublishedCourses, site_url: str) -> None:
        self.course_repo = course_repo
        self.site_url = site_url.rstrip("/")

    async def build(self) -> str:
        """
        The whole sitemap as one XML document.

        Only pages a visitor can open without an account are listed. The lecture pages, the
        profile and the administration are not addresses a search engine has any business
        knowing, and half of them would answer with a refusal anyway.
        """
        courses = await self.course_repo.list_published_slugs()
        entries = [f"{self.site_url}/"] + [f"{self.site_url}/courses/{slug}" for slug, _ in courses]
        dates = [None] + [changed for _, changed in courses]
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<urlset xmlns="{SITEMAP_NAMESPACE}">']
        for url, changed in zip(entries, dates, strict=True):
            lines.append("  <url>")
            lines.append(f"    <loc>{escape(url)}</loc>")
            if changed is not None:
                lines.append(f"    <lastmod>{changed.date().isoformat()}</lastmod>")
            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines)
