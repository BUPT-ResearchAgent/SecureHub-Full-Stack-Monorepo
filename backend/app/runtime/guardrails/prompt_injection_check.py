# Status: [planned]

import re
from pydantic import BaseModel, Field

PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore (all )?(previous|above) instructions",
        r"system prompt",
        r"developer message",
        r"忽略.*(以上|之前).*指令",
    ]
]


class PromptInjectionResult(BaseModel):
    detected: bool
    matched_patterns: list[str] = Field(default_factory=list)


def detect_prompt_injection(text: str) -> PromptInjectionResult:
    matched = [pattern.pattern for pattern in PROMPT_INJECTION_PATTERNS if pattern.search(text)]
    return PromptInjectionResult(detected=bool(matched), matched_patterns=matched)
