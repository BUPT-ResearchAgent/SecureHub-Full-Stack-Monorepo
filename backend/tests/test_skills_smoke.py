# Status: real

"""Skill 走完整 harness 的端到端测试：

确认 9 智能体的关键 skill 在 fixture 模式下能：
- 调用成功
- 产出 evidence_chunk_ids
- 不抛 NotImplementedError
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.career_planner.skills.build_learning_persona import (
    BuildLearningPersona,
    BuildLearningPersonaInput,
)
from app.agents.competition_advisor.skills.generate_quiz import (
    GenerateQuiz,
    GenerateQuizInput,
)
from app.agents.doc_archivist.skills.generate_course_doc import (
    GenerateCourseDoc,
    GenerateCourseDocInput,
)
from app.agents.outcome_evaluator.skills.quality_check import (
    QualityCheck,
    QualityCheckInput,
)
from app.agents.task_orchestrator.skills.generate_learning_path import (
    GenerateLearningPath,
    GenerateLearningPathInput,
)
from app.runtime.harness import HarnessConfig, HarnessContext


@pytest.mark.parametrize(
    "skill_factory,inp_factory",
    [
        (BuildLearningPersona, lambda: BuildLearningPersonaInput(user_id="demo", query="SQL 注入")),
        (GenerateLearningPath, lambda: GenerateLearningPathInput(user_id="demo", query="Web 安全学习路径")),
        (GenerateCourseDoc, lambda: GenerateCourseDocInput(user_id="demo", query="SQL 注入文档", kp_id="kp-sqli")),
        (GenerateQuiz, lambda: GenerateQuizInput(user_id="demo", query="SQL 注入题库", kp_id="kp-sqli")),
        (QualityCheck, lambda: QualityCheckInput(user_id="demo", query="质量校验", artifact={"markdown": "test"})),
    ],
)
def test_skill_runs_with_fixture_evidence(skill_factory, inp_factory):
    async def go():
        skill = skill_factory()
        ctx = HarnessContext(
            user_id="demo",
            workflow_name="course_learning",
            config=HarnessConfig(mock_mode=True, llm_provider="fixture"),
        )
        # Fixture smoke must stay offline even when a developer has live
        # retrieval/provider credentials configured locally.
        with (
            patch(
                "app.agents.planned_skill.retrieve",
                new=AsyncMock(side_effect=AssertionError("fixture smoke called live retriever")),
            ),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(side_effect=AssertionError("fixture smoke called live provider")),
            ),
        ):
            out = await skill.run(inp_factory(), ctx)
        return out

    out = asyncio.run(go())
    assert out is not None
    assert len(out.evidence_chunk_ids) >= 3, "fixture evidence should be ≥ 3"
    assert hasattr(out, "quality_score")
