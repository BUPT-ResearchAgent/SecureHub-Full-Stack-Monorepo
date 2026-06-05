# Status: [planned]

from pydantic import BaseModel, Field


class EmbeddingInput(BaseModel):
    text: str = Field(min_length=1)
    domain: str = "course_websec"


class EmbeddingBatch(BaseModel):
    items: list[EmbeddingInput]
    model: str = "bge-m3"
    dimension: int = 1024


async def embed_texts(batch: EmbeddingBatch) -> list[list[float]]:
    raise NotImplementedError("TODO: generate embeddings with BGE-M3 or XFYun embedding")
