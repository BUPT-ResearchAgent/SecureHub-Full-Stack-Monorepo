# Status: real

"""Redacting context builder used by the canonical SkillExecutor."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class ContextBuilder:
    """Build a bounded prompt without persisting the complete prompt text."""

    def __init__(self, *, max_evidence_chars: int = 4_000, max_persona_chars: int = 800) -> None:
        self.max_evidence_chars = max_evidence_chars
        self.max_persona_chars = max_persona_chars

    def build(
        self,
        *,
        prompt_template: str,
        input_value: BaseModel,
        evidence: list[dict[str, Any]],
        persona_summary: str,
        output_model: type[BaseModel],
    ) -> str:
        snippets: list[str] = []
        remaining = self.max_evidence_chars
        for item in evidence:
            text = str(item.get("excerpt") or "")
            if not text or remaining <= 0:
                continue
            trimmed = text[:remaining]
            snippets.append(f"[{item.get('chunk_id')}] {trimmed}")
            remaining -= len(trimmed)
        evidence_text = "\n\n".join(snippets)
        output_schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
        task_instruction = json.dumps(input_value.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        rendered = prompt_template.format(
            evidence_text=evidence_text,
            persona_text=(persona_summary or "")[: self.max_persona_chars],
            task_instruction=task_instruction,
            artifact_text=json.dumps(getattr(input_value, "artifact", {}), ensure_ascii=False),
            output_schema_hint=output_schema,
        )
        return rendered


__all__ = ["ContextBuilder"]
