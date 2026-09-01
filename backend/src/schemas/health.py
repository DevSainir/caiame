from pydantic import BaseModel


class HealthOut(BaseModel):
    """Liveness answer: the process is running."""

    status: str


class ReadinessOut(BaseModel):
    """Whether the application can serve, and what is broken when it cannot."""

    status: str
    database: bool
    cache: bool
