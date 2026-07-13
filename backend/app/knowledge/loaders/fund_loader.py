# Status: real

"""Idempotent loader for the minimal, official-source fund knowledge slice.

This loader deliberately stores programme-directory facts, not claims that a
particular annual call is open. Unknown dates remain ``未标注`` and each
recommendation must tell the learner to verify the current call at its source.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.knowledge.loaders.embed_chunks import embed_chunks
from app.repositories.fund_knowledge_repository import FUND_DOMAIN
from app.services.knowledge.ingestion_service import IngestionRequest, IngestionService, PreChunkedItem
from app.services.storage import StorageService


FUND_MANIFEST_VERSION = "fund-opportunity-v1"
FUND_HUB_NODE_ID = uuid5(NAMESPACE_URL, "securehub:fund:hub")


@dataclass(frozen=True, slots=True)
class FundSourceManifest:
    slug: str
    fund_name: str
    source_name: str
    source_url: str
    level: str
    deadline: str
    direction: str
    rights_note: str
    license: str
    collection_mode: str = "manual_official_registry"
    published_at: str = "未标注"
    updated_at: str = "未标注"

    @property
    def node_id(self) -> UUID:
        return uuid5(NAMESPACE_URL, f"securehub:fund:opportunity:{self.slug}")


# Each URL is an official programme or publisher entry point. Fields that the
# source directory does not publish are explicitly unknown rather than copied
# from the old mock research repository or guessed from past notices.
FUND_SOURCE_MANIFEST: tuple[FundSourceManifest, ...] = (
    FundSourceManifest(
        slug="nsfc-young-scientists",
        fund_name="国家自然科学基金青年科学基金项目（C类）",
        source_name="国家自然科学基金委员会",
        source_url="https://www.nsfc.gov.cn/",
        level="国家级",
        deadline="待当年项目指南公布",
        direction="网络空间安全、软件与系统安全、人工智能安全",
        rights_note="仅保存公开项目目录的事实摘要；申报条件和截止时间须以国家自然科学基金委员会当年指南为准。",
        license="official-public-information",
    ),
    FundSourceManifest(
        slug="ccf-huawei-noah",
        fund_name="CCF-华为胡杨林基金",
        source_name="中国计算机学会",
        source_url="https://www.ccf.org.cn/",
        level="企业联合基金",
        deadline="以 CCF 基金公告为准",
        direction="网络与系统安全、软件工程、人工智能与可信计算",
        rights_note="仅保存公开基金目录的事实摘要；具体方向、开放状态和截止时间须在 CCF 官方页面核验。",
        license="official-public-information",
    ),
    FundSourceManifest(
        slug="moe-industry-education",
        fund_name="教育部产学合作协同育人项目",
        source_name="教育部产学合作协同育人项目平台",
        source_url="https://cxhz.hep.com.cn/",
        level="部级产学合作",
        deadline="以项目平台批次通知为准",
        direction="网络安全实验教学、产教融合、工程实践与课程资源建设",
        rights_note="仅保存项目平台公开目录的事实摘要；合作单位、批次和申报截止时间须以平台当前通知为准。",
        license="official-public-information",
    ),
)


class FundLoadResult(BaseModel):
    manifest_version: str = FUND_MANIFEST_VERSION
    document_ids: list[UUID] = Field(default_factory=list)
    chunk_ids: list[UUID] = Field(default_factory=list)
    node_ids: list[UUID] = Field(default_factory=list)
    edge_count: int = 0
    domain: str = FUND_DOMAIN


def _source_text(item: FundSourceManifest) -> str:
    return "\n".join(
        (
            f"# {item.fund_name}",
            f"来源机构：{item.source_name}",
            f"官方来源：{item.source_url}",
            f"项目层级：{item.level}",
            f"研究方向：{item.direction}",
            f"截止时间：{item.deadline}",
            "核验要求：系统不能据此推断当前开放状态、资助金额或申请资格；请在官方来源核验。",
        )
    )


async def load_fund_opportunities(*, session: AsyncSession) -> FundLoadResult:
    """Write documents/assets/chunks/nodes/edges under ``domain=fund`` once."""
    storage = StorageService(session)
    ingestion = IngestionService(session)
    result = FundLoadResult()

    hub = await session.get(KnowledgeNode, FUND_HUB_NODE_ID)
    if hub is None:
        session.add(
            KnowledgeNode(
                id=FUND_HUB_NODE_ID,
                domain=FUND_DOMAIN,
                name="科研基金机会",
                description="由官方来源核验的科研机会目录",
                node_type="opportunity_hub",
                level=1,
                metadata_={"manifest_version": FUND_MANIFEST_VERSION},
            )
        )
        await session.flush()
    result.node_ids.append(FUND_HUB_NODE_ID)

    for item in FUND_SOURCE_MANIFEST:
        text = _source_text(item)
        asset_payload = json.dumps(
            {
                "manifest_version": FUND_MANIFEST_VERSION,
                "fund_name": item.fund_name,
                "source_name": item.source_name,
                "source_url": item.source_url,
                "deadline": item.deadline,
                "level": item.level,
                "direction": item.direction,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        object_key = f"fund/source-manifests/{item.slug}.json"
        await storage.put_bytes(
            object_key=object_key,
            content=asset_payload,
            mime_type="application/json",
            original_filename=f"{item.slug}.json",
            metadata={"domain": FUND_DOMAIN, "asset_type": "source_manifest"},
        )
        document = await ingestion.ingest(
            IngestionRequest(
                domain=FUND_DOMAIN,
                source_type="official_program_directory",
                title=item.fund_name,
                url=item.source_url,
                raw_text=text,
                metadata={
                    "platform": item.source_name,
                    "source_url": item.source_url,
                    "author": item.source_name,
                    "published_at": item.published_at,
                    "updated_at": item.updated_at,
                    "rights_note": item.rights_note,
                    "license": item.license,
                    "collection_mode": item.collection_mode,
                    "asset_type": "source_manifest",
                    "trust_score": 0.9,
                    "fund_name": item.fund_name,
                    "fund_level": item.level,
                    "deadline": item.deadline,
                    "direction": item.direction,
                    "deadline_verification_required": True,
                },
                assets=[
                    {
                        "asset_type": "source_manifest",
                        "object_key": object_key,
                        "mime_type": "application/json",
                        "size_bytes": len(asset_payload),
                        "content_hash": sha256(asset_payload).hexdigest(),
                        "metadata": {"manifest_version": FUND_MANIFEST_VERSION, "source_slug": item.slug},
                    }
                ],
                pre_chunked=[
                    PreChunkedItem(
                        text=text,
                        chunk_index=0,
                        metadata={
                            "fund_name": item.fund_name,
                            "fund_level": item.level,
                            "deadline": item.deadline,
                            "direction": item.direction,
                            "source_url": item.source_url,
                            "published_at": item.published_at,
                            "updated_at": item.updated_at,
                            "rights_note": item.rights_note,
                            "license": item.license,
                            "collection_mode": item.collection_mode,
                            "asset_type": "source_manifest",
                        },
                    )
                ],
            )
        )
        result.document_ids.append(document.document_id)
        result.chunk_ids.append(uuid5(NAMESPACE_URL, f"securehub:chunk:{document.document_id}:0"))

        node = await session.get(KnowledgeNode, item.node_id)
        if node is None:
            session.add(
                KnowledgeNode(
                    id=item.node_id,
                    domain=FUND_DOMAIN,
                    name=item.fund_name,
                    description=item.direction,
                    node_type="fund_opportunity",
                    level=2,
                    metadata_={
                        "source_url": item.source_url,
                        "deadline": item.deadline,
                        "level": item.level,
                        "manifest_version": FUND_MANIFEST_VERSION,
                    },
                )
            )
            await session.flush()
        result.node_ids.append(item.node_id)
        edge = await session.scalar(
            select(KnowledgeEdge).where(
                KnowledgeEdge.source_id == FUND_HUB_NODE_ID,
                KnowledgeEdge.target_id == item.node_id,
                KnowledgeEdge.edge_type == "contains",
            )
        )
        if edge is None:
            session.add(
                KnowledgeEdge(
                    source_id=FUND_HUB_NODE_ID,
                    target_id=item.node_id,
                    edge_type="contains",
                    weight=1.0,
                    metadata_={"manifest_version": FUND_MANIFEST_VERSION},
                )
            )
            result.edge_count += 1
    await session.flush()
    return result


async def load_and_embed_fund_opportunities(*, session: AsyncSession) -> FundLoadResult:
    """Load the manifest, commit it, then use the existing Qwen embedding job."""
    result = await load_fund_opportunities(session=session)
    await session.commit()
    # The configured EmbeddingService owns the Qwen profile selection and
    # writes the profile metadata. Do not invent vectors in this loader.
    await embed_chunks(result.chunk_ids)
    return result


async def main() -> None:
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as session:
        result = await load_and_embed_fund_opportunities(session=session)
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())


__all__ = [
    "FUND_DOMAIN",
    "FUND_MANIFEST_VERSION",
    "FUND_SOURCE_MANIFEST",
    "FundLoadResult",
    "FundSourceManifest",
    "load_and_embed_fund_opportunities",
    "load_fund_opportunities",
]
