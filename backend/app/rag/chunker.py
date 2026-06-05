# Status: [planned]

from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    chunk_text: str
    chunk_index: int
    token_count: int
    metadata: dict[str, str] = Field(default_factory=dict)


def chunk_document(text: str, *, chunk_size: int = 700, overlap: int = 100) -> list[TextChunk]:
    raise NotImplementedError("TODO: split document text into overlapping semantic chunks")
