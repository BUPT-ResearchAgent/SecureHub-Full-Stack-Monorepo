# Status: mock

from pydantic import BaseModel

from app.runtime.harness.context import HarnessContext
from app.runtime.harness.types import BaseSkill, SkillContract

PROMPT_TEMPLATE = "Echo: {q}"


class EchoIn(BaseModel):
    query: str
    domain: str = "course_websec"


class EchoOut(BaseModel):
    echoed: str
    evidence_chunk_ids: list[str]
    quality_score: float


class EchoSkill(BaseSkill):
    name = "EchoSkill"
    agent_name = "_examples"
    contract = SkillContract(
        input_schema=EchoIn,
        output_schema=EchoOut,
        required_tools=["rag.retrieve", "llm.mock"],
        required_domains=["course_websec"],
        evidence_floor=1,
        guardrails=[],
        quality_check=True,
        log_run=True,
        retry={"max": 0, "backoff": 1.0},
        fallback=None,
    )

    async def run(self, inp: EchoIn, ctx: HarnessContext) -> EchoOut:
        prompt = PROMPT_TEMPLATE.format(q=inp.query)
        echoed = await ctx.llm.chat(prompt, stream=ctx.stream)
        await ctx.emit("token", {"content": echoed, "index": 0})
        return EchoOut(
            echoed=echoed,
            evidence_chunk_ids=ctx.evidence_chunk_ids,
            quality_score=0.0,
        )
