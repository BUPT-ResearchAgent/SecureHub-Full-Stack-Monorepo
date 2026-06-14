# Harness 迁移 — 现有 Skill 雏形改造审计

> 在 Codex 完成 A3（Harness 骨架）之后，成员 A 需要把现有 22 个 skill 雏形 + `base.py` + `planned_skill.py` 接入新 Harness 契约。本文件列出**每个文件的差距**，让 A 在 Day 1 不用再现场盘点。
>
> 审计基准：`.codex/AGENTS.md §8.5 Skill Harness`。
> 审计时间：2026-06-09。

---

## 1. 现状总览

| 目录 | 文件数 | 已具备 | 需补齐 |
|---|---:|---|---|
| `backend/app/agents/base.py` | 1 | `BaseAgent` / `BaseSkill` / `SkillContext` / `AgentCapability` / 三个 Exception | `SkillContract` dataclass / `HarnessContext` / SSE emit / fixture 支持 |
| `backend/app/agents/planned_skill.py` | 1 | `retrieve → prompt → xfyun_chat → safety_review → log_run` 一条龙 | **被 Harness 替代**；需要逐步迁出 |
| `backend/app/agents/<9 角色>/skills/*.py` | 22 | 每个文件含 `PROMPT_TEMPLATE` + Input/Output Pydantic + `BaseSkill.run()`，调用 `prepare_planned_skill_output()` | input_schema 注册 / SSE emit / quality_check 独立 / artifact 落库 / timeout-retry / fallback |

22 个 skill 文件分布：
- `career_planner/`：3 — `build_learning_persona` · `recommend_resources` · `update_persona`
- `competition_advisor/`：3 — `generate_competition_plan` · `generate_quiz` ⭐ · `recommend_competition`
- `doc_archivist/`：4 — `generate_course_doc` ⭐ · `generate_course_ppt` ⭐ · `generate_mindmap` ⭐ · `generate_video_storyboard` ⭐
- `hot_analyst/`：1 — `recommend_readings`
- `job_analyst/`：0（只有 `agent.py`）
- `outcome_evaluator/`：4 — `evaluate_submission` · `quality_check` ⭐ · `run_assessment` ⭐ · `update_capability`
- `policy_interpreter/`：2 — `compliance_check` · `interpret_policy`
- `task_orchestrator/`：2 — `decompose_wbs` · `generate_learning_path` ⭐
- `topic_explorer/`：3 — `generate_hands_on_lab` ⭐ · `generate_research_topic` · `recommend_readings`

⭐ = A3 P0 关键 skill；优先迁移。

---

## 2. 现有 `planned_skill.py` 与 Harness 的对照

| 阶段 | `planned_skill.py` 现状 | Harness 期望 | 差距 |
|---|---|---|---|
| 0. validate input | 仅 Pydantic 解析 | `SkillContract.input_schema` 注册 + `model_validate` | 把 input 类型挂到 `SkillContract` |
| 1. retrieve | `retrieve(query, domain, top_k=MIN_EVIDENCE)` | 同 + emit `progress("retrieve")` + emit `evidence` 事件 | **缺 SSE emit** |
| 2. evidence_floor | `if len(hits) < MIN_EVIDENCE: raise InsufficientEvidence` ✓ | `SkillContract.evidence_floor` 显式声明 + Harness 统一检查 | 把阈值从 ctx.config 移到 contract |
| 3. compose prompt | string.format ✓ | 同 | 无差距 |
| 4. LLM | `xfyun_chat(prompt, stream=ctx.stream)` | 经 `LLMClient`，含 fallback chain | **缺 fallback 抽象**；改走 §11.3 `llm/client.py` |
| 5. parse output | `model_validate_json(raw)` ✓ | 同 | 无差距 |
| 6. safety / guardrail | `safety_review(out)` ✓ | `SkillContract.guardrails: list[str]` 显式声明 | guardrail 名称列表化 |
| 7. quality_check | **缺失** —— 没有独立调 `outcome_evaluator.QualityCheck` | `SkillContract.quality_check=True` 时强制调 | **核心缺口**：必须新增 |
| 8. persist artifact | **缺失** —— 不写 `generated_resources` / `storage_objects` | Harness 在 artifact 阶段写库 + emit `artifact` | **核心缺口**：必须新增 |
| 9. log_run | `ctx.log_run(...)`，但 `SkillContext.log_run` 抛 NotImplementedError | 真实落 `agent_runs` 表 + emit `trace` | **核心缺口**：必须实现 |
| 10. timeout / retry / fallback | **缺失** | `SkillContract.timeout_seconds` / `retry` / `fallback` | 全部缺，由 Harness 包装 |
| 11. SSE 事件 | **缺失**（只支持 stream=True 的 token 概念，没有 7 事件协议） | `progress` / `evidence` / `token` / `artifact` / `trace` / `done` / `error` | **核心缺口**：全部缺 |
| 12. fixture / mock_mode | **缺失** | `SkillContract.fixtures` + `HARNESS_MOCK_MODE` | 全部缺 |

---

## 3. 每个 skill 文件需要的迁移动作（统一模板）

迁移方案：**保留 PROMPT_TEMPLATE 和 Pydantic Input/Output 不动**；改 3 处：

### 3.1 删除 `prepare_planned_skill_output()` 调用，改用 `SkillContract`

Before（典型 22 个 skill 都长这样）：

```python
class BuildLearningPersona(BaseSkill):
    name = "BuildLearningPersona"
    applicable_domains = ["course_websec"]
    output_schema = BuildLearningPersonaOutput

    async def run(self, inp, ctx) -> BuildLearningPersonaOutput:
        out = await prepare_planned_skill_output(
            self, inp, ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=BuildLearningPersonaOutput,
        )
        await ctx.log_run(...)
        return out
```

After（Harness 接管全链路）：

```python
class BuildLearningPersona(BaseSkill):
    name = "BuildLearningPersona"
    agent_name = "career_planner"
    contract = SkillContract(
        input_schema=BuildLearningPersonaInput,
        output_schema=BuildLearningPersonaOutput,
        required_tools=["rag.retrieve", "llm.xfyun"],
        required_domains=["course_websec"],
        evidence_floor=3,
        guardrails=["input_filter", "prompt_injection_check", "output_filter"],
        quality_check=True,
        log_run=True,
        fixtures={"no_llm": "fixtures/build_learning_persona.json"},
        timeout_seconds=60,
        retry={"max": 1, "backoff": 2.0},
        fallback="deepseek",
    )
    prompt_template = PROMPT_TEMPLATE
```

—— 不再写 `async def run()`；Harness 通过 `SkillContract` 自动驱动。
特殊 skill（如 `outcome_evaluator.QualityCheck`）保留 `run()`，因为它本身就是质量校验，不能再嵌套 quality_check。

### 3.2 `quality_check=False` 的例外名单

以下 skill 不走 QualityCheck（否则递归）：
- `outcome_evaluator.QualityCheck` —— 本身就是 QC
- `outcome_evaluator.UpdateCapability` —— 数据库写入，无生成
- `career_planner.UpdatePersona` —— 同上
- `task_orchestrator.DecomposeWBS` —— 结构化拆解，不属生成内容
- `task_orchestrator.GenerateLearningPath` —— DAG 生成，QC 单独按 evidence_chunk_ids ≥ 3 + 路径连通性校验

### 3.3 `artifact` 落库映射

每个生成式 skill 输出对应 `generated_resources.resource_type`（与 `docs/data-layer-v2-enums.md §8.1` 1:1）：

| Skill | resource_type |
|---|---|
| `doc_archivist.GenerateCourseDoc` | `course_doc` |
| `doc_archivist.GenerateCoursePPT` | `course_ppt` |
| `doc_archivist.GenerateMindmap` | `mindmap` |
| `doc_archivist.GenerateVideoStoryboard` | `video_storyboard` |
| `competition_advisor.GenerateQuiz` | `quiz_set` |
| `topic_explorer.GenerateHandsOnLab` | `hands_on_lab` |
| `hot_analyst.RecommendReadings` / `topic_explorer.RecommendReadings` | `reading_list` |
| `outcome_evaluator.RunAssessment` | `assessment_report` |
| `doc_archivist.GenerateProposal`（如保留）| `proposal` |

非生成式 skill（`BuildLearningPersona` / `UpdatePersona` / `UpdateCapability` / `EvaluateSubmission` / `DecomposeWBS` / `RouteTutorQuestion` / `AnalyzeHotEvent` / `AnalyzeJobMarket` / ...）**不**写 `generated_resources`；它们的输出直接进各自业务表（`user_profiles` / `user_capabilities` / `learning_events`）或 `agent_runs.output_summary`。

---

## 4. `base.py` 需要新增的字段

成员 A 在 Codex 提交 A3 后需要在 `base.py` 里新增（**不要删 SkillContext**，向后兼容）：

```python
from app.runtime.harness.types import SkillContract, HarnessContext
from app.runtime.harness.errors import InsufficientEvidence, SkillTimeout, QualityRejected, GuardrailBlocked
```

`BaseSkill` 增加可选字段：

```python
class BaseSkill(ABC):
    name: ClassVar[str]
    agent_name: ClassVar[str] = ""              # 新增；用于 agent_runs.agent_name 反查
    contract: ClassVar[SkillContract | None] = None  # 新增；优先级 > applicable_domains / output_schema
    applicable_domains: ClassVar[list[str]] = []     # 兼容旧字段
    output_schema: ClassVar[type[BaseModel] | None] = None
    prompt_template: ClassVar[str] = ""         # 新增；显式声明，不再藏在 skill body
    agent_id: UUID | str | None = None
    skill_id: UUID | str | None = None

    # 当 contract 存在时，Harness 自动驱动；否则保留旧 run()
    async def run(self, inp: BaseModel, ctx: SkillContext | HarnessContext) -> BaseModel:
        raise NotImplementedError
```

`SkillContext.log_run` 当前抛 `NotImplementedError` —— 在 A 实现 `runtime/logger.py` 时换成真实落 `agent_runs`。

---

## 5. 迁移顺序（按优先级 + 依赖关系）

1. **Wave 1（必须 Day 1 内完成）**：base.py 扩展 + planned_skill.py 标记 deprecated
2. **Wave 2（Day 1–2）**：5 个 P0 关键 skill 接 Harness：
   - `career_planner.BuildLearningPersona`
   - `task_orchestrator.GenerateLearningPath`
   - `doc_archivist.GenerateCourseDoc`
   - `competition_advisor.GenerateQuiz`
   - `outcome_evaluator.QualityCheck` + `RunAssessment`
3. **Wave 3（Day 3–4）**：其余 doc_archivist 4 个 / topic_explorer / hot_analyst 共 8 个生成式 skill
4. **Wave 4（Week 2）**：career_planner 路由 / policy_interpreter / outcome_evaluator 其余 / task_orchestrator 其余
5. **Wave 5（Week 3）**：删除 `planned_skill.py`，所有 skill 完全切换到 Harness 契约

---

## 6. 必须新加的测试用例（成员 C）

- `test_skill_harness.py`（A3 已含）—— happy + InsufficientEvidence
- `test_skill_contract_alignment.py` —— grep 所有 skill 文件 contract.input_schema 必须出现在 `__all__`
- `test_no_planned_skill_after_week_3.py` —— Wave 5 之后 `prepare_planned_skill_output` import 计数应为 0（CI 防回归）
- `test_quality_check_excluded.py` —— §3.2 排除名单的 skill 不会触发 QC 递归

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Wave 2 改 5 个核心 skill 影响演示 | 全程走 mock_mode；改完立刻跑 demo 故事回归 |
| `planned_skill.py` 删除前的双轨期出现两套 log_run | 双轨期内 `SkillContext.log_run` 与 Harness `log_run` 共用同一底层函数 `runtime.logger.write_agent_run()` |
| QualityCheck 自递归 | §3.2 名单 + Harness 在调 QC 时检测 `skill.name == "QualityCheck"` 直接跳过 |
| 22 个 skill 一次性大改导致 conflict | 严格按 Wave 1→5 顺序，每 Wave 一个 PR |
| input_schema 字段从 ctx.config 迁到 contract 漏字段 | 写 `test_contract_required_fields.py`，断言每个 skill contract 字段齐 |

---

*Last updated: 2026-06-09。本文件是成员 A 的 Day 1 工作清单。Codex 跑完 A3 后，A 应当先打开本文件，再 checkout `feature/backend-agent-harness-workflow`。*
