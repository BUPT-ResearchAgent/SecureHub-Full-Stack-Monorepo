# Status: real

"""Mock / fixture support for offline harness runs.

When the project runs without a real LLM provider or a populated vector store
(typical for demos, CI, and the A3 evidence-floor regression tests) skills must
still produce plausible structured outputs so the workflow can complete and the
frontend can render the demo path.

This module centralizes:
- evidence fixtures (per domain / query keyword)
- LLM completion fixtures keyed by skill name
"""

from dataclasses import dataclass, field
from typing import Any

# --- Evidence fixtures ---------------------------------------------------

_DEFAULT_EVIDENCE: list[dict[str, Any]] = [
    {
        "chunk_id": "fixture-chunk-sqli-1",
        "document_id": "fixture-doc-sqli",
        "domain": "course_websec",
        "source": "OWASP Top 10 - A03 Injection",
        "excerpt": (
            "SQL Injection occurs when untrusted data is sent to an interpreter as part of a "
            "command or query. The attacker's hostile data can trick the interpreter into "
            "executing unintended commands or accessing data without proper authorization."
        ),
        "reliability": 0.95,
        "score": 0.92,
        "metadata": {"platform": "owasp", "kp": "sql_injection"},
    },
    {
        "chunk_id": "fixture-chunk-sqli-2",
        "document_id": "fixture-doc-portswigger",
        "domain": "course_websec",
        "source": "PortSwigger Web Security Academy - SQL Injection",
        "excerpt": (
            "Most instances of SQL injection can be prevented by using parameterized queries "
            "(also known as prepared statements) instead of string concatenation within the query."
        ),
        "reliability": 0.93,
        "score": 0.89,
        "metadata": {"platform": "portswigger", "kp": "sql_injection"},
    },
    {
        "chunk_id": "fixture-chunk-sqli-3",
        "document_id": "fixture-doc-cwe89",
        "domain": "course_websec",
        "source": "CWE-89 Improper Neutralization of Special Elements used in an SQL Command",
        "excerpt": (
            "Without sufficient removal or quoting of SQL syntax in user-controllable inputs, "
            "the generated SQL query can cause those inputs to be interpreted as SQL instead of "
            "ordinary user data."
        ),
        "reliability": 0.9,
        "score": 0.85,
        "metadata": {"platform": "mitre", "kp": "sql_injection"},
    },
    {
        "chunk_id": "fixture-chunk-sqli-4",
        "document_id": "fixture-doc-bobby",
        "domain": "course_websec",
        "source": "Little Bobby Tables - Defensive coding example",
        "excerpt": (
            "Parameterized statements and stored procedures, paired with allowlist input "
            "validation, defeat the vast majority of SQL injection vectors."
        ),
        "reliability": 0.85,
        "score": 0.8,
        "metadata": {"platform": "blog", "kp": "sql_injection"},
    },
]


def default_evidence_fixtures(domain: str = "course_websec") -> list[dict[str, Any]]:
    """Return a copy of the canned evidence list with the requested domain stamped."""
    return [{**hit, "domain": domain} for hit in _DEFAULT_EVIDENCE]


# --- LLM fixtures --------------------------------------------------------

_DEFAULT_LLM_OUTPUTS: dict[str, dict[str, Any]] = {
    "BuildLearningPersona": {
        "content": "Persona drafted from 4 dialogue turns covering background, weak points, and goals.",
        "dimensions": {
            "base_knowledge": "intermediate web development, beginner security",
            "cognitive_style": "example-driven, hands-on",
            "weak_points": ["sql_injection_blind", "ssrf", "deserialization"],
            "preferred_modality": ["doc", "lab", "video"],
            "time_budget": "8h/week",
            "target_direction": "web_security_engineer",
            "motivation": "internship interview preparation",
        },
        "next_question": "Have you tried CTF Web challenges before? If yes, which platform?",
        "quality_score": 0.86,
    },
    "UpdatePersona": {
        "content": "Persona updated based on the latest 5 learning events.",
        "dimensions": {
            "weak_points": ["sql_injection_second_order"],
            "strengths_delta": {"sql_injection": "+0.12"},
        },
        "quality_score": 0.82,
    },
    "RecommendResources": {
        "content": "Top 3 next-step resources selected.",
        "resources": [
            {"resource_type": "course_doc", "title": "SQL Injection deep dive", "score": 0.93},
            {"resource_type": "hands_on_lab", "title": "DVWA SQLi Lab Walkthrough", "score": 0.88},
            {"resource_type": "quiz_set", "title": "10-question SQLi quiz", "score": 0.84},
        ],
        "quality_score": 0.88,
    },
    "GenerateLearningPath": {
        "content": "3-stage path covering basics, exploitation, and defense.",
        "nodes": [
            {"kp_id": "kp-injection-basics", "title": "Injection basics", "est_minutes": 30},
            {"kp_id": "kp-sql-payloads", "title": "Classic SQLi payloads", "est_minutes": 45},
            {"kp_id": "kp-parameterized-queries", "title": "Parameterized queries", "est_minutes": 25},
        ],
        "edges": [
            {"from": "kp-injection-basics", "to": "kp-sql-payloads", "type": "prerequisite"},
            {"from": "kp-sql-payloads", "to": "kp-parameterized-queries", "type": "prerequisite"},
        ],
        "milestones": [
            {"name": "Complete SQLi quiz with >= 80%", "kp_id": "kp-sql-payloads"},
        ],
        "quality_score": 0.84,
    },
    "DecomposeWBS": {
        "content": "Goal decomposed into 4 WBS leaves.",
        "tree": {
            "id": "root",
            "title": "Master SQL Injection",
            "children": [
                {"id": "1", "title": "Read OWASP A03"},
                {"id": "2", "title": "Watch PortSwigger lab walkthrough"},
                {"id": "3", "title": "Implement parameterized query demo"},
                {"id": "4", "title": "Take 10-question quiz"},
            ],
        },
        "quality_score": 0.78,
    },
    "GenerateCourseDoc": {
        "content": "Markdown course document drafted.",
        "markdown": (
            "# SQL 注入基础\n\n"
            "## 1. 什么是 SQL 注入\n\n"
            "SQL 注入（SQL Injection）发生在不可信数据被拼接到 SQL 命令中，"
            "导致解释器执行非预期的查询。\n\n"
            "## 2. 典型攻击向量\n\n"
            "- 字符串拼接 `' OR 1=1--`\n- 布尔盲注\n- 时间盲注\n- 联合查询注入\n\n"
            "## 3. 防御要点\n\n"
            "1. **参数化查询 / 预编译语句**：从根上消除拼接面\n"
            "2. **输入校验**：白名单优先于黑名单\n"
            "3. **最小权限**：数据库账号仅授予业务必需权限\n\n"
            "## 4. 实践建议\n\n"
            "在 DVWA 的 SQLi Low 难度先完成手工注入，再切换到 Medium 体验"
            "WAF / 字符过滤的对抗。\n"
        ),
        "sections": ["定义", "攻击向量", "防御要点", "实践建议"],
        "quality_score": 0.91,
    },
    "GenerateCoursePPT": {
        "content": "Reveal.js style slide outline drafted.",
        "slides": [
            {"title": "SQL 注入：原理与危害", "bullets": ["定义", "影响范围", "OWASP Top 10 排名"]},
            {"title": "经典攻击向量", "bullets": ["布尔盲注", "时间盲注", "联合查询"]},
            {"title": "防御三板斧", "bullets": ["参数化查询", "白名单校验", "最小权限"]},
            {"title": "动手实验", "bullets": ["DVWA SQLi Low", "DVWA SQLi Medium", "sqlmap 自动化"]},
            {"title": "知识检查", "bullets": ["3 道选择题", "1 道代码题"]},
        ],
        "quality_score": 0.87,
    },
    "GenerateMindmap": {
        "content": "Markmap mindmap drafted.",
        "markmap": (
            "# SQL 注入\n"
            "## 原理\n"
            "- 拼接 SQL\n- 非法字符未过滤\n"
            "## 攻击向量\n"
            "- 联合查询\n- 布尔盲注\n- 时间盲注\n"
            "## 检测\n"
            "- sqlmap\n- Burp Suite\n"
            "## 防御\n"
            "- 参数化查询\n- ORM 安全模式\n- 最小权限\n"
        ),
        "mermaid": (
            "graph TD\n"
            "  SQLi[SQL 注入] --> CAUSE[拼接 SQL]\n"
            "  SQLi --> VECTOR[攻击向量]\n"
            "  VECTOR --> UNION[联合查询]\n"
            "  VECTOR --> BLIND[布尔盲注]\n"
            "  SQLi --> DEFENSE[防御]\n"
            "  DEFENSE --> PARAM[参数化查询]\n"
            "  DEFENSE --> LEAST[最小权限]\n"
        ),
        "quality_score": 0.85,
    },
    "GenerateVideoStoryboard": {
        "content": "5-shot storyboard with TTS narration drafted.",
        "shots": [
            {
                "index": 1,
                "duration_sec": 12,
                "visual": "首页：SQL 注入的危害 - OWASP A03 标志",
                "narration": "欢迎来到 SQL 注入入门视频。SQL 注入连续多年位列 OWASP Top 10。",
                "tts_text": "欢迎来到 SQL 注入入门视频。SQL 注入连续多年位列 OWASP Top 10。",
            },
            {
                "index": 2,
                "duration_sec": 18,
                "visual": "代码对比：拼接 vs 参数化",
                "narration": "看一段易受攻击的代码：用户名拼接进 SQL，导致 ' OR 1=1-- 完全绕过认证。",
                "tts_text": "看一段易受攻击的代码：用户名拼接进 SQL，导致 OR 1 等于 1 完全绕过认证。",
            },
            {
                "index": 3,
                "duration_sec": 20,
                "visual": "DVWA SQLi Low 实操录屏",
                "narration": "在 DVWA Low 难度下，输入单引号即可触发数据库错误。",
                "tts_text": "在 DVWA Low 难度下，输入单引号即可触发数据库错误。",
            },
            {
                "index": 4,
                "duration_sec": 15,
                "visual": "防御代码示例 - prepared statement",
                "narration": "切换到参数化查询，所有用户输入都会被安全转义。",
                "tts_text": "切换到参数化查询，所有用户输入都会被安全转义。",
            },
            {
                "index": 5,
                "duration_sec": 10,
                "visual": "总结：三条防御原则",
                "narration": "记住三条：参数化、白名单校验、最小权限。",
                "tts_text": "记住三条：参数化、白名单校验、最小权限。",
            },
        ],
        "quality_score": 0.83,
    },
    "GenerateQuiz": {
        "content": "5 quiz items drafted.",
        "items": [
            {
                "type": "single_choice",
                "question": "下列哪一项是预防 SQL 注入最根本的做法？",
                "options": [
                    "对用户输入做 HTML 转义",
                    "使用参数化查询 / 预编译语句",
                    "把 SQL 关键字加入黑名单",
                    "禁用所有用户输入",
                ],
                "answer": "B",
                "explanation": "参数化查询从协议层把数据与指令分开，是公认最有效的防御。",
                "difficulty": 2,
            },
            {
                "type": "single_choice",
                "question": "下列哪种注入需要观察响应时间差异判断？",
                "options": ["联合查询注入", "报错型注入", "时间盲注", "布尔盲注"],
                "answer": "C",
                "explanation": "时间盲注利用 SLEEP/BENCHMARK 函数让数据库延迟响应。",
                "difficulty": 3,
            },
            {
                "type": "multi_choice",
                "question": "下列哪些字符常被攻击者用作 SQL 注入入口？",
                "options": ["'", "\"", "--", ";"],
                "answer": "A,B,C,D",
                "explanation": "这些字符是 SQL 语法分隔符，未被转义时容易破坏语法结构。",
                "difficulty": 2,
            },
            {
                "type": "fill",
                "question": "用于探测时间盲注的常见 MySQL 函数是 ____。",
                "answer": "SLEEP",
                "explanation": "SLEEP(n) 让数据库延迟 n 秒返回，便于通过时延判断。",
                "difficulty": 2,
            },
            {
                "type": "code",
                "question": "请用 Python + psycopg2 写一段使用参数化查询查询用户名的代码片段。",
                "answer": "cursor.execute('SELECT * FROM users WHERE name = %s', (username,))",
                "explanation": "%s 是 psycopg2 的占位符，参数通过元组单独传入避免拼接。",
                "difficulty": 3,
            },
        ],
        "quality_score": 0.86,
    },
    "RecommendCompetition": {
        "content": "3 competitions ranked by fit.",
        "items": [
            {"name": "全国大学生信息安全竞赛", "level": "national", "fit": 0.88},
            {"name": "DEFCON CTF Qualifiers", "level": "international", "fit": 0.62},
            {"name": "BCTF", "level": "school", "fit": 0.79},
        ],
        "quality_score": 0.78,
    },
    "GenerateCompetitionPlan": {
        "content": "8-week prep plan",
        "milestones": [
            {"week": 1, "focus": "热身：Web 基础题"},
            {"week": 4, "focus": "中等难度 Web + Misc"},
            {"week": 8, "focus": "模拟赛 + 复盘"},
        ],
        "quality_score": 0.74,
    },
    "GenerateResearchTopic": {
        "content": "3 candidate research topics.",
        "topics": [
            {"title": "基于程序分析的 SSRF 自动检测", "feasibility": 0.7, "novelty": 0.6},
            {"title": "LLM 辅助的 Web 漏洞利用代码合成与防御对抗", "feasibility": 0.6, "novelty": 0.85},
            {"title": "基于 RASP 的运行时 SQLi 防御策略评估", "feasibility": 0.75, "novelty": 0.55},
        ],
        "quality_score": 0.75,
    },
    "GenerateHandsOnLab": {
        "content": "DVWA SQLi hands-on lab.",
        "lab": {
            "title": "DVWA SQLi 三难度通关",
            "objective": "掌握手工注入与防御代码的对照实践。",
            "environment": ["docker", "DVWA:latest", "burpsuite-community"],
            "steps": [
                "启动 DVWA 容器，登录后将 security level 设为 Low。",
                "在 SQL Injection 模块输入 1' OR 1=1#，观察返回结果。",
                "切换到 Medium，使用 Burp 修改 POST 参数重放注入。",
                "查看 source code，比对 mysqli_real_escape_string 与参数化查询的差异。",
            ],
            "acceptance": [
                "能在 Low 难度下取出 users 表全部用户名",
                "能解释 Medium 难度下转义函数的局限性",
                "能用 prepared statement 改写存在缺陷的代码",
            ],
        },
        "quality_score": 0.89,
    },
    "RecommendReadings": {
        "content": "Curated readings.",
        "items": [
            {
                "title": "OWASP Cheat Sheet - SQL Injection Prevention",
                "url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
                "platform": "owasp",
                "reason": "权威防御清单",
            },
            {
                "title": "PortSwigger Web Security Academy - SQL Injection",
                "url": "https://portswigger.net/web-security/sql-injection",
                "platform": "portswigger",
                "reason": "免费交互式实验",
            },
        ],
        "quality_score": 0.82,
    },
    "InterpretPolicy": {
        "content": "Policy summary",
        "summary": "《数据安全法》要求建立分级分类制度，关键信息基础设施数据出境需安全评估。",
        "capability_mapping": {"data_classification": "must", "cross_border_review": "must"},
        "compliance_risks": [],
        "quality_score": 0.7,
    },
    "ComplianceCheck": {
        "content": "Compliance report",
        "risks": [],
        "passed": True,
        "quality_score": 0.7,
    },
    "AnalyzeHotEvent": {
        "content": "Hot event analysis",
        "summary": "CVE-2024-XXXX 是一例典型的 SSRF 漏洞，影响范围中等。",
        "edu_value": 0.7,
        "abuse_risk": "low",
        "quality_score": 0.7,
    },
    "AnalyzeJobMarket": {
        "content": "Job market analysis",
        "trend": "渗透测试岗位需求稳中有升，AI 安全方向增长显著。",
        "top_skills": ["渗透测试", "代码审计", "应急响应", "AI 安全"],
        "quality_score": 0.7,
    },
    "SkillGapAnalysis": {
        "content": "Skill gap report",
        "gaps": [{"skill": "二进制漏洞利用", "level_gap": 2}],
        "fill_plan": ["完成 pwn 入门 lab", "练习 30 道 pwn challenge"],
        "quality_score": 0.7,
    },
    "EvaluateSubmission": {
        "content": "Submission evaluated",
        "score_vector": {"correctness": 0.8, "clarity": 0.75, "depth": 0.7},
        "overall_score": 0.75,
        "quality_score": 0.78,
    },
    "RunAssessment": {
        "content": "Assessment completed",
        "score": 0.82,
        "weak_kp_ids": ["kp-blind-sqli"],
        "next_recommendation": "重点复习布尔盲注 + 时间盲注",
        "capability_delta": {"sql_injection": 0.12},
        "quality_score": 0.84,
    },
    "QualityCheck": {
        "content": "Quality check passed.",
        "accept": True,
        "defects": [],
        "fact_consistency": 0.94,
        "citation_completeness": 0.95,
        "quality_score": 0.94,
    },
    "UpdateCapability": {
        "content": "Capabilities updated",
        "delta": {"sql_injection": 0.12, "input_validation": 0.06},
        "quality_score": 0.8,
    },
}


def default_llm_output(skill_name: str) -> dict[str, Any]:
    """Return a deep-ish copy of the canned LLM output for a skill, or a generic stub."""
    template = _DEFAULT_LLM_OUTPUTS.get(skill_name)
    if template is not None:
        return dict(template)
    return {
        "content": f"[fixture] no canned output for skill {skill_name}, returning generic stub.",
        "quality_score": 0.6,
    }


# --- Legacy fixtures kept for dev-era harness tests ----------------------


@dataclass(slots=True)
class ChunkHit:
    chunk_id: str
    document_id: str | None = None
    source_url: str | None = None
    excerpt: str = ""
    chapter: str | None = None
    score: float = 0.9
    metadata: dict[str, Any] = field(default_factory=dict)


class MockRetriever:
    def __init__(self, hits: list[ChunkHit]) -> None:
        self.hits = hits
        self.calls: list[dict[str, Any]] = []

    async def retrieve(
        self,
        query: str,
        *,
        domain: str | None = None,
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[ChunkHit]:
        self.calls.append({"query": query, "domain": domain, "top_k": top_k, "filters": filters})
        return self.hits[:top_k]


class MockLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def chat(self, prompt: str, *, stream: bool = False) -> str:
        self.calls.append({"prompt": prompt, "stream": stream})
        return prompt


class MockQualityCheck:
    def __init__(self, *, score: float = 0.8, accept: bool = True) -> None:
        self.score = score
        self.accept = accept
        self.calls: list[dict[str, Any]] = []

    async def check(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return {"accept": self.accept, "quality_score": self.score}
