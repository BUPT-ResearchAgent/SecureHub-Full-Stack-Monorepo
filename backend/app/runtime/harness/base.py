# Status: real

from time import perf_counter
from typing import Any

from pydantic import BaseModel

from app.runtime.harness.context import HarnessContext
from app.runtime.harness.errors import InsufficientEvidence, QualityRejected
from app.runtime.harness.types import BaseSkill


class Harness:
    def __init__(self, retriever: Any, llm: Any, quality_checker: Any, storage_service: Any) -> None:
        self.retriever = retriever
        self.llm = llm
        self.quality_checker = quality_checker
        self.storage_service = storage_service

    async def run(self, skill: BaseSkill, raw_input: dict[str, Any], ctx: HarnessContext) -> BaseModel:
        started = perf_counter()
        contract = skill.contract
        agent_id = skill.agent_name
        skill_id = skill.name

        await ctx.emit(
            "progress",
            {
                "node_name": "validate",
                "agent_id": agent_id,
                "skill_id": skill_id,
                "percentage": 5,
                "status": "running",
            },
        )
        inp = contract.input_schema.model_validate(raw_input)
        query = getattr(inp, "query")
        domain = getattr(inp, "domain", None) or contract.required_domains[0]

        await ctx.emit(
            "progress",
            {
                "node_name": "retrieve",
                "agent_id": agent_id,
                "skill_id": skill_id,
                "percentage": 20,
                "status": "running",
            },
        )
        hits = await self.retriever.retrieve(query, domain=domain, top_k=8)
        if len(hits) < contract.evidence_floor:
            raise InsufficientEvidence(
                f"{skill.name} requires at least {contract.evidence_floor} evidence chunks, got {len(hits)}"
            )

        ctx.evidence_chunk_ids = [str(hit.chunk_id) for hit in hits]
        await ctx.emit("evidence", [hit.to_dto().model_dump(mode="json") for hit in hits])

        await ctx.emit(
            "progress",
            {
                "node_name": "compose",
                "agent_id": agent_id,
                "skill_id": skill_id,
                "percentage": 45,
                "status": "running",
            },
        )
        ctx.llm = self.llm
        ctx.quality_checker = self.quality_checker
        ctx.storage_service = self.storage_service
        out = await skill.run(inp, ctx)
        out = contract.output_schema.model_validate(out.model_dump())

        quality_score = getattr(out, "quality_score", None)
        if contract.quality_check:
            await ctx.emit(
                "progress",
                {
                    "node_name": "quality_check",
                    "agent_id": agent_id,
                    "skill_id": skill_id,
                    "percentage": 75,
                    "status": "running",
                },
            )
            quality_score = await self.quality_checker.check(out, hits)
            if quality_score < 0:
                raise QualityRejected(f"{skill.name} failed quality check: {quality_score}")
            if hasattr(out, "quality_score"):
                out.quality_score = quality_score

        artifact = getattr(out, "artifact", None)
        if artifact is not None and self.storage_service is not None:
            stored = await self.storage_service.put(artifact)
            await ctx.emit("artifact", stored)

        duration_ms = int((perf_counter() - started) * 1000)
        run_id = ""
        if contract.log_run:
            run_id = await ctx.log_run(
                workflow_name="course_learning",
                agent_name=agent_id,
                skill_name=skill_id,
                status="success",
                duration_ms=duration_ms,
                quality_score=quality_score,
                evidence_chunk_ids=ctx.evidence_chunk_ids,
                input_summary={"query": query, "domain": domain},
                output_summary=out.model_dump(mode="json"),
            )
        await ctx.emit(
            "trace",
            {
                "run_id": run_id,
                "parent_run_id": ctx.parent_run_id,
                "agent_name": agent_id,
                "skill_name": skill_id,
                "status": "success",
                "duration_ms": duration_ms,
                "quality_score": quality_score,
            },
        )
        await ctx.emit(
            "done",
            {
                "run_id": run_id,
                "final_output_ref": f"agent_runs/{run_id}",
                "quality_score": quality_score,
            },
        )
        return out
