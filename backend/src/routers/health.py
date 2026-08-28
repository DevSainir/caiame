from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Service"])


class HealthOut(BaseModel):
    """Liveness answer."""

    status: str


@router.get("/health", response_model=HealthOut, responses={200: {"description": "Service is up."}})
async def health() -> HealthOut:
    """Report that the process is alive. Used by the container health check."""
    return HealthOut(status="ok")
