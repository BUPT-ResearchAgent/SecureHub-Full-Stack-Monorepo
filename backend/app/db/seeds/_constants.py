# Status: real

"""Single source of truth for stable demo identifiers + the canonical 9-agent
and core-skill catalogue. ``20260611_0960_seed_agents_skills`` and the seed
scripts in this package both import from here so the two surfaces never drift.
"""

from uuid import NAMESPACE_URL, UUID, uuid5


def stable_id(name: str) -> UUID:
    """Deterministic UUID5 helper. Same name → same id across re-seeds."""
    return uuid5(NAMESPACE_URL, f"securehub:{name}")


# ---- Demo user --------------------------------------------------------------

DEMO_USER_ID: UUID = stable_id("user:demo-student")
DEMO_USER_EMAIL = "demo-student@securehub.local"
DEMO_USER_NAME = "陈同学"
DEMO_USER_PASSWORD = "SecureHub@2026"

DEMO_USER_DIMENSIONS: dict[str, object] = {
    "knowledge_basis": "中级 — 学过 Web 开发与计算机网络基础",
    "cognitive_style": "看 demo 上手，遇到边界条件再深挖文档",
    "easy_mistakes": ["URL 编码混淆", "Cookie / Session 区分"],
    "learning_pace": "每周 4-6 小时",
    "interest_anchors": ["Web 安全", "AI 安全"],
    "career_goal": "甲方安全工程师 / SDL 方向",
}

# Radar-chart dimensions seeded for the demo user.
DEMO_USER_CAPABILITIES: list[tuple[str, float, float]] = [
    # (dimension, score, confidence) — score is 0..1
    ("web_security", 0.40, 0.60),
    ("crypto", 0.20, 0.40),
    ("reverse", 0.10, 0.30),
    ("binary_exploitation", 0.05, 0.20),
    ("ai_security", 0.35, 0.50),
    ("system_security", 0.30, 0.40),
    ("network_security", 0.45, 0.65),
    ("engineering_practice", 0.55, 0.70),
    ("academic_writing", 0.25, 0.30),
]


# ---- Agents (fixed 9) -------------------------------------------------------

AGENTS: list[tuple[str, str, str]] = [
    ("policy_interpreter", "Policy and compliance interpretation agent.", "medium"),
    ("hot_analyst", "Security event and reading recommendation agent.", "high"),
    ("job_analyst", "Job market and skill gap analysis agent.", "low"),
    ("competition_advisor", "Competition and quiz generation agent.", "medium"),
    (
        "career_planner",
        "Learning persona, resource recommendation, and tutor routing agent.",
        "high",
    ),
    ("topic_explorer", "Research topic and hands-on lab agent.", "medium"),
    ("doc_archivist", "Course document / PPT / mindmap / video storyboard agent.", "low"),
    ("task_orchestrator", "Learning path and task planning agent.", "low"),
    (
        "outcome_evaluator",
        "Assessment, capability update, and quality gate agent.",
        "high",
    ),
]

# Frozen production Skill catalog.  The name is kept for compatibility with
# older seed callers, but v1.1 deliberately contains all 28 production
# bindings rather than only the old 14-skill "core" subset.
CORE_SKILLS: dict[str, list[str]] = {
    "policy_interpreter": ["InterpretPolicy", "ComplianceCheck"],
    "hot_analyst": ["AnalyzeHotEvent", "RecommendReadings"],
    "job_analyst": ["AnalyzeJobMarket", "SkillGapAnalysis"],
    "competition_advisor": [
        "GenerateCompetitionPlan",
        "GenerateQuiz",
        "RecommendCompetition",
    ],
    "career_planner": [
        "BuildLearningPersona",
        "UpdatePersona",
        "RecommendResources",
        "RouteTutorQuestion",
        "GenerateGrowthPlan",
    ],
    "topic_explorer": [
        "GenerateHandsOnLab",
        "GenerateResearchTopic",
        "RecommendReadings",
    ],
    "doc_archivist": [
        "GenerateCourseDoc",
        "GenerateCoursePPT",
        "GenerateMindmap",
        "GenerateVideoStoryboard",
        "GenerateProposal",
    ],
    "task_orchestrator": ["GenerateLearningPath", "DecomposeWBS"],
    "outcome_evaluator": [
        "EvaluateSubmission",
        "RunAssessment",
        "QualityCheck",
        "UpdateCapability",
    ],
}


def agent_id(name: str) -> UUID:
    return stable_id(f"agent:{name}")


def skill_id(agent_name: str, skill_name: str, version: int = 1) -> UUID:
    return stable_id(f"skill:{agent_name}:{skill_name}:{version}")


# ---- Course websec ----------------------------------------------------------

COURSE_WEBSEC_ID: UUID = stable_id("course:websec-foundation")
# Wave 0 smoke roots used this transient course row.  It remains a read-only
# compatibility alias for already-persisted artifacts; new product roots use
# ``COURSE_WEBSEC_ID`` and ``WEBSEC-101`` exclusively.
LEGACY_SMOKE_COURSE_WEBSEC_ID = UUID("00000000-0000-0000-0000-000000000101")
COURSE_WEBSEC_CODE = "WEBSEC-101"
COURSE_WEBSEC_TITLE = "Web 安全基础"
COURSE_WEBSEC_DESCRIPTION = (
    "面向网络安全方向本科生的入门课程：HTTP/HTTPS 协议、常见 Web 攻击与防御、"
    "OWASP Top 10、SSRF / SSTI / 反序列化等专题，配套 SQL 注入实操案例。"
)

# Course productisation uses the existing knowledge asset tables.  These
# stable codes only classify nodes/documents; they do not introduce a parallel
# chapter or course-content table.
COURSE_WEBSEC_MANIFEST_ID = "websec-foundation-v1"
WEBSEC_CHAPTERS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "web-foundations",
        "Web 与浏览器安全边界",
        ("http-basics", "same-origin", "cookie-session"),
    ),
    (
        "input-and-browser-attacks",
        "输入处理与浏览器攻击",
        ("sql-injection", "sql-injection-blind", "xss-reflected", "xss-stored", "xss-dom", "csrf"),
    ),
    (
        "server-side-attack-surface",
        "服务端攻击面",
        ("file-upload", "ssrf", "deserialization", "rce"),
    ),
    (
        "identity-and-secure-development",
        "身份、授权与安全开发",
        ("auth-bypass", "waf-bypass", "secure-coding"),
    ),
    (
        "owasp-review",
        "OWASP Top 10 综合回顾",
        ("owasp-top10",),
    ),
]
WEBSEC_CHAPTER_BY_SLUG = {
    slug: (chapter_code, chapter_title)
    for chapter_code, chapter_title, slugs in WEBSEC_CHAPTERS
    for slug in slugs
}

# 17 knowledge points (kept tight for demo readability).
WEBSEC_NODES: list[tuple[str, str, int]] = [
    # (slug, name, level 1..5)
    ("http-basics", "HTTP / HTTPS 协议基础", 1),
    ("same-origin", "同源策略与 CORS", 2),
    ("cookie-session", "Cookie / Session / Token 鉴权", 2),
    ("sql-injection", "SQL 注入原理", 3),
    ("sql-injection-blind", "盲注与 Time-based 注入", 4),
    ("xss-reflected", "反射型 XSS", 3),
    ("xss-stored", "存储型 XSS", 3),
    ("xss-dom", "DOM-based XSS", 4),
    ("csrf", "CSRF 攻击与 Token 防御", 3),
    ("file-upload", "文件上传漏洞", 3),
    ("ssrf", "SSRF 与内网穿透", 4),
    ("deserialization", "反序列化漏洞与安全边界", 4),
    ("rce", "命令执行 / RCE", 4),
    ("auth-bypass", "认证绕过与越权", 3),
    ("waf-bypass", "WAF 检测与绕过常识", 4),
    ("secure-coding", "安全编码与修复闭环", 2),
    ("owasp-top10", "OWASP Top 10 综合回顾", 2),
]

# 39 prerequisite edges — small, hand-curated to look realistic in the demo.
WEBSEC_EDGES: list[tuple[str, str]] = [
    # (source_slug, target_slug)  — source must come before target
    ("http-basics", "same-origin"),
    ("http-basics", "cookie-session"),
    ("http-basics", "sql-injection"),
    ("http-basics", "xss-reflected"),
    ("http-basics", "csrf"),
    ("http-basics", "file-upload"),
    ("http-basics", "ssrf"),
    ("http-basics", "secure-coding"),
    ("http-basics", "rce"),
    ("cookie-session", "auth-bypass"),
    ("cookie-session", "csrf"),
    ("cookie-session", "deserialization"),
    ("sql-injection", "sql-injection-blind"),
    ("sql-injection", "auth-bypass"),
    ("sql-injection", "waf-bypass"),
    ("sql-injection", "secure-coding"),
    ("xss-reflected", "xss-stored"),
    ("xss-reflected", "xss-dom"),
    ("xss-reflected", "secure-coding"),
    ("xss-stored", "owasp-top10"),
    ("xss-dom", "owasp-top10"),
    ("csrf", "secure-coding"),
    ("csrf", "owasp-top10"),
    ("file-upload", "rce"),
    ("file-upload", "deserialization"),
    ("file-upload", "owasp-top10"),
    ("ssrf", "rce"),
    ("ssrf", "owasp-top10"),
    ("deserialization", "rce"),
    ("deserialization", "owasp-top10"),
    ("rce", "owasp-top10"),
    ("auth-bypass", "owasp-top10"),
    ("waf-bypass", "owasp-top10"),
    ("secure-coding", "owasp-top10"),
    ("same-origin", "xss-reflected"),
    ("same-origin", "csrf"),
    ("sql-injection-blind", "waf-bypass"),
    ("sql-injection-blind", "owasp-top10"),
    ("auth-bypass", "waf-bypass"),
]


def node_id(slug: str) -> UUID:
    return stable_id(f"kp:websec:{slug}")


def chunk_id(slug: str, index: int) -> UUID:
    return stable_id(f"chunk:websec:{slug}:{index:03d}")


def document_id(slug: str) -> UUID:
    return stable_id(f"document:websec:{slug}")
