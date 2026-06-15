# Status: real

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker
from app.services.knowledge.ingestion_service import IngestionRequest, IngestionService
from app.services.storage.storage_service import StorageService


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
    storage_prefix: str = "course_websec/mineru",
) -> CourseLoadResult:
    storage = StorageService(session)
    mineru_dir = mineru_output_dir or pdf_path.with_suffix("")
    markdown_path = _find_mineru_markdown(mineru_dir)
    markdown = (
        markdown_path.read_text(encoding="utf-8")
        if markdown_path is not None
        else _fallback_markdown(pdf_path, title=title)
    )
    body_title = title or _first_heading(markdown) or pdf_path.stem
    base_key = f"{storage_prefix}/{pdf_path.stem}"

    pdf_bytes = pdf_path.read_bytes()
    pdf_key = f"{base_key}/{pdf_path.name}"
    await storage.put_bytes(
        object_key=pdf_key,
        content=pdf_bytes,
        mime_type="application/pdf",
        original_filename=pdf_path.name,
        metadata={"domain": domain, "asset_type": "original_pdf"},
    )
    pdf_hash = sha256(pdf_bytes).hexdigest()

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

    merged_metadata = {
        "platform": "mineru",
        "source_url": source_url,
        "author": "SecureHub / MinerU",
        "published_at": None,
        "license": "unknown",
        "rights_note": "PDF/MinerU 解析结果仅用于课程知识库演示；保留原始文件来源。",
        "asset_type": "markdown_full",
        "original_filename": pdf_path.name,
        "mineru_output_dir": str(mineru_dir),
        "mineru_mode": "output_dir" if markdown_path is not None else "manual_fallback",
    }
    merged_metadata.update(metadata or {})

    result = await IngestionService(session).ingest(
        IngestionRequest(
            domain=domain,
            source_type="pdf_mineru_import",
            title=body_title,
            url=source_url or f"local://{pdf_path.name}",
            raw_text=markdown,
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
            ],
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
    preferred = [output_dir / "full.md", output_dir / "output.md", output_dir / "markdown.md"]
    for path in preferred:
        if path.exists():
            return path
    markdown_files = sorted(output_dir.rglob("*.md"))
    return markdown_files[0] if markdown_files else None


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
