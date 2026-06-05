# Status: [planned]

import json
from typing import Literal

from pydantic import BaseModel


class BaseSSEEvent(BaseModel):
    event: str

    def to_sse(self) -> str:
        data = self.model_dump(exclude={"event"}, mode="json")
        return f"event: {self.event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class TokenEvent(BaseSSEEvent):
    event: Literal["token"] = "token"
    content: str


class EvidenceEvent(BaseSSEEvent):
    event: Literal["evidence"] = "evidence"
    chunk_id: str
    source: str
    excerpt: str
    reliability: float


class ProgressEvent(BaseSSEEvent):
    event: Literal["progress"] = "progress"
    node_name: str
    status: str
    agent_id: str | None = None
    skill_id: str | None = None
    percentage: int


class DoneEvent(BaseSSEEvent):
    event: Literal["done"] = "done"
    run_id: str
    final_output_ref: str | None = None
    quality_score: float | None = None


class ErrorEvent(BaseSSEEvent):
    event: Literal["error"] = "error"
    code: str
    message: str
    recoverable: bool = False


SSEEvent = TokenEvent | EvidenceEvent | ProgressEvent | DoneEvent | ErrorEvent
