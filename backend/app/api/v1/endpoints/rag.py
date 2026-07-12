# Status: real

"""RAG 检索 endpoint。

向客户端暴露统一的 ``POST /rag/search`` 接口（按 SecureHub_智能体开发计划.md §7.3 契约），
fixture 只能通过 ``mode=fixture`` 显式请求；real 查询没有证据时 fail-closed。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.rag import RagSearchRequest, RagSearchResponse, search
from app.rag.search import RagSearchUnavailable

router = APIRouter()


@router.post("/rag/search", response_model=RagSearchResponse)
async def rag_search(payload: RagSearchRequest) -> RagSearchResponse:
    try:
        return await search(payload)
    except RagSearchUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "RAG_UNAVAILABLE", "message": str(exc)},
        ) from exc
