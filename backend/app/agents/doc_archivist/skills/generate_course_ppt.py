# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateCoursePPTInput(SkillInput):
    kp_id: str | None = None


PptLayoutId = Literal["cover", "statement", "timeline", "compare", "cards", "closing"]


class PptCodeDemo(BaseModel):
    language: str = Field(default="text", max_length=24)
    before: str | None = Field(default=None, max_length=900)
    after: str | None = Field(default=None, max_length=900)
    caption: str | None = Field(default=None, max_length=120)


class PptDeckSlide(BaseModel):
    layout_id: PptLayoutId
    title: str = Field(min_length=1, max_length=34)
    claim: str = Field(min_length=1, max_length=160)
    bullets: list[str] = Field(min_length=1, max_length=6)
    code_demo: PptCodeDemo | None = None
    evidence_refs: list[str] = Field(min_length=1, max_length=6)
    speaker_note: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def drop_executable_attack_demo(self) -> "PptDeckSlide":
        if self.code_demo is not None and _unsafe_code_demo(self.code_demo):
            self.code_demo = None
        return self


def _unsafe_text(value: object) -> str | None:
    if isinstance(value, str):
        lowered = value.lower()
        for token in ("<script", "</script", "eval(", "new function", "innerhtml", "document.write", "javascript:"):
            if token in lowered:
                return token
    if isinstance(value, dict):
        for item in value.values():
            found = _unsafe_text(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _unsafe_text(item)
            if found:
                return found
    return None


def _unsafe_code_demo(value: PptCodeDemo) -> str | None:
    text = "\n".join(
        item
        for item in (value.before, value.after, value.caption)
        if isinstance(item, str)
    ).lower()
    return _unsafe_attack_text(text)


def _unsafe_attack_text(text: str) -> str | None:
    lowered = text.lower()
    for token in (
        "sleep(",
        "benchmark(",
        "union select",
        " or 1=1",
        "' or '1'='1",
        "--",
        "/*",
        "xp_cmdshell",
        "load_file(",
    ):
        if token in lowered:
            return token
    return None


class PptDeckSpec(BaseModel):
    title: str = Field(min_length=1, max_length=42)
    theme: str = Field(default="securehub_swiss_orange", max_length=48)
    slides: list[PptDeckSlide] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def reject_unsafe_dynamic_content(self) -> "PptDeckSpec":
        found = _unsafe_text(self.model_dump(mode="json"))
        if found:
            raise ValueError(f"deck_spec contains unsafe dynamic content token: {found}")
        return self


class GenerateCoursePPTOutput(SkillOutput):
    reveal_markdown: str = ""
    slides: list[dict[str, object]] = Field(default_factory=list)
    deck_spec: PptDeckSpec | None = None
    render_mode: Literal["securehub_swiss_v1"] = "securehub_swiss_v1"

    @model_validator(mode="before")
    @classmethod
    def tolerate_malformed_deck_spec_when_legacy_payload_exists(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        if normalized.get("render_mode") != "securehub_swiss_v1":
            normalized["render_mode"] = "securehub_swiss_v1"
        if "deck_spec" not in normalized or normalized.get("deck_spec") is None:
            return normalized

        try:
            normalized["deck_spec"] = PptDeckSpec.model_validate(normalized["deck_spec"])
        except ValueError:
            normalized["deck_spec"] = _coerce_deck_spec(normalized["deck_spec"])
        return normalized

    @model_validator(mode="after")
    def ensure_deck_spec_compatibility(self) -> "GenerateCoursePPTOutput":
        if self.deck_spec is not None:
            if not self.slides:
                self.slides = _legacy_slides_from_deck_spec(self.deck_spec)
            if not self.reveal_markdown:
                self.reveal_markdown = _reveal_markdown_from_deck_spec(self.deck_spec)
            return self

        source_slides = self.slides or _slides_from_reveal_markdown(self.reveal_markdown)
        if not source_slides:
            raise ValueError("PPT output requires deck_spec or legacy slides/reveal_markdown")

        evidence_refs = self.evidence_chunk_ids or ["retrieved-evidence"]
        layouts: list[PptLayoutId] = ["cover", "statement", "timeline", "compare", "cards", "closing"]
        spec_slides: list[PptDeckSlide] = []
        for index, source in enumerate(source_slides[:7]):
            title = _safe_short_text(source.get("title"), fallback=f"第 {index + 1} 页", limit=34)
            bullets = _safe_bullets(source.get("bullets") or source.get("content"))
            claim_source = source.get("claim") or source.get("summary") or (bullets[0] if bullets else title)
            spec_slides.append(
                PptDeckSlide(
                    layout_id=layouts[min(index, len(layouts) - 1)],
                    title=title,
                    claim=_safe_short_text(claim_source, fallback=title, limit=160),
                    bullets=bullets or ["结合证据链复盘本页核心概念"],
                    evidence_refs=evidence_refs[:6],
                )
            )

        while len(spec_slides) < 3:
            spec_slides.append(
                PptDeckSlide(
                    layout_id=layouts[min(len(spec_slides), len(layouts) - 1)],
                    title=f"课堂要点 {len(spec_slides) + 1}",
                    claim="结合已检索证据补充课堂讲解要点。",
                    bullets=["核心概念", "风险判断", "防御建议"],
                    evidence_refs=evidence_refs[:6],
                )
            )

        deck_title = spec_slides[0].title if spec_slides else "SecureHub 课程 PPT"
        self.deck_spec = PptDeckSpec(
            title=_safe_short_text(deck_title, fallback="SecureHub 课程 PPT", limit=42),
            theme="securehub_swiss_orange",
            slides=spec_slides,
        )
        return self


def _safe_short_text(value: object, *, fallback: str, limit: int) -> str:
    text = str(value).strip() if value is not None else ""
    if not text or _unsafe_text(text):
        text = fallback
    return text[:limit]


def _safe_bullets(value: object) -> list[str]:
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        candidates = [line.strip("-• 0123456789.").strip() for line in value.splitlines()]
    else:
        candidates = []
    bullets: list[str] = []
    for item in candidates:
        text = str(item).strip()
        if not text or _unsafe_text(text) or _unsafe_attack_text(text):
            continue
        bullets.append(text[:120])
        if len(bullets) >= 6:
            break
    return bullets


def _safe_evidence_refs(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["retrieved-evidence"]
    refs = [str(item).strip()[:128] for item in value if str(item).strip()]
    return refs[:6] or ["retrieved-evidence"]


def _safe_code_demo(value: object) -> PptCodeDemo | None:
    if not isinstance(value, dict):
        return None
    try:
        demo = PptCodeDemo.model_validate(value)
    except ValueError:
        return None
    if _unsafe_code_demo(demo):
        return None
    return demo


def _coerce_deck_spec(value: object) -> PptDeckSpec | None:
    if not isinstance(value, dict):
        return None
    raw_slides = value.get("slides")
    if not isinstance(raw_slides, list):
        return None

    layouts: list[PptLayoutId] = ["cover", "statement", "timeline", "compare", "cards", "closing"]
    slides: list[PptDeckSlide] = []
    for index, raw_slide in enumerate(raw_slides[:10]):
        if not isinstance(raw_slide, dict):
            continue
        raw_layout = raw_slide.get("layout_id")
        layout: PptLayoutId = raw_layout if raw_layout in layouts else layouts[min(index, len(layouts) - 1)]
        title = _safe_short_text(raw_slide.get("title"), fallback=f"第 {index + 1} 页", limit=34)
        bullets = _safe_bullets(raw_slide.get("bullets"))
        claim_source = raw_slide.get("claim") or (bullets[0] if bullets else title)
        slides.append(
            PptDeckSlide(
                layout_id=layout,
                title=title,
                claim=_safe_short_text(claim_source, fallback=title, limit=160),
                bullets=bullets or ["结合证据链复盘本页核心概念"],
                code_demo=_safe_code_demo(raw_slide.get("code_demo")),
                evidence_refs=_safe_evidence_refs(raw_slide.get("evidence_refs")),
                speaker_note=_safe_short_text(raw_slide.get("speaker_note"), fallback="", limit=320) or None,
            )
        )

    if len(slides) < 3:
        return None
    return PptDeckSpec(
        title=_safe_short_text(value.get("title"), fallback="SecureHub 课程 PPT", limit=42),
        theme=_safe_short_text(value.get("theme"), fallback="securehub_swiss_orange", limit=48),
        slides=slides,
    )


def _slides_from_reveal_markdown(markdown: str) -> list[dict[str, object]]:
    slides: list[dict[str, object]] = []
    for raw_slide in markdown.split("\n---\n"):
        lines = [line.strip() for line in raw_slide.splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("# ").strip() or "课程演示页"
        bullets = [line.strip("-• ").strip() for line in lines[1:] if line.startswith(("-", "•"))]
        slides.append({"title": title, "bullets": bullets})
    return slides


def _legacy_slides_from_deck_spec(deck_spec: PptDeckSpec) -> list[dict[str, object]]:
    return [
        {
            "title": slide.title,
            "claim": slide.claim,
            "bullets": slide.bullets,
            "layout_id": slide.layout_id,
            "evidence_refs": slide.evidence_refs,
        }
        for slide in deck_spec.slides
    ]


def _reveal_markdown_from_deck_spec(deck_spec: PptDeckSpec) -> str:
    markdown_slides: list[str] = []
    for slide in deck_spec.slides:
        lines = [f"# {slide.title}", "", slide.claim, ""]
        lines.extend(f"- {bullet}" for bullet in slide.bullets)
        markdown_slides.append("\n".join(lines).strip())
    return "\n---\n".join(markdown_slides)


PPT_JSON_RULES = """
Return only one JSON object. Do not wrap it in Markdown fences.
The JSON must include:
- deck_spec: a SecureHub PptDeckSpec for the trusted frontend renderer.
- render_mode: exactly "securehub_swiss_v1".
The backend will derive legacy reveal_markdown and slides from deck_spec; omit
those legacy fields unless they are short.

PptDeckSpec rules:
- deck_spec.title is the deck title.
- deck_spec.theme should be "securehub_swiss_orange" unless the evidence strongly suggests another SecureHub-safe theme token.
- deck_spec.slides must contain 5-7 slides.
- slide.layout_id must be one of: cover, statement, timeline, compare, cards, closing.
- Each slide must have title, claim, bullets, evidence_refs, and may have code_demo and speaker_note.
- evidence_refs must be non-empty and refer to retrieved evidence chunk ids or compact evidence labels from [Evidence].
- Do not cite evidence_refs only. Incorporate concrete details from [Evidence]
  into claims or bullets, such as the source topic, parameter/page context,
  defense method, rights note, or lab-safe observation.
- code_demo is inert text only, for comparison or teaching snippets. Do not include runnable exploit payloads.

Safety rules:
- Do not output HTML, CSS, JavaScript, script tags, iframe tags, event handlers, eval, innerHTML, document.write, external URLs as executable assets, or CDN references.
- Do not generate arbitrary renderer code. The frontend owns all layout and styling.
- Do not put attack payloads in code_demo. For SQL injection lessons, code_demo
  may compare vulnerable string concatenation with parameterized queries, but
  must not include SLEEP, BENCHMARK, UNION SELECT, comment markers, tautology
  payloads, file access functions, or other copyable exploit strings.
"""


PROMPT_TEMPLATE = """
You are doc_archivist generating a SecureHub course PPT artifact.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

{ppt_json_rules}

Return JSON matching:
{output_schema_hint}
""".replace("{ppt_json_rules}", PPT_JSON_RULES)


class GenerateCoursePPT(BaseSkill):
    name = "GenerateCoursePPT"
    applicable_domains = ["course_websec"]
    output_schema = GenerateCoursePPTOutput
