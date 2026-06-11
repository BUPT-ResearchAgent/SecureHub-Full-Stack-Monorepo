# Status: real

"""RAG 检索 endpoint。

向客户端暴露统一的 ``POST /rag/search`` 接口（按 SecureHub_智能体开发计划.md §7.3 契约），
内部转发给 ``app.rag.search.search``，支持 fallback fixture 返回。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.rag import RagSearchRequest, RagSearchResponse, search

router = APIRouter()


@router.post("/rag/search", response_model=RagSearchResponse)
async def rag_search(payload: RagSearchRequest) -> RagSearchResponse:
    return await search(payload)
