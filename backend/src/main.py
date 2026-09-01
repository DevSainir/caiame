import uuid
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import Settings, get_settings
from core.logger import get_logger
from routers.router import api_router

settings = get_settings()
logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"


class DocumentationUrls(NamedTuple):
    """Addresses of the generated documentation, or nothing where it is closed."""

    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


def documentation_urls(app_settings: Settings) -> DocumentationUrls:
    """
    Where the generated documentation lives, and whether it exists at all.

    Closed in production. The schema is a complete map of the API — every administration
    route, every field, every refusal — and publishing it saves an attacker the work of
    finding out what is there. It is not a secret worth defending on its own, but it is
    also not something a public site needs to serve.
    """
    if app_settings.environment == "production":
        return DocumentationUrls(docs_url=None, redoc_url=None, openapi_url=None)
    return DocumentationUrls(docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")


documentation = documentation_urls(settings)
app = FastAPI(
    title="Caiame API",
    version="0.1.0",
    description="Continuing medical education platform.",
    docs_url=documentation.docs_url,
    redoc_url=documentation.redoc_url,
    openapi_url=documentation.openapi_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)


@app.middleware("http")
async def tag_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Give every request an identifier and make sure a failure leaves a trace.

    Without this a report of «it broke around noon» has nothing to match against: the log
    holds a stack trace with no way to tell which of the day's requests it belongs to. The
    identifier goes back in a header, so a person can quote it and land on one line of log.

    The answer to the caller stays the same either way — one sentence, no internals. What
    went wrong is written down, not shown.
    """
    request_id = str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled error %s %s request_id=%s", request.method, request.url.path, request_id
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_error"},
            headers={REQUEST_ID_HEADER: request_id},
        )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


app.include_router(api_router, prefix=settings.api_prefix)
