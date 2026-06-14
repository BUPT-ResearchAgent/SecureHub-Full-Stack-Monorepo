# Status: real

"""防幻觉回归：无证据场景下，Harness / skill 应当拒绝生成并抛出 InsufficientEvidence。"""

from __future__ import annotations

import asyncio

import pytest

from app.agents._examples.echo_skill import EchoSkill
from app.runtime.harness import Harness, HarnessConfig, HarnessContext
from app.runtime.harness.errors import InsufficientEvidence
from app.runtime.harness.fixtures import MockLLM, MockQualityCheck, MockRetriever


def test_empty_index_triggers_evidence_floor_guard():
    async def go():
        retriever = MockRetriever([])
        llm = MockLLM()
        harness = Harness(retriever=retriever, llm=llm, quality_checker=MockQualityCheck(), storage_service=None)
        ctx = HarnessContext(config=HarnessConfig(min_evidence=3, mock_mode=True))
        with pytest.raises(InsufficientEvidence):
            await harness.run(EchoSkill(), {"query": "generate exploit for CVE-9999-9999"}, ctx)
        assert llm.calls == []

    asyncio.run(go())
