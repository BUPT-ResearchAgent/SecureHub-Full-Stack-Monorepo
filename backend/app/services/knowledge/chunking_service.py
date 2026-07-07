# Status: real

"""Per task brief §6.1 — ChunkingService splits a document into ``chunks``
rows with ``embedding_status='pending'``. EmbeddingService later fills the
vectors.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.services.knowledge.chapter_classifier import (
    ClassifiedHeading,
    HeadingLevel,
    classify_heading,
)


@dataclass(slots=True)
class ChapterBlock:
    """A semantic textbook chapter plus all child headings and body lines."""

    title: str
    level: HeadingLevel
    start_line: int
    end_line: int
    body: str
    heading_path_root: list[str]


@dataclass(slots=True)
class ChapterChunk:
    text: str
    chunk_index_in_chapter: int
    heading_path: list[str]
    heading_level: HeadingLevel
    section_hint: str | None


@dataclass(slots=True)
class _LineTrace:
    start: int
    end: int
    section: str | None
    subsection: str | None
    level: HeadingLevel


class ChunkingService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    @staticmethod
    def split_text(text: str, *, size: int = 600, overlap: int = 100) -> list[str]:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not cleaned:
            return []
        if size <= 0:
            raise ValueError("size must be positive")
        if overlap < 0 or overlap >= size:
            raise ValueError("overlap must be non-negative and smaller than size")

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + size, len(cleaned))
            chunks.append(cleaned[start:end])
            if end == len(cleaned):
                break
            start = end - overlap
        return chunks

    @staticmethod
    def split_into_chapters(
        markdown: str,
        *,
        chapter_anchor: HeadingLevel = HeadingLevel.CHAPTER,
    ) -> list[ChapterBlock]:
        """Split MinerU Markdown by semantic Chinese textbook chapter headings."""

        lines = markdown.splitlines()
        classified: list[ClassifiedHeading] = []
        for line_no, line in enumerate(lines, start=1):
            heading = classify_heading(line, line_no=line_no)
            if heading is not None:
                classified.append(heading)

        chapter_starts = [heading for heading in classified if heading.level == chapter_anchor]
        block_level = chapter_anchor
        if not chapter_starts and chapter_anchor == HeadingLevel.CHAPTER:
            chapter_starts = [heading for heading in classified if heading.level == HeadingLevel.PART]
            block_level = HeadingLevel.PART

        if not chapter_starts:
            book_title = next(
                (heading.text for heading in classified if heading.level == HeadingLevel.BOOK),
                "unknown",
            )
            return [
                ChapterBlock(
                    title=book_title,
                    level=HeadingLevel.BOOK,
                    start_line=1,
                    end_line=len(lines),
                    body=markdown,
                    heading_path_root=[],
                )
            ]

        book_title = next(
            (heading.text for heading in classified if heading.level == HeadingLevel.BOOK),
            None,
        )
        root_path = [book_title] if book_title else []

        blocks: list[ChapterBlock] = []
        for index, start_heading in enumerate(chapter_starts):
            end_line = (
                chapter_starts[index + 1].line_no - 1
                if index + 1 < len(chapter_starts)
                else len(lines)
            )
            body = "\n".join(lines[start_heading.line_no - 1 : end_line])
            blocks.append(
                ChapterBlock(
                    title=start_heading.text,
                    level=block_level,
                    start_line=start_heading.line_no,
                    end_line=end_line,
                    body=body,
                    heading_path_root=root_path,
                )
            )
        return blocks

    def split_chapter_into_chunks(
        self,
        chapter: ChapterBlock,
        *,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ) -> list[ChapterChunk]:
        """Split one chapter while preserving nearest section/subsection metadata."""

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        cleaned_lines: list[str] = []
        traces: list[_LineTrace] = []
        current_section: str | None = None
        current_subsection: str | None = None
        current_level = chapter.level
        offset = 0

        for line_offset, line in enumerate(chapter.body.splitlines()):
            text = line.strip()
            if not text:
                continue

            heading = classify_heading(line, line_no=chapter.start_line + line_offset)
            if heading is not None:
                if heading.level == HeadingLevel.SECTION:
                    current_section = heading.text
                    current_subsection = None
                    current_level = HeadingLevel.SECTION
                elif heading.level == HeadingLevel.SUBSECTION:
                    current_subsection = heading.text
                    current_level = HeadingLevel.SUBSECTION
                elif heading.level in {HeadingLevel.CHAPTER, HeadingLevel.PART, HeadingLevel.BOOK}:
                    current_section = None
                    current_subsection = None
                    current_level = heading.level

            start = offset + (1 if cleaned_lines else 0)
            end = start + len(text)
            cleaned_lines.append(text)
            traces.append(
                _LineTrace(
                    start=start,
                    end=end,
                    section=current_section,
                    subsection=current_subsection,
                    level=current_level,
                )
            )
            offset = end

        cleaned = "\n".join(cleaned_lines)
        if not cleaned:
            return []

        chunks: list[ChapterChunk] = []
        start = 0
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            trace = _trace_for_offset(traces, start, end)
            heading_path = chapter.heading_path_root + [chapter.title]
            heading_level = chapter.level
            section_hint: str | None = None
            if trace is not None:
                if trace.section:
                    heading_path.append(trace.section)
                    heading_level = HeadingLevel.SECTION
                    section_hint = trace.section
                if trace.subsection:
                    heading_path.append(trace.subsection)
                    heading_level = HeadingLevel.SUBSECTION

            chunks.append(
                ChapterChunk(
                    text=cleaned[start:end],
                    chunk_index_in_chapter=len(chunks),
                    heading_path=heading_path,
                    heading_level=heading_level,
                    section_hint=section_hint,
                )
            )
            if end == len(cleaned):
                break
            start = end - chunk_overlap
        return chunks

    async def chunk_document(
        self,
        document_id: UUID,
        *,
        size: int = 600,
        overlap: int = 100,
        metadata: dict[str, object] | None = None,
    ) -> Sequence[UUID]:
        """Return the freshly inserted chunk ids in chunk-index order."""
        if self.session is None:
            raise ValueError("session is required to persist document chunks")
        documents = DocumentRepository(self.session)
        document = await documents.get_by_id(document_id)
        if document is None:
            raise ValueError(f"document not found: {document_id}")
        if not document.raw_text:
            return []

        chunks = ChunkRepository(self.session)
        existing = await chunks.list_by_document(document_id)
        if existing:
            return [row.id for row in existing]

        source_metadata = dict(document.metadata_ or {})
        if metadata:
            source_metadata.update(metadata)

        rows: list[Chunk] = []
        for index, text in enumerate(self.split_text(document.raw_text, size=size, overlap=overlap)):
            chunk_id = uuid5(NAMESPACE_URL, f"securehub:chunk:{document_id}:{index}")
            rows.append(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    domain=document.domain,
                    chunk_text=text,
                    chunk_index=index,
                    token_count=len(text.split()),
                    embedding=None,
                    embedding_status="pending",
                    metadata_=source_metadata | {"chunker": "fixed_window_v1"},
                )
            )

        await chunks.bulk_create(rows)
        return [row.id for row in rows]


def _trace_for_offset(
    traces: list[_LineTrace],
    start: int,
    end: int,
) -> _LineTrace | None:
    best_trace: _LineTrace | None = None
    best_overlap = -1
    for trace in traces:
        if trace.end < start:
            continue
        if trace.start > end:
            break
        overlap = min(trace.end, end) - max(trace.start, start)
        if overlap > best_overlap:
            best_trace = trace
            best_overlap = overlap
    return best_trace
