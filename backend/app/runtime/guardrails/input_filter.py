# Status: [planned]

from pydantic import BaseModel, Field


class InputReview(BaseModel):
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    normalized_text: str


def review_input(text: str, *, max_length: int = 8000) -> InputReview:
    if len(text) > max_length:
        return InputReview(allowed=False, reasons=["input_too_long"], normalized_text=text[:max_length])
    return InputReview(allowed=True, normalized_text=text)
