# Status: planned

"""Per task brief §6.4 — ArtifactStorageService saves the binary side of a
generated artefact (PPT / Markdown / TTS audio / video script). It writes a
``storage_objects`` row and returns the ``object_key`` ResourceGenerationService
attaches to the ``generated_resources`` row.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class StoredArtifact:
    storage_id: str
    object_key: str
    size_bytes: int | None
    content_hash: str | None


class ArtifactStorageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(
        self,
        *,
        provider: str = "local",
        original_filename: str | None,
        mime_type: str | None,
        content: bytes,
    ) -> StoredArtifact:
        raise NotImplementedError("planned: P1")
