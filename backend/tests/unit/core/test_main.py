"""
What the application exposes before any route is asked.

Both cases here are about production being different from a laptop, and both are easy to
get wrong in the direction nobody notices until it matters.
"""

from core.config import Settings
from main import documentation_urls


def test_the_api_map_is_not_published_in_production() -> None:
    """
    The generated schema lists every administration route and every field it takes.

    Not a secret worth defending on its own — but a public site has no reason to hand out
    a map of itself, and the default is to serve one.
    """
    urls = documentation_urls(Settings(ENVIRONMENT="production", JWT_SECRET="x" * 32))

    assert urls.docs_url is None
    assert urls.redoc_url is None
    assert urls.openapi_url is None


def test_the_documentation_is_there_in_development() -> None:
    """Locally it is the fastest way to see what a route accepts, so it stays."""
    urls = documentation_urls(Settings(ENVIRONMENT="development"))

    assert urls.docs_url == "/docs"
    assert urls.openapi_url == "/openapi.json"
