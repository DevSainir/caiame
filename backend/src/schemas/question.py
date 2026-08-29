from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    """One question with its answer."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    answer: str


class QuestionListOut(BaseModel):
    """
    Every question of one course at once.

    Not paged, unlike reviews: this is editorial content written by the academy, a couple
    of dozen at most, and the page opens three of them with the rest one click away.
    """

    items: list[QuestionOut]
