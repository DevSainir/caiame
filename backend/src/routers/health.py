from fastapi import APIRouter, Response, status

from core.deps import HealthSvc
from schemas.health import HealthOut, ReadinessOut

router = APIRouter(tags=["Service"])


@router.get("/health", response_model=HealthOut, responses={200: {"description": "Service is up."}})
async def health() -> HealthOut:
    """
    Report that the process is alive. Read by the container health check.

    Deliberately answers without touching anything: a liveness probe that follows the
    database restarts the API whenever the database blinks.
    """
    return HealthOut(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadinessOut,
    responses={
        200: {"description": "The application can serve requests."},
        503: {"description": "Something the application depends on is not answering."},
    },
)
async def readiness(svc: HealthSvc, response: Response) -> ReadinessOut:
    """
    Whether the application can serve right now. This is what a monitor should watch.

    A process that is running but cannot reach its database answers every page with an
    error while looking perfectly alive from outside — that is the outage nobody notices
    until somebody writes in.
    """
    state = await svc.readiness()
    if state.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return state
