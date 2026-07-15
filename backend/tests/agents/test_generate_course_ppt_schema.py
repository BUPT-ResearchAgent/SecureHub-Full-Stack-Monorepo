# Status: real

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.agents.doc_archivist.skills.generate_course_ppt import GenerateCoursePPTOutput
from app.runtime.harness.fixtures import default_llm_output


def test_generate_course_ppt_fixture_exposes_securehub_deck_spec() -> None:
    output = GenerateCoursePPTOutput.model_validate(default_llm_output("GenerateCoursePPT"))

    assert output.render_mode == "securehub_swiss_v1"
    assert output.reveal_markdown
    assert output.slides
    assert output.deck_spec is not None
    assert 5 <= len(output.deck_spec.slides) <= 7
    for slide in output.deck_spec.slides:
        assert len(slide.title) <= 34
        assert 1 <= len(slide.bullets) <= 6
        assert slide.evidence_refs


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["deck_spec"]["slides"].clear(),
        lambda payload: payload["deck_spec"]["slides"][0].update({"title": "题" * 35}),
        lambda payload: payload["deck_spec"]["slides"][0].update({"bullets": [str(index) for index in range(7)]}),
        lambda payload: payload["deck_spec"]["slides"][0].update({"evidence_refs": []}),
        lambda payload: payload["deck_spec"]["slides"][0].update({"claim": "<script>alert(1)</script>"}),
        lambda payload: payload["deck_spec"]["slides"][0].update({"claim": "use eval(input)"}),
        lambda payload: payload["deck_spec"]["slides"][0].update({"claim": "do not assign innerHTML"}),
    ],
)
def test_generate_course_ppt_backfills_when_provider_returns_malformed_deck_spec(mutation) -> None:
    payload = deepcopy(default_llm_output("GenerateCoursePPT"))
    mutation(payload)

    output = GenerateCoursePPTOutput.model_validate(payload)

    assert output.deck_spec is not None
    assert len(output.deck_spec.slides) >= 3
    assert all(slide.evidence_refs for slide in output.deck_spec.slides)


def test_generate_course_ppt_rejects_payload_without_any_renderable_slide_source() -> None:
    with pytest.raises(ValidationError) as exc_info:
        GenerateCoursePPTOutput.model_validate(
            {
                "content": "not enough for a deck",
                "deck_spec": {"title": "坏 deck", "theme": "securehub_swiss_orange", "slides": []},
                "quality_score": 0.8,
            }
        )

    assert "PPT output requires deck_spec or legacy slides/reveal_markdown" in str(exc_info.value)


def test_generate_course_ppt_strict_schema_backfills_legacy_slide_payload() -> None:
    output = GenerateCoursePPTOutput.model_validate(
        {
            "content": "legacy PPT outline",
            "reveal_markdown": "# 旧版演示大纲\n\n- 原理\n- 防御\n---\n# 参数化查询\n\n- 固定 SQL 结构\n- 输入作为值绑定",
            "slides": [
                {"title": "旧版演示大纲", "bullets": ["原理", "防御"]},
                {"title": "参数化查询", "bullets": ["固定 SQL 结构", "输入作为值绑定"]},
            ],
            "evidence_chunk_ids": ["chunk-a", "chunk-b"],
            "quality_score": 0.8,
        }
    )

    assert output.render_mode == "securehub_swiss_v1"
    assert output.deck_spec is not None
    assert len(output.deck_spec.slides) >= 3
    assert output.deck_spec.slides[0].evidence_refs == ["chunk-a", "chunk-b"]


def test_generate_course_ppt_derives_legacy_payload_from_deck_spec() -> None:
    output = GenerateCoursePPTOutput.model_validate(
        {
            "content": "deck spec only",
            "deck_spec": {
                "title": "SQL 注入演示",
                "theme": "securehub_swiss_orange",
                "slides": [
                    {
                        "layout_id": "cover",
                        "title": "SQL 注入",
                        "claim": "把数据和 SQL 语法边界讲清楚。",
                        "bullets": ["边界", "风险", "防御"],
                        "evidence_refs": ["chunk-a"],
                    },
                    {
                        "layout_id": "statement",
                        "title": "边界失守",
                        "claim": "不可信输入被解释成查询语法。",
                        "bullets": ["拼接", "语义改变", "越权"],
                        "evidence_refs": ["chunk-a"],
                    },
                    {
                        "layout_id": "closing",
                        "title": "防御收束",
                        "claim": "参数化与白名单共同固定查询意图。",
                        "bullets": ["参数化", "白名单", "回归测试"],
                        "evidence_refs": ["chunk-b"],
                    },
                ],
            },
        }
    )

    assert output.reveal_markdown.startswith("# SQL 注入")
    assert len(output.slides) == 3
    assert output.slides[0]["evidence_refs"] == ["chunk-a"]


def test_generate_course_ppt_drops_executable_attack_code_demo() -> None:
    payload = deepcopy(default_llm_output("GenerateCoursePPT"))
    payload["deck_spec"]["slides"][3]["code_demo"] = {
        "language": "sql",
        "before": "SELECT * FROM users WHERE id = '1' OR 1=1 --",
        "after": "SELECT * FROM users WHERE id = 1 OR IF(1=1,SLEEP(5),0)",
        "caption": "Do not keep executable payloads.",
    }

    output = GenerateCoursePPTOutput.model_validate(payload)

    assert output.deck_spec is not None
    assert output.deck_spec.slides[3].code_demo is None


def test_generate_course_ppt_repairs_provider_deck_spec_drift() -> None:
    output = GenerateCoursePPTOutput.model_validate(
        {
            "deck_spec": {
                "title": "Blind SQL Injection & Time-Based Attacks",
                "theme": "securehub_swiss_orange",
                "slides": [
                    {
                        "layout_id": "cover",
                        "title": "Blind SQL Injection & Time-Based Attacks",
                        "claim": "Understanding how attackers extract data without direct output, and how to defend against it.",
                        "bullets": ["Blind SQL injection techniques", "Time-based payloads and detection"],
                        "evidence_refs": ["chunk-a"],
                    },
                    {
                        "layout_id": "timeline",
                        "title": "Attack Flow: Time-Based Injection",
                        "claim": "Step-by-step process of a time-based blind SQL injection attack.",
                        "bullets": [
                            "1. Identify injectable parameter",
                            "2. Test with ' AND SLEEP(5) -- to observe delay",
                            "3. Infer true/false conditions based on response time",
                        ],
                        "evidence_refs": ["chunk-b"],
                    },
                    {
                        "layout_id": "closing",
                        "title": "Key Takeaways",
                        "claim": "Blind SQL injection is preventable with secure coding.",
                        "bullets": ["Always use parameterized queries", "Conduct regular security testing with safe payloads"],
                        "evidence_refs": ["chunk-c"],
                    },
                ],
            },
            "render_mode": "securehub_swiss_v1",
        }
    )

    assert output.deck_spec is not None
    assert len(output.deck_spec.slides[0].title) <= 34
    assert output.deck_spec.slides[0].title.startswith("Blind SQL Injection")
    assert all("SLEEP" not in bullet for slide in output.deck_spec.slides for bullet in slide.bullets)
    assert output.reveal_markdown
