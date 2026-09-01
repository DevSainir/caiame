from fastapi import APIRouter, Response

from core.deps import SitemapSvc

router = APIRouter(tags=["Service"])


@router.get(
    "/sitemap.xml",
    response_class=Response,
    responses={
        200: {
            "description": "Addresses a search engine may crawl.",
            "content": {"application/xml": {}},
        }
    },
)
async def sitemap(svc: SitemapSvc) -> Response:
    """
    The sitemap, assembled from the courses that are actually published.

    Served by the application rather than shipped as a file with the frontend: the
    catalogue changes from the administration, and a file in the build would go stale the
    first time somebody publishes a course.
    """
    return Response(content=await svc.build(), media_type="application/xml")
