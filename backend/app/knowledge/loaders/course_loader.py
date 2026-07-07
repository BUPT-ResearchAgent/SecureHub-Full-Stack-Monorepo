# Status: real

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.document import Document
from app.db.session import get_sessionmaker
from app.services.knowledge.chapter_classifier import HeadingLevel
from app.services.knowledge.chunking_service import ChunkingService
from app.services.knowledge.ingestion_service import (
    IngestionRequest,
    IngestionService,
    PreChunkedItem,
)
from app.services.storage.storage_service import StorageService


MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+[\"'][^)]*[\"'])?\)"
)

TEXTBOOK_RIGHTS_NOTE = (
    "教材版权归原作者与出版社；本项目仅在 SecureHub 内部教学演示 RAG "
    "检索场景使用，不对外分发原文，展示时保留章节引用与来源标注。"
)

TEXTBOOK_METADATA: dict[str, dict[str, Any]] = {
    "crypto-basics": {
        "title_zh": "现代密码学教程（第2版）",
        "author": "谷利泽 / 郑世慧 / 杨义先",
        "publisher": "北京邮电大学出版社",
        "year": "2015",
        "isbn": "978-7-5635-4307-6",
        "domain_tag": ["crypto", "cryptography"],
        "trust_score": 0.9,
        "rights_note": TEXTBOOK_RIGHTS_NOTE,
        "license": "proprietary-educational-use",
    },
    "network-security": {
        "title_zh": "网络安全原理与实践",
        "author": "陈伟 / 李频",
        "publisher": "清华大学出版社",
        "year": "2014",
        "isbn": "978-7-302-35654-7",
        "domain_tag": ["network_security"],
        "trust_score": 0.9,
        "rights_note": TEXTBOOK_RIGHTS_NOTE,
        "license": "proprietary-educational-use",
    },
    "reverse-engineering": {
        "title_zh": "汇编语言（第3版）",
        "author": "王爽",
        "publisher": "清华大学出版社",
        "year": "2013",
        "isbn": "978-7-302-33314-2",
        "domain_tag": ["reverse", "assembly", "binary"],
        "trust_score": 0.9,
        "rights_note": TEXTBOOK_RIGHTS_NOTE,
        "license": "proprietary-educational-use",
    },
}


class CourseLoadResult(BaseModel):
    document_ids: list[UUID]
    chunk_count: int
    asset_count: int = 0
    domain: str = "course_websec"


@dataclass(slots=True)
class ManualImportItem:
    title: str
    content: str
    source_type: str = "manual_import"
    url: str | None = None
    metadata: dict[str, Any] | None = None


async def manual_import(
    items: list[ManualImportItem],
    *,
    session: AsyncSession,
    domain: str = "course_websec",
) -> CourseLoadResult:
    service = IngestionService(session)
    document_ids: list[UUID] = []
    chunk_count = 0
    asset_count = 0
    for item in items:
        result = await service.ingest(
            IngestionRequest(
                domain=domain,
                source_type=item.source_type,
                title=item.title,
                url=item.url,
                raw_text=item.content,
                metadata=item.metadata,
            )
        )
        document_ids.append(result.document_id)
        chunk_count += result.chunk_count
        asset_count += result.asset_count
    return CourseLoadResult(
        document_ids=document_ids,
        chunk_count=chunk_count,
        asset_count=asset_count,
        domain=domain,
    )


async def markdown_import(
    paths: list[Path],
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/manual",
) -> CourseLoadResult:
    storage = StorageService(session)
    service = IngestionService(session)
    document_ids: list[UUID] = []
    chunk_count = 0
    asset_count = 0
    for path in paths:
        markdown = path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(markdown)
        title = str(frontmatter.get("title") or _first_heading(body) or path.stem)
        object_key = f"{storage_prefix}/{path.name}"
        content = markdown.encode("utf-8")
        await storage.put_bytes(
            object_key=object_key,
            content=content,
            mime_type="text/markdown; charset=utf-8",
            original_filename=path.name,
            metadata={"domain": domain, "asset_type": "markdown_full"},
        )
        digest = sha256(content).hexdigest()
        metadata = {
            "platform": frontmatter.get("platform", "manual"),
            "source_url": frontmatter.get("source_url") or frontmatter.get("url"),
            "author": frontmatter.get("author", "SecureHub 手工整理"),
            "published_at": frontmatter.get("published_at"),
            "license": frontmatter.get("license", "unknown"),
            "rights_note": frontmatter.get(
                "rights_note",
                "教学演示用途；保留原始来源，不批量转载。",
            ),
            "asset_type": "markdown_full",
            "chapter": frontmatter.get("chapter"),
            "content_hash": digest,
        }
        result = await service.ingest(
            IngestionRequest(
                domain=domain,
                source_type=str(frontmatter.get("source_type", "markdown_import")),
                title=title,
                url=metadata["source_url"],
                raw_text=body,
                metadata=metadata,
                assets=[
                    {
                        "asset_type": "markdown_full",
                        "object_key": object_key,
                        "mime_type": "text/markdown; charset=utf-8",
                        "size_bytes": len(content),
                        "content_hash": digest,
                        "metadata": {"source_path": str(path), "chapter": metadata["chapter"]},
                    }
                ],
            )
        )
        document_ids.append(result.document_id)
        chunk_count += result.chunk_count
        asset_count += result.asset_count
    return CourseLoadResult(
        document_ids=document_ids,
        chunk_count=chunk_count,
        asset_count=asset_count,
        domain=domain,
    )


async def pdf_mineru_import(
    pdf_path: Path,
    *,
    session: AsyncSession,
    mineru_output_dir: Path | None = None,
    domain: str = "course_websec",
    title: str | None = None,
    source_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    storage_prefix: str = "course_websec/mineru_ingested",
    chapter_anchor: HeadingLevel = HeadingLevel.CHAPTER,
    force_reingest: bool = False,
    storage_local_root: Path | None = None,
) -> CourseLoadResult:
    storage = StorageService(session, local_root=storage_local_root)
    effective_url = source_url or f"local://{pdf_path.name}"
    pdf_bytes = pdf_path.read_bytes()
    pdf_hash = sha256(pdf_bytes).hexdigest()
    existing = await session.execute(
        select(Document).where(
            Document.domain == domain,
            Document.content_hash == pdf_hash,
        )
    )
    if not force_reingest and (existing_doc := existing.scalars().first()):
        return CourseLoadResult(
            document_ids=[existing_doc.id],
            chunk_count=0,
            asset_count=0,
            domain=domain,
        )
    if not force_reingest and effective_url:
        existing_by_url = await session.execute(
            select(Document).where(
                Document.domain == domain,
                Document.url == effective_url,
            )
        )
        if existing_doc := existing_by_url.scalars().first():
            return CourseLoadResult(
                document_ids=[existing_doc.id],
                chunk_count=0,
                asset_count=0,
                domain=domain,
            )

    mineru_dir = mineru_output_dir or pdf_path.with_suffix("")
    markdown_path = _find_mineru_markdown(mineru_dir)
    markdown = (
        markdown_path.read_text(encoding="utf-8")
        if markdown_path is not None
        else _fallback_markdown(pdf_path, title=title)
    )
    textbook_metadata = _textbook_metadata_for(pdf_path)
    merged_metadata = {
        "platform": "mineru",
        "source_url": effective_url,
        "author": "SecureHub / MinerU",
        "published_at": None,
        "license": "unknown",
        "rights_note": "PDF/MinerU 解析结果仅用于课程知识库演示；保留原始文件来源。",
        "asset_type": "markdown_full",
        "collection_mode": "manual",
        "original_filename": pdf_path.name,
        "mineru_output_dir": str(mineru_dir),
        "mineru_mode": "output_dir" if markdown_path is not None else "manual_fallback",
    }
    merged_metadata.update(textbook_metadata)
    merged_metadata.update(metadata or {})
    body_title = title or str(merged_metadata.get("title_zh") or _first_heading(markdown) or pdf_path.stem)
    base_key = f"{storage_prefix}/{pdf_path.stem}"
    _ensure_storage_target_outside_inputs(
        storage.local_root,
        base_key=base_key,
        pdf_path=pdf_path,
        mineru_dir=mineru_dir,
    )

    pdf_key = f"{base_key}/{pdf_path.name}"
    await storage.put_bytes(
        object_key=pdf_key,
        content=pdf_bytes,
        mime_type="application/pdf",
        original_filename=pdf_path.name,
        metadata={"domain": domain, "asset_type": "original_pdf"},
    )

    md_bytes = markdown.encode("utf-8")
    md_key = f"{base_key}/full.md"
    await storage.put_bytes(
        object_key=md_key,
        content=md_bytes,
        mime_type="text/markdown; charset=utf-8",
        original_filename="full.md",
        metadata={"domain": domain, "asset_type": "markdown_full"},
    )
    md_hash = sha256(md_bytes).hexdigest()
    image_assets = await _store_local_markdown_images(
        storage,
        markdown=markdown,
        markdown_path=markdown_path,
        base_key=base_key,
        domain=domain,
    )

    chunker = ChunkingService()
    chapters = chunker.split_into_chapters(markdown, chapter_anchor=chapter_anchor)
    chapter_assets: list[dict[str, Any]] = []
    pre_chunked: list[PreChunkedItem] = []
    global_chunk_index = 0
    for chapter_index, chapter in enumerate(chapters):
        chapter_bytes = chapter.body.encode("utf-8")
        chapter_key = f"{base_key}/chapters/{chapter_index:04d}_{_safe_slug(chapter.title)}.md"
        await storage.put_bytes(
            object_key=chapter_key,
            content=chapter_bytes,
            mime_type="text/markdown; charset=utf-8",
            original_filename=f"{chapter_index:04d}_{_safe_slug(chapter.title)}.md",
            metadata={"domain": domain, "asset_type": "markdown_chapter"},
        )
        chapter_asset_metadata = {
            "chapter_title": chapter.title,
            "heading_level": int(chapter.level),
            "heading_path": chapter.heading_path_root + [chapter.title],
            "start_line": chapter.start_line,
            "end_line": chapter.end_line,
            "chapter_index": chapter_index,
        }
        chapter_assets.append(
            {
                "asset_type": "markdown_chapter",
                "object_key": chapter_key,
                "mime_type": "text/markdown; charset=utf-8",
                "size_bytes": len(chapter_bytes),
                "content_hash": sha256(chapter_bytes).hexdigest(),
                "metadata": chapter_asset_metadata,
            }
        )

        for chunk in chunker.split_chapter_into_chunks(chapter):
            pre_chunked.append(
                PreChunkedItem(
                    text=chunk.text,
                    chunk_index=global_chunk_index,
                    metadata={
                        "asset_type": "markdown_chapter",
                        "asset_object_key": chapter_key,
                        "chapter": chapter.title,
                        "chapter_index": chapter_index,
                        "chunk_index_in_chapter": chunk.chunk_index_in_chapter,
                        "heading_path": chunk.heading_path,
                        "heading_level": int(chunk.heading_level),
                        "section_hint": chunk.section_hint,
                        "source_type": "pdf_mineru",
                        "book_title": body_title,
                        "title_zh": merged_metadata.get("title_zh"),
                    },
                )
            )
            global_chunk_index += 1

    result = await IngestionService(session).ingest(
        IngestionRequest(
            domain=domain,
            source_type="pdf_mineru",
            title=body_title,
            url=effective_url,
            raw_text=markdown,
            content_hash=pdf_hash,
            metadata=merged_metadata,
            assets=[
                {
                    "asset_type": "original_pdf",
                    "object_key": pdf_key,
                    "mime_type": "application/pdf",
                    "size_bytes": len(pdf_bytes),
                    "content_hash": pdf_hash,
                    "metadata": {"source_path": str(pdf_path)},
                },
                {
                    "asset_type": "markdown_full",
                    "object_key": md_key,
                    "mime_type": "text/markdown; charset=utf-8",
                    "size_bytes": len(md_bytes),
                    "content_hash": md_hash,
                    "metadata": {"source_path": str(markdown_path) if markdown_path else None},
                },
                *chapter_assets,
                *image_assets,
            ],
            pre_chunked=pre_chunked,
        )
    )
    return CourseLoadResult(
        document_ids=[result.document_id],
        chunk_count=result.chunk_count,
        asset_count=result.asset_count,
        domain=domain,
    )


async def load_course_materials(
    paths: list[Path],
    *,
    domain: str = "course_websec",
) -> CourseLoadResult:
    sm = get_sessionmaker()
    async with sm() as session:
        markdown_paths = [path for path in paths if path.suffix.lower() in {".md", ".markdown"}]
        pdf_paths = [path for path in paths if path.suffix.lower() == ".pdf"]
        document_ids: list[UUID] = []
        chunk_count = 0
        asset_count = 0
        if markdown_paths:
            result = await markdown_import(markdown_paths, session=session, domain=domain)
            document_ids.extend(result.document_ids)
            chunk_count += result.chunk_count
            asset_count += result.asset_count
        for pdf_path in pdf_paths:
            result = await pdf_mineru_import(pdf_path, session=session, domain=domain)
            document_ids.extend(result.document_ids)
            chunk_count += result.chunk_count
            asset_count += result.asset_count
        await session.commit()
        return CourseLoadResult(
            document_ids=document_ids,
            chunk_count=chunk_count,
            asset_count=asset_count,
            domain=domain,
        )


def _split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    end = markdown.find("\n---\n", 4)
    if end < 0:
        return {}, markdown
    raw = markdown[4:end]
    body = markdown[end + 5 :]
    metadata: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body


def _first_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _find_mineru_markdown(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    if output_dir.is_file() and output_dir.suffix.lower() in {".md", ".markdown"}:
        return output_dir
    if output_dir.is_file():
        return None
    preferred = [output_dir / "full.md", output_dir / "output.md", output_dir / "markdown.md"]
    for path in preferred:
        if path.exists():
            return path
    markdown_files = sorted(output_dir.rglob("*.md"))
    return markdown_files[0] if markdown_files else None


async def _store_local_markdown_images(
    storage: StorageService,
    *,
    markdown: str,
    markdown_path: Path | None,
    base_key: str,
    domain: str,
) -> list[dict[str, Any]]:
    if markdown_path is None:
        return []

    image_refs = list(dict.fromkeys(match.group("target") for match in MARKDOWN_IMAGE_RE.finditer(markdown)))
    assets: list[dict[str, Any]] = []
    for index, ref in enumerate(image_refs, start=1):
        image_path = _resolve_markdown_image(markdown_path, ref)
        if image_path is None:
            continue

        content = image_path.read_bytes()
        digest = sha256(content).hexdigest()
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        object_key = f"{base_key}/assets/{index:04d}_{image_path.name}"
        await storage.put_bytes(
            object_key=object_key,
            content=content,
            mime_type=mime_type,
            original_filename=image_path.name,
            metadata={
                "domain": domain,
                "asset_type": "page_image",
                "source_markdown": str(markdown_path),
                "markdown_ref": ref,
            },
        )
        assets.append(
            {
                "asset_type": "page_image",
                "object_key": object_key,
                "mime_type": mime_type,
                "size_bytes": len(content),
                "content_hash": digest,
                "metadata": {
                    "source_path": str(image_path),
                    "source_markdown": str(markdown_path),
                    "markdown_ref": ref,
                },
            }
        )
    return assets


def _resolve_markdown_image(markdown_path: Path, ref: str) -> Path | None:
    parsed = urlsplit(ref)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = (markdown_path.parent / unquote(parsed.path)).resolve()
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def _textbook_metadata_for(pdf_path: Path) -> dict[str, Any]:
    key = pdf_path.stem
    metadata = TEXTBOOK_METADATA.get(key)
    if metadata is None:
        metadata = TEXTBOOK_METADATA.get(pdf_path.parent.name)
    return dict(metadata or {})


def _safe_slug(value: str, *, max_length: int = 80) -> str:
    slug = re.sub(r"[\\/:*?\"<>|\s]+", "_", value.strip())
    slug = re.sub(r"_+", "_", slug).strip("._")
    if not slug:
        return "chapter"
    return slug[:max_length].rstrip("._")


def _ensure_storage_target_outside_inputs(
    local_root: Path,
    *,
    base_key: str,
    pdf_path: Path,
    mineru_dir: Path,
) -> None:
    target_dir = (local_root / base_key).resolve()
    pdf_target = (target_dir / pdf_path.name).resolve()
    md_target = (target_dir / "full.md").resolve()
    chapter_target = (target_dir / "chapters").resolve()
    pdf_source = pdf_path.resolve()
    mineru_source = mineru_dir.resolve()
    markdown_source = (mineru_source / "full.md").resolve()

    overlaps_pdf = pdf_target == pdf_source
    overlaps_markdown = markdown_source.exists() and md_target == markdown_source
    overlaps_mineru_dir = mineru_source.exists() and (
        target_dir == mineru_source
        or mineru_source in target_dir.parents
        or chapter_target == mineru_source
        or mineru_source in chapter_target.parents
    )
    if overlaps_pdf or overlaps_markdown or overlaps_mineru_dir:
        raise ValueError(
            "storage_prefix would write imported assets into the MinerU input "
            f"directory: {target_dir}"
        )


def _fallback_markdown(pdf_path: Path, *, title: str | None = None) -> str:
    mime_type = mimetypes.guess_type(pdf_path.name)[0] or "application/pdf"
    manifest = {
        "original_filename": pdf_path.name,
        "mime_type": mime_type,
        "fallback": "MinerU output not found; manual markdown stub created for ingestion.",
    }
    return (
        f"# {title or pdf_path.stem}\n\n"
        "本条目使用 MinerU 兜底流程入库：原始 PDF 已登记为 original_pdf，"
        "完整 Markdown 暂由人工摘要占位，后续可用 MinerU 输出覆盖。\n\n"
        "## 入库说明\n\n"
        "- 资产类型：original_pdf + markdown_full\n"
        "- 向量化状态：pending\n"
        "- 合规说明：仅用于课程演示，保留原文件来源。\n\n"
        "```json\n"
        f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )
