# Status: real

"""Controlled, idempotent WEBSEC-101 showcase-course seed profile.

This seed deliberately writes ordinary production-domain records instead of a
frontend-only fixture.  It is for local development, competition rehearsal,
and explicitly authorised test databases only.  The command is disabled in a
production environment and needs an explicit opt-in environment variable.

Run:
    $env:SECUREHUB_ALLOW_SHOWCASE_SEED='1'
    uv run python -m app.db.seeds.seed_showcase_course seed

Verify:
    uv run python -m app.db.seeds.seed_showcase_course verify

Reset only this profile (never the base demo seed or unrelated user data):
    $env:SECUREHUB_ALLOW_SHOWCASE_SEED='1'
    uv run python -m app.db.seeds.seed_showcase_course reset
"""

from __future__ import annotations

import argparse
import asyncio
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.models.agent.agent_run import AgentRun
from app.db.models.collaboration.collaboration import (
    CourseUpdateDecision,
    CourseUpdateImpact,
    CourseUpdateSuggestion,
    ExternalSignal,
    Message,
    MessageDelivery,
)
from app.db.models.education.education_domain import (
    CourseEnrollment,
    GovernanceAuditEvent,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
    TeachingClassTeacher,
)
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.learning_event import LearningEvent
from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_replan import (
    CourseResourceRecommendation,
    LearningPathDecision,
    LearningPathReplanCandidate,
    LearningPathVersion,
)
from app.db.models.learning.learning_task import LearningTask
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizItemEvidence, QuizQualityReport
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.resource.resource_feedback import ResourceFeedback
from app.db.models.resource.resource_version import ResourceVersion
from app.db.models.storage.storage_object import StorageObject
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentItem,
    AssessmentSubmission,
    AssessmentVersion,
    ClassWeaknessSnapshot,
    CourseAssetGovernance,
    CourseDocumentBinding,
    CourseSyllabus,
    CourseSyllabusVersion,
    SyllabusReviewDecision,
    TeachingRecommendation,
    TeachingRecommendationDecision,
)
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot, WorkflowRun
from app.db.seeds._constants import (
    COURSE_WEBSEC_ID,
    DEMO_USER_PASSWORD,
    DEMO_USER_EMAIL,
    DEMO_USER_ID,
    DEMO_USER_NAME,
    chunk_id,
    document_id,
    node_id,
    stable_id,
)
from app.db.seeds.seed_agent_skills import run as seed_agent_skills
from app.db.seeds.seed_agents import run as seed_agents
from app.db.seeds.seed_course_websec import WEBSEC_QUIZ_ITEMS, run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import (
    DEMO_COURSE_TEACHER_ID,
    DEMO_ENROLLMENT_ID,
    DEMO_GROUP_MEMBER_ID,
    DEMO_STUDENT_GROUP_ID,
    DEMO_TEACHING_CLASS_ID,
    run as seed_education_domain,
)
from app.db.session import get_sessionmaker
from app.services.learning.student_course_experience_service import (
    StudentCourseExperienceService,
)
from app.services.learning.quiz_quality_service import QuizQualityService


PROFILE = "showcase_course"
MANIFEST_VERSION = "websec-101-showcase-v7"
MANIFEST_ID = stable_id("showcase-course:manifest:websec-101:v1")
SEED_AT = datetime(2026, 7, 17, 9, 0, tzinfo=UTC)
BASELINE_START = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
RECENT_START = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
RECENT_END = datetime(2026, 7, 16, 23, 59, tzinfo=UTC)

SHOWCASE_CLASS_B_ID = stable_id("showcase-course:class:websec:2026-b")
SHOWCASE_CLASS_B_TEACHER_ID = stable_id("showcase-course:class-teacher:websec:2026-b")
SHOWCASE_A_GROUP_B_ID = stable_id("showcase-course:group:websec:2026-a:lab-b")
SHOWCASE_B_GROUP_A_ID = stable_id("showcase-course:group:websec:2026-b:lab-a")
SHOWCASE_B_GROUP_B_ID = stable_id("showcase-course:group:websec:2026-b:lab-b")

SHOWCASE_LECTURE_DOCUMENT_ID = stable_id("showcase-course:lecture-document:websec-defensive-foundations")
SHOWCASE_LECTURE_ASSET_ID = stable_id("showcase-course:lecture-asset:websec-defensive-foundations")
SHOWCASE_LECTURE_STORAGE_ID = stable_id("showcase-course:lecture-storage:websec-defensive-foundations")
SHOWCASE_LECTURE_OBJECT_KEY = "course_websec/showcase/websec-101-defensive-foundations-lecture.md"
SHOWCASE_LECTURE_FILENAME = "websec-101-defensive-foundations-lecture.md"
SHOWCASE_LECTURE_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "storage"
    / "course_websec"
    / "curated"
    / SHOWCASE_LECTURE_FILENAME
)

_LECTURE_SECTION_KNOWLEDGE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("学习目标与前置", ("http-basics", "cookie-session")),
    ("从请求边界开始建模", ("http-basics", "auth-bypass", "secure-coding")),
    ("输入、查询与错误处理", ("sql-injection", "secure-coding")),
    ("浏览器输出与会话保护", ("xss-reflected", "same-origin", "cookie-session")),
    ("文件与服务端请求的最小权限", ("file-upload", "ssrf")),
    ("练习、复盘与下一步", ("owasp-top10", "secure-coding")),
    ("来源与使用边界", ("owasp-top10",)),
)


# Names are fictional course aliases, never student identities.  The stories
# drive capability, attempt, activity, and resource-progress differences.
SHOWCASE_STUDENTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("qinglan", "青岚", "accelerated", "a", "a1"),
    ("xingzhi", "行知", "accelerated", "a", "a1"),
    ("yanyue", "言越", "accelerated", "a", "a1"),
    ("ruixi", "睿析", "accelerated", "a", "a1"),
    ("zhiyuan", "知远", "accelerated", "a", "a1"),
    ("mingche", "明澈", "accelerated", "a", "a1"),
    ("anhe", "安和", "steady", "a", "a1"),
    ("jingye", "景页", "steady", "a", "a1"),
    ("shuyan", "书衍", "steady", "a", "a2"),
    ("linxi", "临溪", "steady", "a", "a2"),
    ("kecheng", "可澄", "steady", "a", "a2"),
    ("yuxuan", "予弦", "steady", "a", "a2"),
    ("yuanqi", "远启", "steady", "a", "a2"),
    ("qiaomu", "乔木", "steady", "a", "a2"),
    ("shuhang", "书航", "input_validation", "a", "a2"),
    ("weilan", "微澜", "input_validation", "a", "a2"),
    ("yuanjing", "远景", "input_validation", "b", "b1"),
    ("zhenghe", "正合", "input_validation", "b", "b1"),
    ("shishan", "时杉", "input_validation", "b", "b1"),
    ("jingran", "竟然", "input_validation", "b", "b1"),
    ("zhilin", "知临", "input_validation", "b", "b1"),
    ("yinzhi", "因知", "xss_prerequisite", "b", "b1"),
    ("lingyun", "凌云", "xss_prerequisite", "b", "b1"),
    ("qianmo", "阡陌", "xss_prerequisite", "b", "b1"),
    ("siyuan", "思源", "xss_prerequisite", "b", "b2"),
    ("xinran", "欣然", "xss_prerequisite", "b", "b2"),
    ("zhiyin", "知因", "xss_prerequisite", "b", "b2"),
    ("hanyue", "寒月", "recovery", "b", "b2"),
    ("denggao", "登高", "recovery", "b", "b2"),
    ("qinghe", "清和", "recovery", "b", "b2"),
    ("xingwen", "星闻", "recovery", "b", "b2"),
    ("zhiyu", "知遇", "recovery", "b", "b2"),
)

# The ordinary demo login remains its existing identity and authorization
# subject.  This overlay only gives it a clearly-labelled fictional course
# learner scenario so the default student route consumes the same durable
# records as the 32 course aliases.
SHOWCASE_DEMO_STUDENT_SLUG = "demo-student"
SHOWCASE_DEMO_STUDENT_DISPLAY_NAME = "课程演示学员"
SHOWCASE_DEMO_STUDENT_STORY = "input_validation"
SHOWCASE_DEMO_STUDENT_INDEX = len(SHOWCASE_STUDENTS)
SHOWCASE_DEMO_CAPABILITY_DIMENSIONS = (
    "web_security",
    "http_security",
    "authentication",
    "input_validation",
    "xss_defense",
    "secure_coding",
    "learning_progress",
)
SHOWCASE_DEMO_PROFILE_KEYS = (
    "profile_kind",
    "seed_profile",
    "showcase_account",
    "learning_story",
    "learning_story_summary",
    "course_id",
    "current_progress",
    "recommended_next_step",
    "source_boundary",
)
SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY = "demo-student-assessment-quiz"
SHOWCASE_DEMO_ASSESSMENT_EVENT_KEY = "demo-student-assessment-draft"
SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY = "demo-comprehensive-36"


# Fifteen additional quality-gated items bring the profile to 36 questions
# without changing the historical 21-item base seed or its focused tests.
SHOWCASE_QUIZZES: tuple[dict[str, Any], ...] = (
    {
        "slug": "http-basics", "key": "http-security-boundary", "type": "single_choice", "difficulty": 1,
        "question": "排查 Web 请求安全边界时，最适合作为首个核对点的是哪一项？",
        "options": ["请求方法、认证状态与服务端授权是否一致", "只检查页面配色是否统一", "只统计接口响应字节数", "先关闭所有日志"],
        "answer": "请求方法、认证状态与服务端授权是否一致",
        "explanation": "HTTP 方法、认证与授权共同决定一次请求能否被正确处理，防御排查不能只依赖前端页面表现。",
    },
    {
        "slug": "cookie-session", "key": "session-cookie-flags", "type": "multi_choice", "difficulty": 2,
        "question": "会话 Cookie 的安全配置通常应包含哪些控制？",
        "options": ["HttpOnly", "Secure", "合理的 SameSite 策略", "把令牌写入公开页面标题"],
        "answer": "HttpOnly;Secure;合理的 SameSite 策略",
        "explanation": "这些属性分别降低脚本读取、明文传输和跨站携带风险；公开暴露凭据会扩大泄露面。",
    },
    {
        "slug": "auth-bypass", "key": "object-authorization-check", "type": "single_choice", "difficulty": 2,
        "question": "服务端处理带对象标识的请求时，最关键的授权检查是什么？",
        "options": ["验证当前用户是否有权访问该具体对象", "隐藏前端删除按钮", "要求浏览器使用深色模式", "仅检查对象标识格式"],
        "answer": "验证当前用户是否有权访问该具体对象",
        "explanation": "认证确认身份，授权必须逐对象判断访问权；前端隐藏控件不能替代服务端校验。",
    },
    {
        "slug": "sql-injection", "key": "input-validation-layering", "type": "short_answer", "difficulty": 3,
        "question": "某查询接口同时接收筛选条件和排序字段。请说明防御性设计应如何区分数据参数与结构化选项。",
        "options": [],
        "answer": "数据参数使用参数化查询；排序字段使用服务端白名单映射；两类输入都记录可审计的拒绝原因。",
        "explanation": "参数化查询处理数据值，白名单处理不能参数化的结构化选项；两者共同避免不可信输入改变查询结构。",
    },
    {
        "slug": "xss-reflected", "key": "contextual-output-encoding", "type": "short_answer", "difficulty": 3,
        "question": "为什么 XSS 防御需要按输出上下文选择编码方式？",
        "options": [],
        "answer": "HTML 文本、属性、URL 和脚本上下文的解析规则不同，必须使用对应编码并避免危险 sink。",
        "explanation": "统一替换字符无法覆盖不同解析上下文；模板自动转义、上下文编码和 CSP 形成分层防线。",
    },
    {
        "slug": "xss-stored", "key": "stored-xss-review-path", "type": "short_answer", "difficulty": 3,
        "question": "评论功能引入富文本后，代码评审应优先检查哪些防御环节？",
        "options": [],
        "answer": "富文本白名单净化、持久化前后的一致校验、渲染时安全模板、历史内容复核和 CSP 监测。",
        "explanation": "存储型风险跨越提交、保存和展示环节，修复不能只处理一个表单入口。",
    },
    {
        "slug": "xss-dom", "key": "dom-safe-sink", "type": "single_choice", "difficulty": 3,
        "question": "处理来自 URL 片段的展示文本时，哪种做法更符合防御性默认值？",
        "options": ["使用 textContent 或受信模板渲染", "直接拼接到 innerHTML", "关闭浏览器同源策略", "将片段转成可执行脚本"],
        "answer": "使用 textContent 或受信模板渲染",
        "explanation": "安全 sink 减少把不可信数据解释为标记或脚本的机会，应配合严格 URL 解析。",
    },
    {
        "slug": "file-upload", "key": "upload-defense-checklist", "type": "multi_choice", "difficulty": 3,
        "question": "上传功能的防御性验收应检查哪些内容？",
        "options": ["类型与大小白名单", "服务端重新命名并隔离存储", "异步扫描或安全处理", "按原文件名直接放入 Web 根目录"],
        "answer": "类型与大小白名单;服务端重新命名并隔离存储;异步扫描或安全处理",
        "explanation": "上传内容应脱离可直接执行的 Web 路径，并经过服务端可审计的类型、大小和处理检查。",
    },
    {
        "slug": "ssrf", "key": "ssrf-outbound-allowlist", "type": "single_choice", "difficulty": 3,
        "question": "提供 URL 预览能力时，最稳妥的服务端出站请求策略是什么？",
        "options": ["域名白名单、DNS/IP 校验和内网地址段拦截", "允许任意协议和内网地址", "仅让前端隐藏输入框", "把请求结果直接转发给浏览器"],
        "answer": "域名白名单、DNS/IP 校验和内网地址段拦截",
        "explanation": "SSRF 防御应在服务端建立出站边界，避免解析结果绕过以及对内部地址的访问。",
    },
    {
        "slug": "deserialization", "key": "deserialization-data-format", "type": "fill", "difficulty": 3,
        "question": "完成防御原则：面对不可信跨服务数据，应优先使用 ______ 格式，并校验类型、来源、签名和允许字段。",
        "options": [],
        "answer": "简单数据",
        "explanation": "安全边界在于不让外部数据触发对象生命周期或危险 gadget 链，而不是事后捕获异常。",
    },
    {
        "slug": "secure-coding", "key": "secure-review-evidence", "type": "multi_choice", "difficulty": 2,
        "question": "一次可追溯的安全修复复盘应保留哪些证据？",
        "options": ["问题成因与影响范围", "修复后的回归验证", "剩余风险与后续责任", "只保留一句“已优化”"],
        "answer": "问题成因与影响范围;修复后的回归验证;剩余风险与后续责任",
        "explanation": "可追溯复盘连接问题、修复、验证和残余风险，避免用泛化结论掩盖未验证边界。",
    },
    {
        "slug": "csrf", "key": "csrf-request-origin", "type": "single_choice", "difficulty": 2,
        "question": "下列哪项最能说明敏感状态变更请求来自经过验证的交互上下文？",
        "options": ["校验 CSRF Token 并结合 SameSite 与 Origin/Referer 策略", "只检查用户已登录", "只把请求改为 POST", "关闭错误提示"],
        "answer": "校验 CSRF Token 并结合 SameSite 与 Origin/Referer 策略",
        "explanation": "登录态本身不证明请求意图；Token 与浏览器上下文策略共同形成防御。",
    },
    {
        "slug": "same-origin", "key": "cors-least-privilege", "type": "short_answer", "difficulty": 2,
        "question": "跨域 API 需要被合作站点调用时，CORS 配置应遵循什么最小权限原则？",
        "options": [],
        "answer": "仅允许经过审核的来源、方法和请求头；凭据场景不用通配来源，并记录配置变更与验证结果。",
        "explanation": "CORS 是浏览器侧边界配置，过宽来源和凭据组合会扩大可被读取的响应范围。",
    },
    {
        "slug": "owasp-top10", "key": "risk-prioritization-review", "type": "short_answer", "difficulty": 2,
        "question": "课程复盘中如何把多个 Web 风险转化为下一步学习优先级？",
        "options": [],
        "answer": "结合真实作答样本、错误率、前置知识和近期趋势，先安排可验证的补学资源与练习。",
        "explanation": "学习优先级需要证据和前置关系，不能只依据单次平均分或通用口号。",
    },
    {
        "slug": "waf-bypass", "key": "waf-defense-boundary", "type": "single_choice", "difficulty": 2,
        "question": "关于 WAF 在安全体系中的定位，哪项表述更准确？",
        "options": ["WAF 是补充检测控制，核心漏洞仍应在应用层修复", "部署 WAF 后可以取消参数化查询", "WAF 取代访问控制", "WAF 能替代所有回归测试"],
        "answer": "WAF 是补充检测控制，核心漏洞仍应在应用层修复",
        "explanation": "边界设备不能替代安全编码、授权检查和验证；课程强调识别与修复而非绕过细节。",
    },
)


def _id(kind: str, key: str) -> UUID:
    return stable_id(f"showcase-course:{kind}:{key}")


def _student_id(slug: str) -> UUID:
    return _id("student", slug)


def _quiz_id(key: str) -> UUID:
    return _id("quiz", key)


def _demo_comprehensive_quiz_ids(quizzes: dict[str, UUID]) -> list[UUID]:
    """Return the base 21 plus showcase 15 in their published course order.

    ``SHOWCASE_QUIZZES`` deliberately contains only the supplemental 15
    items.  The existing ``seed_course_websec`` owns the other 21 persisted,
    quality-gated items, so the comprehensive assessment must explicitly
    combine both sources instead of mistaking the supplemental set for the
    full 36-question bank.
    """

    return [
        *[UUID(str(item["id"])) for item in WEBSEC_QUIZ_ITEMS],
        *[quizzes[str(item["key"])] for item in SHOWCASE_QUIZZES],
    ]


def _evidence_ids(session: AsyncSession, *values: UUID) -> list[UUID | str]:
    """Keep PostgreSQL UUID arrays typed while retaining SQLite test compatibility."""

    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        return [str(value) for value in values]
    return list(values)


def _profile_user_ids() -> list[UUID]:
    return [_student_id(slug) for slug, *_ in SHOWCASE_STUDENTS]


def _showcase_learner_ids() -> list[UUID]:
    """Return the 32 fictional aliases plus the existing demo learner."""

    return [*_profile_user_ids(), DEMO_USER_ID]


def _showcase_learner_ids_for_class(teaching_class_id: UUID) -> list[UUID]:
    learner_ids = [
        _student_id(slug)
        for slug, _alias, _story, class_key, _group_key in SHOWCASE_STUDENTS
        if (
            class_key == "a" and teaching_class_id == DEMO_TEACHING_CLASS_ID
        ) or (
            class_key == "b" and teaching_class_id == SHOWCASE_CLASS_B_ID
        )
    ]
    if teaching_class_id == DEMO_TEACHING_CLASS_ID:
        learner_ids.append(DEMO_USER_ID)
    return learner_ids


def _demo_showcase_capability_ids() -> list[UUID]:
    return [
        _id("capability", f"{SHOWCASE_DEMO_STUDENT_SLUG}:{dimension}")
        for dimension in SHOWCASE_DEMO_CAPABILITY_DIMENSIONS
    ]


def _is_allowed_environment() -> bool:
    settings = get_settings()
    return settings.APP_ENV.strip().lower() not in {"production", "prod", "release"}


def _require_explicit_opt_in() -> None:
    if not _is_allowed_environment():
        raise RuntimeError("showcase_course seed is disabled when APP_ENV is production/release")
    if os.getenv("SECUREHUB_ALLOW_SHOWCASE_SEED", "").strip().lower() not in {"1", "true", "yes"}:
        raise RuntimeError(
            "showcase_course seed requires SECUREHUB_ALLOW_SHOWCASE_SEED=1; it never runs at application startup"
        )


async def _ensure(
    session: AsyncSession, orm_model: type[Any], row_id: UUID, **values: Any
) -> tuple[Any, bool]:
    row = await session.get(orm_model, row_id)
    if row is None:
        row = orm_model(id=row_id, **values)
        session.add(row)
        await session.flush()
        return row, True
    changed = False
    for name, value in values.items():
        if getattr(row, name) != value:
            setattr(row, name, value)
            changed = True
    if changed:
        await session.flush()
    return row, False


def _read_showcase_lecture() -> tuple[str, list[tuple[str, str]]]:
    """Load the versioned local lecture and retain its semantic section boundaries."""

    if not SHOWCASE_LECTURE_PATH.is_file():
        raise RuntimeError(f"showcase lecture file missing: {SHOWCASE_LECTURE_PATH}")
    content = SHOWCASE_LECTURE_PATH.read_text(encoding="utf-8").strip()
    if len(content) < 900:
        raise RuntimeError("showcase lecture does not meet the minimum teaching-content length")

    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.removeprefix("## ").strip()
            current_lines = [line]
        elif current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if len(sections) != len(_LECTURE_SECTION_KNOWLEDGE):
        raise RuntimeError("showcase lecture sections no longer match the persisted chunk contract")
    if any(len(section_body) < 120 for _, section_body in sections):
        raise RuntimeError("showcase lecture contains an under-specified teaching section")
    return content, sections


async def _seed_showcase_lecture(session: AsyncSession, counts: dict[str, int]) -> None:
    """Persist the curated lecture through the shared knowledge asset layer.

    This is a preprocessed local teaching asset, not an upload or a live PDF
    parse.  Its parse and chunk facts are persisted so the teacher UI can show
    them honestly and the normal embedding pipeline can later consume the
    pending chunks.
    """

    content, sections = _read_showcase_lecture()
    content_bytes = content.encode("utf-8")
    content_hash = sha256(content_bytes).hexdigest()
    chapter_count = len(sections)
    processed_at = SEED_AT - timedelta(minutes=12)
    processing_timeline = [
        {
            "stage": "upload_registered",
            "label": "受控讲义已登记到本地演示存储",
            "state": "completed",
            "occurred_at": (processed_at - timedelta(seconds=18)).isoformat(),
        },
        {
            "stage": "safety_format_check",
            "label": "已完成格式、来源边界和防御性教学内容检查",
            "state": "completed",
            "occurred_at": (processed_at - timedelta(seconds=12)).isoformat(),
        },
        {
            "stage": "structured_parse",
            "label": "预置讲义结构已持久化；不是本次页面操作实时解析",
            "state": "completed",
            "occurred_at": (processed_at - timedelta(seconds=7)).isoformat(),
        },
        {
            "stage": "chunked",
            "label": f"已按 {chapter_count} 个教学章节写入可追溯知识块",
            "state": "completed",
            "occurred_at": processed_at.isoformat(),
        },
        {
            "stage": "index_pending",
            "label": "向量化/索引等待当前环境配置的既有嵌入任务；不会在前端模拟成功",
            "state": "pending",
            "occurred_at": None,
        },
    ]
    metadata = {
        "course_id": str(COURSE_WEBSEC_ID),
        "course_code": "WEBSEC-101",
        "source_kind": "curated-demo",
        "source_boundary": "受控预置教学讲义；仅用于本地/比赛演示/授权测试，不是实时模型生成或生产教材发布。",
        "processing_mode": "preprocessed_seed",
        "not_live_ingestion": True,
        "page_count": None,
        "chapter_count": chapter_count,
        "processing_elapsed_ms": 1840,
        "processing_timeline": processing_timeline,
        "platform": "securehub_course_team",
        "source_url": "local://course_websec/curated/websec-101-defensive-foundations-lecture.md",
        "author": "SecureHub 课程组",
        "published_at": None,
        "fetched_at": processed_at.isoformat(),
        "license": "demo-only curated teaching material",
        "rights_note": "课程团队整理的防御性教学讲义；来源、Evidence 和版权边界须在资产详情核验。",
        "collection_mode": "controlled_seed",
    }
    _, created = await _ensure(
        session,
        StorageObject,
        SHOWCASE_LECTURE_STORAGE_ID,
        provider="local",
        bucket="securehub-demo",
        object_key=SHOWCASE_LECTURE_OBJECT_KEY,
        original_filename=SHOWCASE_LECTURE_FILENAME,
        mime_type="text/markdown; charset=utf-8",
        size_bytes=len(content_bytes),
        content_hash=content_hash,
        status="ready",
        metadata_={
            "seed_profile": PROFILE,
            "source_kind": "curated-demo",
            "not_live_generated": True,
            "source_boundary": metadata["source_boundary"],
        },
    )
    counts["lecture_storage_objects"] += int(created)
    _, created = await _ensure(
        session,
        Document,
        SHOWCASE_LECTURE_DOCUMENT_ID,
        domain="course_websec",
        source_type="curated_lecture",
        title="WEBSEC-101 Web 安全防御基础讲义",
        url=str(metadata["source_url"]),
        content_hash=content_hash,
        raw_text=content,
        metadata_=metadata,
        trust_score=0.9,
        status="ready",
        fetched_at=processed_at,
    )
    counts["lecture_documents"] += int(created)
    _, created = await _ensure(
        session,
        DocumentAsset,
        SHOWCASE_LECTURE_ASSET_ID,
        document_id=SHOWCASE_LECTURE_DOCUMENT_ID,
        asset_type="markdown_full",
        object_key=SHOWCASE_LECTURE_OBJECT_KEY,
        mime_type="text/markdown; charset=utf-8",
        size_bytes=len(content_bytes),
        content_hash=content_hash,
        metadata_={
            "seed_profile": PROFILE,
            "display_name": "WEBSEC-101 Web 安全防御基础讲义",
            "chapter_count": chapter_count,
            "page_count": None,
            "processing_elapsed_ms": metadata["processing_elapsed_ms"],
            "processing_mode": "preprocessed_seed",
            "not_live_ingestion": True,
        },
    )
    counts["lecture_document_assets"] += int(created)

    for index, ((title, text), (expected_title, slugs)) in enumerate(
        zip(sections, _LECTURE_SECTION_KNOWLEDGE, strict=True)
    ):
        if expected_title not in title:
            raise RuntimeError(f"showcase lecture chapter mismatch: {title}")
        _, created = await _ensure(
            session,
            Chunk,
            _id("lecture-chunk", f"{index:02d}"),
            document_id=SHOWCASE_LECTURE_DOCUMENT_ID,
            domain="course_websec",
            chunk_text=text,
            chunk_index=index,
            token_count=len(text.split()),
            embedding=None,
            embedding_status="pending",
            metadata_={
                "seed_profile": PROFILE,
                "course_id": str(COURSE_WEBSEC_ID),
                "course_code": "WEBSEC-101",
                "asset_id": str(SHOWCASE_LECTURE_ASSET_ID),
                "asset_object_key": SHOWCASE_LECTURE_OBJECT_KEY,
                "asset_type": "markdown_full",
                "chapter": title,
                "headings": [title],
                "page_no": None,
                "kp_ids": [str(node_id(slug)) for slug in slugs],
                "source_url": metadata["source_url"],
                "platform": metadata["platform"],
                "author": metadata["author"],
                "license": metadata["license"],
                "rights_note": metadata["rights_note"],
                "source_boundary": metadata["source_boundary"],
                "quality_state": "reviewed_seed",
            },
        )
        counts["lecture_chunks"] += int(created)


def _story_scores(story: str, index: int) -> dict[str, float]:
    offset = (index % 5) * 0.013
    baselines = {
        "accelerated": {"http": 0.91, "auth": 0.89, "input": 0.86, "xss": 0.87, "progress": 0.9},
        "steady": {"http": 0.76, "auth": 0.74, "input": 0.72, "xss": 0.7, "progress": 0.73},
        "input_validation": {"http": 0.73, "auth": 0.71, "input": 0.39, "xss": 0.62, "progress": 0.66},
        "xss_prerequisite": {"http": 0.57, "auth": 0.67, "input": 0.61, "xss": 0.36, "progress": 0.6},
        "recovery": {"http": 0.62, "auth": 0.63, "input": 0.53, "xss": 0.49, "progress": 0.59},
    }
    return {key: round(min(0.97, value + offset), 3) for key, value in baselines[story].items()}


def _story_label(story: str) -> str:
    return {
        "accelerated": "基础扎实，可进入综合案例与同伴支持任务",
        "steady": "核心概念稳定，适合按节奏巩固并完成阶段练习",
        "input_validation": "HTTP 与认证基础可用，输入验证和参数化查询需重点复盘",
        "xss_prerequisite": "XSS 与浏览器先修边薄弱，需先回看同源策略和输出上下文",
        "recovery": "前期进度滞后，近期已通过资源复盘和补交任务出现改善",
    }[story]


def _attempt_scores(story: str, index: int) -> tuple[list[float], list[float]]:
    jitter = ((index % 4) - 1.5) * 0.018
    baseline = {
        "accelerated": [0.9, 0.88, 0.87, 0.89, 0.86, 0.88],
        "steady": [0.74, 0.72, 0.7, 0.69, 0.71, 0.73],
        "input_validation": [0.73, 0.68, 0.38, 0.61, 0.66, 0.65],
        "xss_prerequisite": [0.55, 0.62, 0.61, 0.32, 0.6, 0.58],
        "recovery": [0.45, 0.5, 0.42, 0.4, 0.48, 0.46],
    }[story]
    recent = {
        "accelerated": [0.94, 0.92, 0.91, 0.92, 0.9, 0.91],
        "steady": [0.79, 0.77, 0.75, 0.74, 0.76, 0.77],
        "input_validation": [0.78, 0.73, 0.48, 0.65, 0.7, 0.69],
        "xss_prerequisite": [0.63, 0.68, 0.66, 0.43, 0.66, 0.65],
        "recovery": [0.68, 0.7, 0.62, 0.61, 0.66, 0.67],
    }[story]
    return (
        [round(max(0.0, min(1.0, value + jitter)), 3) for value in baseline],
        [round(max(0.0, min(1.0, value + jitter)), 3) for value in recent],
    )


def _resource_definitions() -> tuple[dict[str, Any], ...]:
    return (
        {
            "key": "input-validation-guide-v1", "type": "doc", "slug": "sql-injection", "version": 1,
            "title": "输入验证与参数化查询防御学习单", "parent": None,
            "content": {"source_type": "curated-demo", "learning_objectives": ["区分数据参数与结构化选项", "解释参数化查询的防御边界"], "sections": ["前置：HTTP 请求与数据库访问边界", "输入分类与白名单", "参数化查询和错误处理", "复盘检查清单"], "cases": ["搜索条件的安全映射", "排序字段的服务端白名单"], "next_step": "完成输入验证分层练习并查看证据切片。"},
        },
        {
            "key": "input-validation-guide-v2", "type": "doc", "slug": "sql-injection", "version": 2,
            "title": "输入验证与参数化查询防御学习单（补充案例版）", "parent": "input-validation-guide-v1",
            "content": {
                "source_type": "curated-demo",
                "change_summary": "增加排序字段白名单、日志审计和回归验证案例",
                "learning_objectives": ["区分数据参数与结构化选项", "将参数化查询与白名单策略组合应用", "把修复结论写成可验证的检查记录"],
                "prerequisites": ["HTTP 请求中的查询参数", "服务端授权与错误处理的基本边界"],
                "sections": ["一、请求边界与输入分类", "二、数据参数的参数化查询", "三、结构化选项的白名单映射", "四、两个防御案例", "五、回归检查与下一步"],
                "body": (
                    "## 学习目标\n"
                    "本学习单帮助你把“过滤输入”拆成可以验证的服务端责任：先确认请求是否经过认证与授权，再区分普通数据值和会改变查询结构的选项。完成后，你应能说明参数化查询、白名单映射、错误处理和审计记录分别解决什么问题，而不是把所有控制笼统称为“拦截”。\n\n"
                    "## 前置条件\n"
                    "开始前请能读懂一次 HTTP 请求中的查询条件、排序字段和分页参数，并知道浏览器页面上的隐藏按钮不能替代服务端对象授权。课程不要求编写或复现攻击载荷；所有讨论围绕识别风险、修复实现和验证证据。\n\n"
                    "## 一、先按输入语义分层\n"
                    "筛选条件通常是数据值，例如课程名称、日期范围或状态。这类值应交给数据库驱动的参数绑定接口，避免由字符串拼接决定查询语法。排序字段、字段名和可选聚合方式则属于结构化选项，不能仅靠参数化占位符处理。服务端应建立有限的业务映射，例如把“最新提交”映射为经过审核的列名和固定排序方向；未知选项返回可理解的校验错误，并在日志中记录被拒绝的原因。\n\n"
                    "## 二、案例：筛选条件与排序字段\n"
                    "在课程作业列表中，学生可按提交时间筛选并选择“按截止时间”或“按成绩状态”排序。修复后的接口把筛选值作为参数传入查询，把排序选项映射到服务端枚举；页面传来的任意文本都不能直接成为 SQL 结构。验证时需要覆盖合法筛选、未知排序、空值、超长值和无权限对象五类请求，并确认错误响应不泄露数据库细节。\n\n"
                    "## 三、案例：修复后的审计与回归\n"
                    "某教师筛选本班提交记录时，系统除了校验输入，还必须先校验教学班归属。测试记录应说明：请求用户、允许的课程范围、采用的白名单键、参数化查询是否生效，以及拒绝时是否保留了最小必要的审计事件。这样复盘时能够区分“输入格式不合法”和“用户没有对象权限”，也能避免把一次成功页面渲染误当成完整安全修复。\n\n"
                    "## 检查清单\n"
                    "- 数据值是否使用参数绑定，而不是拼接查询文本？\n"
                    "- 字段名、排序和操作符是否来自有限白名单？\n"
                    "- 是否先完成认证、课程范围和对象授权检查？\n"
                    "- 错误信息是否对用户可理解且不暴露内部结构？\n"
                    "- 是否为允许和拒绝路径保存了可复查的验证记录？\n\n"
                    "## 练习与下一步\n"
                    "任选一个课程列表场景，写出数据参数、结构化选项、授权边界和两条回归断言。随后进入已发布的输入验证练习，提交后再对照评分反馈调整学习路径。"
                ),
                "cases": ["筛选条件与排序字段的不同处理", "修复后的审计日志核对"],
                "evidence_note": "受控课程整理资料；Evidence 摘要和来源边界在详情中可查看。",
                "next_step": "完成输入验证分层练习并查看已发布题目的反馈。",
            },
        },
        {
            "key": "xss-defense-slides-v1", "type": "ppt", "slug": "xss-reflected", "version": 1,
            "title": "浏览器输出边界与 XSS 防御课件", "parent": None,
            "content": {"source_type": "curated-demo", "slides": [{"title": "学习目标", "points": ["识别反射、存储与 DOM 三类风险", "按输出上下文选择防御"]}, {"title": "先修关系", "points": ["HTTP 请求响应", "同源策略与浏览器解析"]}, {"title": "输出上下文", "points": ["HTML 文本", "属性", "URL", "脚本"]}, {"title": "防御案例", "points": ["受信模板", "textContent", "CSP"]}, {"title": "检查点", "points": ["危险 sink 审计", "历史内容复核"]}], "evidence_note": "课程整理内容，证据链接保留在资源详情。"},
        },
        {
            "key": "xss-defense-slides-v2", "type": "ppt", "slug": "xss-reflected", "version": 2,
            "title": "浏览器输出边界与 XSS 防御课件（复盘版）", "parent": "xss-defense-slides-v1",
            "content": {
                "source_type": "curated-demo",
                "change_summary": "补充 DOM sink 检查、存储型内容治理和课后验证页",
                "slides": [
                    {"title": "封面：浏览器输出边界复盘", "points": ["WEBSEC-101 课程整理课件", "主题：输出上下文、模板与验证"], "speaker_note": "说明本课件是受控预置资料，不是实时生成。"},
                    {"title": "本节学习目标", "points": ["区分 HTML、属性、URL 与脚本上下文", "选择受信渲染和编码策略", "完成可验证的修复复盘"], "speaker_note": "先明确学习产出，避免只记住风险名称。"},
                    {"title": "先修关系", "points": ["HTTP 请求和响应", "同源策略", "浏览器解析与 Cookie 边界"], "speaker_note": "先修概念未稳定时，先回到同源与响应渲染。"},
                    {"title": "风险从哪里进入", "points": ["URL 参数与搜索结果", "评论和富文本历史内容", "前端状态与第三方数据"], "speaker_note": "只描述数据流和防御面，不提供可复现攻击载荷。"},
                    {"title": "输出上下文决定控制", "points": ["HTML 文本使用模板默认转义", "属性与 URL 使用上下文编码和严格解析", "避免把数据放入脚本执行上下文"], "speaker_note": "同一种替换规则不能覆盖所有浏览器解析器。"},
                    {"title": "DOM 安全 sink", "points": ["优先 textContent 和受信模板", "对 URL 采用协议与目标校验", "审核高风险渲染 API"], "speaker_note": "把注意力放在安全 sink 的选择与代码审计。"},
                    {"title": "案例一：搜索结果展示", "points": ["输入仅作为文本呈现", "服务端返回结构化结果", "回归测试覆盖特殊字符和空状态"], "speaker_note": "验证页面可见结果与安全渲染规则同时成立。"},
                    {"title": "案例二：富文本评论治理", "points": ["内容白名单净化", "持久化前后的一致校验", "历史内容复核与发布流程"], "speaker_note": "存储型风险必须覆盖提交、保存和再次展示。"},
                    {"title": "CSP 是补充控制", "points": ["限制不受信脚本来源", "报告模式帮助发现回归", "不能替代模板转义和安全编码"], "speaker_note": "强调分层防御，避免把单个配置当作万能修复。"},
                    {"title": "检查点", "points": ["是否识别了输出上下文", "是否使用安全 sink", "是否复核历史内容和第三方数据"], "speaker_note": "每个检查点都应能对应代码或测试证据。"},
                    {"title": "阶段练习", "points": ["标注一个页面的数据流", "说明一个安全渲染选择", "写出两条回归断言"], "speaker_note": "练习后进入已发布作业，而不是只浏览幻灯片。"},
                    {"title": "下一步与来源", "points": ["回看同源策略先修节点", "完成输入处理与浏览器输出练习", "在资源详情查看 Evidence 摘要"], "speaker_note": "来源：受控课程整理与课程 Evidence；非实时模型输出。"}
                ],
                "evidence_note": "预置课程课件，包含 12 页可分页结构；不是实时生成。",
                "next_step": "完成浏览器输出边界阶段作业或查看同源策略先修资源。",
            },
        },
        {
            "key": "websec-map-v1", "type": "mindmap", "slug": "http-basics", "version": 1,
            "title": "WEBSEC-101 防御知识地图", "parent": None,
            "content": {"source_type": "curated-demo", "nodes": ["HTTP / HTTPS", "认证与会话", "输入验证", "SQL 注入防御", "XSS 输出编码", "文件上传隔离", "SSRF 出站控制", "安全编码复盘"], "depth": 3, "navigation": "节点可跳转到课程知识点和相关练习。"},
        },
        {
            "key": "websec-map-v2", "type": "mindmap", "slug": "http-basics", "version": 2,
            "title": "WEBSEC-101 防御知识地图（先修标注版）", "parent": "websec-map-v1",
            "content": {
                "source_type": "curated-demo",
                "change_summary": "标注同源策略到 XSS、Cookie 到 CSRF 的先修边，并补齐可跳转的三层节点",
                "depth": 3,
                "nodes": [
                    {"id": "root", "parent": None, "label": "WEBSEC-101 防御学习", "knowledge_point": "课程总览"},
                    {"id": "http", "parent": "root", "label": "HTTP 与浏览器边界", "knowledge_point": "HTTP / HTTPS 协议基础"},
                    {"id": "http-method", "parent": "http", "label": "请求方法与状态码", "knowledge_point": "HTTP / HTTPS 协议基础"},
                    {"id": "same-origin", "parent": "http", "label": "同源策略与 CORS", "knowledge_point": "同源策略与 CORS"},
                    {"id": "session", "parent": "http", "label": "Cookie 与会话", "knowledge_point": "Cookie / Session / Token 鉴权"},
                    {"id": "session-flags", "parent": "session", "label": "Secure、HttpOnly、SameSite", "knowledge_point": "Cookie / Session / Token 鉴权"},
                    {"id": "input", "parent": "root", "label": "输入与数据访问", "knowledge_point": "输入验证"},
                    {"id": "parameter", "parent": "input", "label": "参数化查询", "knowledge_point": "SQL 注入原理"},
                    {"id": "allowlist", "parent": "input", "label": "结构化选项白名单", "knowledge_point": "SQL 注入原理"},
                    {"id": "audit", "parent": "input", "label": "拒绝路径审计", "knowledge_point": "安全编码与修复闭环"},
                    {"id": "output", "parent": "root", "label": "浏览器输出与 XSS 防御", "knowledge_point": "反射型 XSS"},
                    {"id": "context", "parent": "output", "label": "上下文编码", "knowledge_point": "反射型 XSS"},
                    {"id": "safe-sink", "parent": "output", "label": "安全 sink 与模板", "knowledge_point": "DOM-based XSS"},
                    {"id": "rich-text", "parent": "output", "label": "富文本治理", "knowledge_point": "存储型 XSS"},
                    {"id": "csp", "parent": "output", "label": "CSP 补充控制", "knowledge_point": "安全编码与修复闭环"},
                    {"id": "server", "parent": "root", "label": "服务端攻击面收敛", "knowledge_point": "服务端防御"},
                    {"id": "upload", "parent": "server", "label": "上传隔离与扫描", "knowledge_point": "文件上传漏洞"},
                    {"id": "outbound", "parent": "server", "label": "SSRF 出站控制", "knowledge_point": "SSRF 与内网穿透"},
                    {"id": "dns", "parent": "outbound", "label": "域名、DNS 与地址段校验", "knowledge_point": "SSRF 与内网穿透"},
                    {"id": "review", "parent": "root", "label": "修复验证与复盘", "knowledge_point": "安全编码与修复闭环"},
                    {"id": "evidence", "parent": "review", "label": "Evidence 与回归记录", "knowledge_point": "安全编码与修复闭环"}
                ],
                "navigation": "节点可跳转到同名知识点、相关课程资料或已发布练习；路线关系来自受控课程整理。",
                "next_step": "选择当前薄弱节点，进入关联资源或阶段练习。",
            },
        },
        {
            "key": "sql-xss-practice-set", "type": "quiz", "slug": "sql-injection", "version": 1,
            "title": "输入处理与浏览器输出阶段练习", "parent": None,
            "content": {"source_type": "curated-demo", "question_count": 8, "question_types": ["单选", "多选", "填空", "简答"], "knowledge_points": ["SQL 注入原理", "反射型 XSS", "DOM-based XSS"], "difficulty_layers": ["基础辨识", "情境分析", "修复验证"], "scoring_rule": "客观题按冻结答案确定性评分；简答题仅提供 Evidence 化建议，教师复核后才可发布最终成绩。", "explanation_boundary": "每题解析链接到课程知识点和 Evidence；不提供可直接滥用的攻击载荷。", "quality_state": "已发布且通过题目质量检查的课程练习入口", "next_step": "完成真实已发布题目后查看评分反馈。"},
        },
        {
            "key": "upload-lab", "type": "lab", "slug": "file-upload", "version": 1,
            "title": "文件上传防御验收实操", "parent": None,
            "content": {"source_type": "curated-demo", "prerequisites": ["了解 MIME、文件路径和对象存储边界", "能阅读服务端上传校验日志"], "task": "为一个课程资料上传入口设计类型校验、隔离存储、异步处理与复核日志方案。", "deliverables": ["校验清单", "验收记录", "失败路径说明"], "acceptance": ["类型、大小和扩展名按服务端白名单验证", "服务器重新命名并存放于 Web 根目录外", "处理失败、拒绝和人工复核均有可查询日志", "下载或预览经过权限校验"], "common_mistakes": ["只依赖浏览器提交的 MIME", "沿用原始文件名", "把拒绝原因写入公开响应", "把扫描结果当作授权检查"], "result_example": "验收记录示例：8 项控制中 8 项通过；一次异常类型请求被拒绝并写入最小审计事件，未产生可访问对象。", "defensive_review": "复盘重点是证明隔离、权限和日志在允许与拒绝路径都有效；本实操不提供攻击载荷、绕过步骤或工具链。", "next_step": "提交校验清单后进入上传与出站控制作业。"},
        },
        {
            "key": "ssrf-reading", "type": "readings", "slug": "ssrf", "version": 1,
            "title": "SSRF 出站边界阅读导引", "parent": None,
            "content": {"source_type": "external-preview", "reading_goal": "理解 URL 预览与服务端出站请求的边界", "summary": "围绕 allowlist、DNS/IP 校验、协议限制、重定向处理和网络隔离组织阅读；目标是建立可测试的出站控制，而不是复现请求绕过。", "keywords": ["allowlist", "DNS", "内网地址", "出站网络", "重定向"], "estimated_minutes": 18, "source_url": "https://owasp.org/www-community/attacks/Server_Side_Request_Forgery", "related_exercise": "阅读后，为 URL 预览功能写出域名校验、地址段拒绝和失败审计三条验收条件。", "rights_note": "外部公开资料链接；SecureHub 只提供导引和跳转，不托管全文。", "next_step": "完成 SSRF 防御检查点。"},
        },
        {
            "key": "websec-video-script", "type": "video", "slug": "secure-coding", "version": 1,
            "title": "安全修复闭环讲解脚本与分镜", "parent": None,
            "content": {"source_type": "curated-demo", "artifact_kind": "讲解脚本/分镜", "is_playable_video": False, "segments": [{"title": "风险识别", "goal": "用请求边界和日志说明问题范围"}, {"title": "修复设计", "goal": "选择授权、输入、输出或出站控制"}, {"title": "验证与复盘", "goal": "保留回归结果、Evidence 与残余风险"}], "external_link": "https://www.bilibili.com/", "source_note": "外部链接仅用于后续公开内容跳转；当前资源是讲解脚本/分镜，不是平台自有或可播放视频成品。", "next_step": "查看安全编码复盘清单，或跳转外部公开目录。"},
        },
    )


# These are persisted learning records, not a replacement for a new tutor
# request.  The UI must label them as curated course material; new questions
# continue through tutor_routing_v3 and its RAG/Evidence safety boundary.
SHOWCASE_TUTOR_EXCHANGES: tuple[dict[str, str], ...] = (
    {
        "question": "联合查询注入为什么要先判断列数？",
        "concept": "在经过授权的课程复盘里，理解查询结果列数需要兼容，能帮助解释为什么不应把外部输入拼接进查询结构。防御重点不是试探外部系统，而是让查询结构由服务端固定，外部值只走参数绑定。",
        "defensive_example": "课程作业中的报表接口把允许的字段和排序方式映射为服务端枚举；数据过滤条件使用参数绑定，并为异常输入记录最小审计事件与回归测试结果。",
        "next_step": "回看“输入验证与参数化查询防御学习单”的查询结构边界，再完成已发布练习中的防御性说明题。",
        "evidence_status": "available",
    },
    {
        "question": "为什么参数化查询不能替代排序字段的白名单？",
        "concept": "参数化查询适合把不可信数据值与查询语法分离；排序字段属于结构化选项，需要由服务端映射到有限、经过审核的字段集合。两种控制分别覆盖不同边界。",
        "defensive_example": "课程列表接口把筛选值作为参数绑定，把“按截止时间”映射为固定列名；未知排序选项返回可理解的校验错误并记录最小审计信息。",
        "next_step": "打开“输入验证与参数化查询防御学习单”，完成检查清单后进入已发布练习。",
        "evidence_status": "available",
    },
    {
        "question": "XSS 防御为什么要区分输出上下文？",
        "concept": "HTML 文本、属性、URL 和脚本上下文由不同解析规则处理。安全设计应采用受信模板、上下文编码和安全 sink，而不是依赖一种通用字符串替换。",
        "defensive_example": "展示搜索关键字时优先使用模板默认转义或 textContent；链接先验证协议与目标，再写入受控属性。复盘同时检查历史富文本是否经过白名单净化。",
        "next_step": "查看浏览器输出边界课件的“输出上下文”和“DOM 安全 sink”页，再完成阶段作业。",
        "evidence_status": "available",
    },
    {
        "question": "上传验收为什么既要隔离存储，也要保留失败日志？",
        "concept": "隔离存储减少文件被直接执行或公开访问的机会；失败日志让教师和开发者能够复核控制是否在拒绝路径真正生效。两者共同支持可验证的防御闭环。",
        "defensive_example": "服务端重新命名文件、验证类型和大小，并将对象存放在 Web 根目录外。拒绝的请求只返回必要说明，完整的校验结果写入受权限保护的审计记录。",
        "next_step": "进入文件上传防御验收实操，提交校验清单和失败路径说明。",
        "evidence_status": "available",
    },
    {
        "question": "URL 预览功能怎样建立 SSRF 出站边界？",
        "concept": "服务端需要把外部访问当作受控能力：限制允许的域名和协议，校验解析后的地址，拒绝内网和保留地址段，并对重定向结果再次验证。",
        "defensive_example": "阅读导引中的检查点要求把域名白名单、DNS/IP 校验、超时和出站日志写成可测试条件；浏览器隐藏输入框不能替代服务端控制。",
        "next_step": "阅读 SSRF 出站边界导引，完成三个验收条件后再开始复盘。",
        "evidence_status": "available",
    },
    {
        "question": "能否根据当前课程资料判断某个未提供上下文的外部系统是否安全？",
        "concept": "不能。当前课程没有该外部系统的已授权证据、实现细节或测试记录，不能据此给出安全结论。",
        "defensive_example": "请先提供经过授权的架构说明、日志或测试范围；系统会在证据不足时保留边界，而不是用通用经验替代事实判断。",
        "next_step": "回到课程内的已知案例，或将需要人工复核的问题提交给课程教师。",
        "evidence_status": "insufficient",
    },
)


async def _seed_prerequisites(session: AsyncSession) -> None:
    await seed_agents(session)
    await seed_agent_skills(session)
    await seed_demo_user(session)
    await seed_course_websec(session)
    await seed_education_domain(session)


async def _seed_class_and_groups(session: AsyncSession, counts: dict[str, int]) -> dict[str, UUID]:
    _, created = await _ensure(
        session, TeachingClass, SHOWCASE_CLASS_B_ID,
        course_id=COURSE_WEBSEC_ID, code="WEBSEC-2026-B", name="Web 安全基础 · 2026 春 B 班",
        status="active", created_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["teaching_classes"] += int(created)
    _, created = await _ensure(
        session, TeachingClassTeacher, SHOWCASE_CLASS_B_TEACHER_ID,
        teaching_class_id=SHOWCASE_CLASS_B_ID, teacher_id=DEMO_COURSE_TEACHER_ID,
        role="owner", status="active", assigned_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["teaching_class_teachers"] += int(created)
    groups = {
        "a1": DEMO_STUDENT_GROUP_ID,
        "a2": SHOWCASE_A_GROUP_B_ID,
        "b1": SHOWCASE_B_GROUP_A_ID,
        "b2": SHOWCASE_B_GROUP_B_ID,
    }
    for key, class_id, name in (
        ("a2", DEMO_TEACHING_CLASS_ID, "实验 B 组"),
        ("b1", SHOWCASE_CLASS_B_ID, "案例复盘组"),
        ("b2", SHOWCASE_CLASS_B_ID, "防御验证组"),
    ):
        _, created = await _ensure(
            session, StudentGroup, groups[key], teaching_class_id=class_id, name=name,
            status="active", created_by=DEMO_COURSE_TEACHER_ID,
        )
        counts["student_groups"] += int(created)
    return groups


async def _seed_students(
    session: AsyncSession, groups: dict[str, UUID], counts: dict[str, int]
) -> dict[UUID, tuple[str, int, UUID]]:
    password_hash = hash_password(DEMO_USER_PASSWORD)
    rows: dict[UUID, tuple[str, int, UUID]] = {}
    for index, (slug, alias, story, class_key, group_key) in enumerate(SHOWCASE_STUDENTS):
        student_id = _student_id(slug)
        class_id = DEMO_TEACHING_CLASS_ID if class_key == "a" else SHOWCASE_CLASS_B_ID
        user, created = await _ensure(
            session, User, student_id,
            email=f"websec-{slug}@securehub.local", display_name=alias,
            hashed_password=password_hash, is_active=True, role="student",
        )
        del user
        counts["students"] += int(created)
        enrollment_id = _id("enrollment", slug)
        _, created = await _ensure(
            session, CourseEnrollment, enrollment_id,
            course_id=COURSE_WEBSEC_ID, student_id=student_id, teaching_class_id=class_id,
            status="enrolled", enrolled_by=DEMO_COURSE_TEACHER_ID, enrolled_at=SEED_AT - timedelta(days=96),
        )
        counts["enrollments"] += int(created)
        member_id = _id("group-member", slug)
        _, created = await _ensure(
            session, StudentGroupMember, member_id,
            group_id=groups[group_key], student_id=student_id, status="active",
            changed_by=DEMO_COURSE_TEACHER_ID, changed_at=SEED_AT - timedelta(days=90),
        )
        counts["group_members"] += int(created)

        scores = _story_scores(story, index)
        dimensions = {
            "profile_kind": "fictional_course_alias",
            "seed_profile": PROFILE,
            "learning_story": story,
            "learning_story_summary": _story_label(story),
            "course_id": str(COURSE_WEBSEC_ID),
            "current_progress": scores["progress"],
            "recommended_next_step": "完成关联资源后进入真实已发布练习。",
            "source_boundary": "受控预置课程场景；不是在校学生或实时模型生成画像。",
        }
        profile = await session.get(UserProfile, student_id)
        if profile is None:
            session.add(UserProfile(user_id=student_id, dimensions=dimensions, embedding=None))
            counts["profiles"] += 1
        elif profile.dimensions != dimensions:
            profile.dimensions = dimensions
        for capability, score in (
            ("web_security", round((scores["http"] + scores["auth"] + scores["input"] + scores["xss"]) / 4, 3)),
            ("http_security", scores["http"]),
            ("authentication", scores["auth"]),
            ("input_validation", scores["input"]),
            ("xss_defense", scores["xss"]),
            ("secure_coding", round((scores["input"] + scores["xss"]) / 2, 3)),
            ("learning_progress", scores["progress"]),
        ):
            cap_id = _id("capability", f"{slug}:{capability}")
            cap = await session.get(UserCapability, cap_id)
            metadata = {"seed_profile": PROFILE, "story": story, "course_id": str(COURSE_WEBSEC_ID)}
            if cap is None:
                session.add(UserCapability(
                    id=cap_id, user_id=student_id, dimension=capability, score=score,
                    confidence=round(0.69 + (index % 5) * 0.04, 2), evidence_count=6, metadata_=metadata,
                ))
                counts["capabilities"] += 1
            elif (cap.score, cap.confidence, cap.evidence_count, cap.metadata_) != (
                score, round(0.69 + (index % 5) * 0.04, 2), 6, metadata
            ):
                cap.score = score
                cap.confidence = round(0.69 + (index % 5) * 0.04, 2)
                cap.evidence_count = 6
                cap.metadata_ = metadata
        rows[student_id] = (story, index, class_id)

    await _seed_demo_showcase_student(session, counts, rows)
    await session.flush()
    return rows


async def _seed_demo_showcase_student(
    session: AsyncSession,
    counts: dict[str, int],
    rows: dict[UUID, tuple[str, int, UUID]],
) -> None:
    """Overlay the existing demo account with a scoped fictional course record.

    The base seed owns the user, credentials, role, enrollment, and group
    membership.  The showcase profile only adds course-facing projection data
    and never creates a second account for the same login.
    """

    user = await session.get(User, DEMO_USER_ID)
    if user is None or user.email != DEMO_USER_EMAIL or user.role != "student":
        raise RuntimeError("showcase demo learner prerequisite is missing or has an invalid role")

    enrollment = await session.get(CourseEnrollment, DEMO_ENROLLMENT_ID)
    if (
        enrollment is None
        or enrollment.student_id != DEMO_USER_ID
        or enrollment.course_id != COURSE_WEBSEC_ID
        or enrollment.teaching_class_id != DEMO_TEACHING_CLASS_ID
        or enrollment.status != "enrolled"
    ):
        raise RuntimeError("showcase demo learner is missing its base WEBSEC-101 enrollment")
    member = await session.get(StudentGroupMember, DEMO_GROUP_MEMBER_ID)
    if (
        member is None
        or member.student_id != DEMO_USER_ID
        or member.group_id != DEMO_STUDENT_GROUP_ID
        or member.status != "active"
    ):
        raise RuntimeError("showcase demo learner is missing its base teaching-group membership")

    if user.display_name != SHOWCASE_DEMO_STUDENT_DISPLAY_NAME:
        user.display_name = SHOWCASE_DEMO_STUDENT_DISPLAY_NAME
        counts["demo_student_display_overlay"] += 1

    story = SHOWCASE_DEMO_STUDENT_STORY
    index = SHOWCASE_DEMO_STUDENT_INDEX
    scores = _story_scores(story, index)
    overlay_dimensions = {
        "profile_kind": "fictional_course_demo_learner",
        "seed_profile": PROFILE,
        "showcase_account": SHOWCASE_DEMO_STUDENT_SLUG,
        "learning_story": story,
        "learning_story_summary": _story_label(story),
        "course_id": str(COURSE_WEBSEC_ID),
        "current_progress": scores["progress"],
        "recommended_next_step": "完成输入验证复盘后进入已发布的课程练习。",
        "source_boundary": "受控预置课程演示学员；复用本地 demo 登录，不是真实在校学生或实时模型生成画像。",
    }
    profile = await session.get(UserProfile, DEMO_USER_ID)
    if profile is None:
        session.add(UserProfile(user_id=DEMO_USER_ID, dimensions=overlay_dimensions, embedding=None))
        counts["demo_student_profile_overlay"] += 1
    else:
        merged_dimensions = {**dict(profile.dimensions or {}), **overlay_dimensions}
        if profile.dimensions != merged_dimensions:
            profile.dimensions = merged_dimensions
            counts["demo_student_profile_overlay"] += 1

    capability_scores = {
        "web_security": round(
            (scores["http"] + scores["auth"] + scores["input"] + scores["xss"]) / 4,
            3,
        ),
        "http_security": scores["http"],
        "authentication": scores["auth"],
        "input_validation": scores["input"],
        "xss_defense": scores["xss"],
        "secure_coding": round((scores["input"] + scores["xss"]) / 2, 3),
        "learning_progress": scores["progress"],
    }
    metadata = {
        "seed_profile": PROFILE,
        "story": story,
        "course_id": str(COURSE_WEBSEC_ID),
        "source_boundary": "受控课程演示能力快照；由课程 scenario seed 写入，不是实时模型评分。",
    }
    confidence = round(0.69 + (index % 5) * 0.04, 2)
    for dimension, score in capability_scores.items():
        capability_id = _id("capability", f"{SHOWCASE_DEMO_STUDENT_SLUG}:{dimension}")
        capability = await session.get(UserCapability, capability_id)
        if capability is None:
            existing = await session.scalar(
                select(UserCapability).where(
                    UserCapability.user_id == DEMO_USER_ID,
                    UserCapability.dimension == dimension,
                )
            )
            if existing is not None:
                # A separately managed capability remains authoritative.  It
                # is not overwritten simply because the local showcase seed runs.
                continue
            session.add(
                UserCapability(
                    id=capability_id,
                    user_id=DEMO_USER_ID,
                    dimension=dimension,
                    score=score,
                    confidence=confidence,
                    evidence_count=6,
                    metadata_=metadata,
                )
            )
            counts["demo_student_capabilities"] += 1
            continue
        if capability.user_id != DEMO_USER_ID or capability.dimension != dimension:
            raise RuntimeError("showcase demo capability identifier conflicts with another record")
        if (
            capability.score,
            capability.confidence,
            capability.evidence_count,
            capability.metadata_,
        ) != (score, confidence, 6, metadata):
            capability.score = score
            capability.confidence = confidence
            capability.evidence_count = 6
            capability.metadata_ = metadata

    rows[DEMO_USER_ID] = (story, index, DEMO_TEACHING_CLASS_ID)


async def _seed_showcase_quizzes(session: AsyncSession, counts: dict[str, int]) -> dict[str, UUID]:
    ids: dict[str, UUID] = {}
    for item in SHOWCASE_QUIZZES:
        quiz_id = _quiz_id(str(item["key"]))
        ids[str(item["key"])] = quiz_id
        slug = str(item["slug"])
        _, created = await _ensure(
            session, QuizItem, quiz_id,
            kp_id=node_id(slug), canonical_key=f"websec:showcase:v1:{item['key']}", content_version=1,
            type=str(item["type"]), question=str(item["question"]), options=item["options"],
            answer=str(item["answer"]), explanation=str(item["explanation"]), difficulty=int(item["difficulty"]),
            review_status="curated", source_status="seeded",
            generated_by_skill=None,
        )
        counts["quiz_items"] += int(created)
        evidence_id = _id("quiz-evidence", str(item["key"]))
        _, created = await _ensure(
            session, QuizItemEvidence, evidence_id,
            quiz_item_id=quiz_id, chunk_id=chunk_id(slug, 1), citation_label=f"{slug} 课程证据切片 1",
        )
        counts["quiz_evidence"] += int(created)
    await session.flush()
    quality = await QuizQualityService(session).validate_course(course_id=COURSE_WEBSEC_ID)
    if quality.result != "passed":
        failures = ", ".join(
            f"{row.canonical_key}:{'/'.join(row.failure_codes)}" for row in quality.failure_samples
        )
        raise RuntimeError(f"showcase quiz quality gate failed: {failures}")
    counts["quality_passed_items"] = len([item for item in quality.items if item.result == "passed"])
    return ids


async def _seed_runs_and_evidence(session: AsyncSession, counts: dict[str, int]) -> list[tuple[UUID, UUID]]:
    specs = (
        ("teaching-insight", "sql-injection", {"suggested_score": 74.0}),
        ("syllabus-candidate", "secure-coding", {"typed_syllabus": _typed_syllabus_content()}),
        ("subjective-grade", "xss-reflected", {"suggested_score": 7.5}),
        ("resource-curation", "file-upload", {"resource_summary": "上传防御实操资源经过预置课程审核。"}),
        ("course-update", "ssrf", {"signal_summary": "将 SSRF 出站控制加入近期复盘。"}),
        ("student-tutoring", "cookie-session", {"answer_boundary": "给出防御性解释并指向课程证据。"}),
    )
    pairs: list[tuple[UUID, UUID]] = []
    for offset, (key, slug, output) in enumerate(specs):
        workflow_id = _id("workflow-run", key)
        run_id = _id("agent-run", key)
        evidence_id = _id("evidence", key)
        _, created = await _ensure(
            session, WorkflowRun, workflow_id,
            workflow_name="websec_showcase_seed", workflow_version="curated-v1", workflow_definition_digest="showcase-seed",
            catalog_version="production-catalog-v1", provider_policy_version="curated-demo-v1",
            checkpoint_schema_version="v1", runtime_build_sha="showcase-seed", user_id=DEMO_COURSE_TEACHER_ID,
            credential_id=None, status="succeeded", state_version=1, mode="curated-demo",
            requested_provider=None, requested_model=None,
            input_payload={"course_id": str(COURSE_WEBSEC_ID), "seed_profile": PROFILE, "purpose": key},
            output_ref={"seed_profile": PROFILE, "purpose": key}, budget={}, error={}, idempotency_key=f"{PROFILE}:{key}",
            cancel_requested_at=None, lease_owner=None, lease_expires_at=None, lease_epoch=0, next_event_sequence=1,
            started_at=SEED_AT + timedelta(minutes=offset), finished_at=SEED_AT + timedelta(minutes=offset + 1),
        )
        counts["workflow_runs"] += int(created)
        chunk = chunk_id(slug, 1)
        _, created = await _ensure(
            session, AgentRun, run_id,
            workflow_name="websec_showcase_seed", user_id=DEMO_COURSE_TEACHER_ID, agent_id=None, skill_id=None,
            parent_run_id=None, workflow_run_id=workflow_id, step_attempt_id=None, attempt=1,
            provider="curated-demo", model="pre-generated-course-content", error_code=None,
            started_at=SEED_AT + timedelta(minutes=offset), finished_at=SEED_AT + timedelta(minutes=offset + 1),
            input_summary={"course_id": str(COURSE_WEBSEC_ID), "purpose": key, "source_kind": "curated-demo"},
            output_summary={**output, "course_id": str(COURSE_WEBSEC_ID), "source_kind": "curated-demo", "not_live_generated": True},
            evidence_chunk_ids=_evidence_ids(session, chunk), quality_score=0.9, status="succeeded", duration_ms=450, token_usage={"mode": "curated-demo", "total_tokens": 0},
        )
        counts["agent_runs"] += int(created)
        _, created = await _ensure(
            session, WorkflowEvidenceSnapshot, evidence_id,
            workflow_run_id=workflow_id, step_attempt_id=None, agent_run_id=run_id, chunk_id=str(chunk),
            document_id=str(document_id(slug)), chunk_version="showcase-v1",
            content_digest=sha256(f"{PROFILE}:{key}:{chunk}".encode()).hexdigest(),
            excerpt="预置课程证据切片；来源、时间和版权说明保留在 Evidence 详情。",
            citation={"chunk_id": str(chunk), "course_id": str(COURSE_WEBSEC_ID), "seed_profile": PROFILE},
            source={"source_kind": "curated-demo", "course_id": str(COURSE_WEBSEC_ID)},
            rights={"note": "仅用于受控课程演示，来源边界需在详情中展示。"}, rank=1,
        )
        counts["evidence_snapshots"] += int(created)
        pairs.append((run_id, evidence_id))
    return pairs


def _typed_syllabus_content() -> dict[str, Any]:
    return {
        "title": "WEBSEC-101 Web 安全基础教学大纲（预置课程候选）",
        "summary": "本大纲围绕 HTTP 边界、认证与会话、输入处理、浏览器输出、上传与服务端出站控制展开。每个模块以可解释的防御案例、练习和验收为主，适用于两个教学班的分层复盘。内容为受控课程整理，Evidence 与运行编号保留在版本详情中。",
        "learning_outcomes": ["识别 Web 请求、认证和授权边界", "针对常见输入与输出风险选择防御控制", "用证据、测试和复盘说明修复是否有效"],
        "modules": [
            {"module_id": "m1", "title": "HTTP、同源与会话边界", "knowledge_node_ids": [str(node_id("http-basics")), str(node_id("same-origin")), str(node_id("cookie-session"))], "learning_outcome": "能够说明浏览器与服务端边界如何影响认证和跨站请求。", "activities": ["请求链路标注", "会话配置检查"]},
            {"module_id": "m2", "title": "输入验证与数据访问", "knowledge_node_ids": [str(node_id("sql-injection")), str(node_id("sql-injection-blind"))], "learning_outcome": "能够区分数据参数和结构化选项，并提出参数化查询与白名单策略。", "activities": ["查询边界案例分析", "回归检查清单"]},
            {"module_id": "m3", "title": "浏览器输出与 XSS 防御", "knowledge_node_ids": [str(node_id("xss-reflected")), str(node_id("xss-stored")), str(node_id("xss-dom"))], "learning_outcome": "能够按输出上下文选择编码、模板与 CSP 防御。", "activities": ["危险 sink 审计", "富文本治理复盘"]},
            {"module_id": "m4", "title": "上传、SSRF 与安全修复闭环", "knowledge_node_ids": [str(node_id("file-upload")), str(node_id("ssrf")), str(node_id("secure-coding"))], "learning_outcome": "能够设计上传隔离和出站请求控制，并用验证记录完成复盘。", "activities": ["防御性验收实操", "Evidence 驱动的修复说明"]},
        ],
        "assessment_plan": "采用分层练习、阶段作业、教师复核和已发布成绩反馈；AI 结果仅作为引用 Evidence 的建议，不自动决定成绩。",
        "source_note": "课程整理来源与 Evidence Snapshot 均为受控预置记录，不宣称为实时模型生成。",
    }


async def _seed_resources(session: AsyncSession, counts: dict[str, int]) -> dict[str, UUID]:
    resource_ids: dict[str, UUID] = {}
    for item in _resource_definitions():
        key = str(item["key"])
        resource_id = _id("resource", key)
        resource_ids[key] = resource_id
        parent_key = item["parent"]
        parent_id = _id("resource", str(parent_key)) if parent_key else None
        root_id = parent_id or resource_id
        _, created = await _ensure(
            session, GeneratedResource, resource_id,
            user_id=None, course_id=COURSE_WEBSEC_ID, kp_id=node_id(str(item["slug"])), agent_run_id=None,
            workflow_run_id=None, step_attempt_id=None, parent_resource_id=parent_id, lineage_root_id=root_id,
            version=int(item["version"]), resource_type=str(item["type"]), title=str(item["title"]),
            content=item["content"], object_key=None,
            evidence_chunk_ids=_evidence_ids(session, chunk_id(str(item["slug"]), 1)),
            quality_score=0.9, status="ready", metadata_={
                "seed_profile": PROFILE,
                "source_kind": item["content"]["source_type"],
                "logical_key": key,
                "quality_state": "curated_reviewed" if item["content"]["source_type"] == "curated-demo" else "external_preview",
                "not_live_generated": True,
            },
        )
        counts["resources"] += int(created)
        version_id = _id("resource-version", key)
        _, created = await _ensure(
            session, ResourceVersion, version_id, resource_id=resource_id, version=int(item["version"]),
            content=item["content"], object_key=None,
            change_summary=str(item["content"].get("change_summary") or "课程整理初始版本"),
            metadata_={"seed_profile": PROFILE, "source_kind": item["content"]["source_type"], "logical_key": key},
        )
        counts["resource_versions"] += int(created)
    return resource_ids


async def _seed_learning_data(
    session: AsyncSession,
    students: dict[UUID, tuple[str, int, UUID]],
    quizzes: dict[str, UUID],
    resources: dict[str, UUID],
    counts: dict[str, int],
) -> None:
    attempt_quizzes = [
        quizzes["http-security-boundary"], quizzes["session-cookie-flags"], quizzes["input-validation-layering"],
        quizzes["contextual-output-encoding"], quizzes["upload-defense-checklist"], quizzes["ssrf-outbound-allowlist"],
    ]
    attempt_nodes = ["http-basics", "cookie-session", "sql-injection", "xss-reflected", "file-upload", "ssrf"]
    for student_id, (story, index, _) in students.items():
        path_id = _id("learning-path", str(student_id))
        _, created = await _ensure(
            session, LearningPath, path_id, user_id=student_id, course_id=COURSE_WEBSEC_ID,
            title="WEBSEC-101 防御学习路径", objective=_story_label(story), status="active",
            metadata_={"seed_profile": PROFILE, "story": story, "source_kind": "curated-demo"},
        )
        counts["learning_paths"] += int(created)
        for task_index, slug in enumerate(("http-basics", "sql-injection", "xss-reflected", "file-upload", "ssrf"), start=1):
            task_id = _id("learning-task", f"{student_id}:{slug}")
            state = "done" if task_index <= (2 if story == "recovery" else 3) else "todo"
            _, created = await _ensure(
                session, LearningTask, task_id, path_id=path_id, kp_id=node_id(slug),
                title=f"{slug} 防御学习任务", task_type="course_learning", order_index=task_index,
                status=state, metadata_={"seed_profile": PROFILE, "story": story},
            )
            counts["learning_tasks"] += int(created)
        baseline, recent = _attempt_scores(story, index)
        for window, scores, start in (("baseline", baseline, BASELINE_START), ("recent", recent, RECENT_START)):
            for item_index, (quiz_id, slug, score) in enumerate(zip(attempt_quizzes, attempt_nodes, scores, strict=True)):
                attempt_id = _id("quiz-attempt", f"{student_id}:{window}:{slug}")
                correct = score >= 0.6
                _, created = await _ensure(
                    session, QuizAttempt, attempt_id, quiz_item_id=quiz_id, user_id=student_id,
                    submitted_answer={"answer": "已掌握的防御性要点" if correct else "需要复盘的概念"},
                    is_correct=correct, score=score,
                    feedback="受控预置的真实作答记录；用于课程聚合与教师复盘，不是实时生成成绩。",
                    metadata_={"seed_profile": PROFILE, "story": story, "window": window, "course_id": str(COURSE_WEBSEC_ID)},
                    created_at=start + timedelta(days=index % 12, minutes=item_index), updated_at=start + timedelta(days=index % 12, minutes=item_index),
                )
                counts["quiz_attempts"] += int(created)
        event_specs = (
            ("course_entry", "http-basics", None, BASELINE_START),
            ("resource_opened", "sql-injection", resources["input-validation-guide-v2"], BASELINE_START + timedelta(days=7)),
            ("quiz_completed", "sql-injection", None, BASELINE_START + timedelta(days=14)),
            ("resource_opened", "xss-reflected", resources["xss-defense-slides-v2"], RECENT_START),
            ("practice_reviewed", "file-upload", resources["upload-lab"], RECENT_START + timedelta(days=8)),
            ("path_progress", "ssrf", resources["ssrf-reading"], RECENT_START + timedelta(days=18)),
        )
        for event_index, (event_type, slug, resource_id, occurred) in enumerate(event_specs):
            event_id = _id("learning-event", f"{student_id}:{event_index}")
            _, created = await _ensure(
                session, LearningEvent, event_id, user_id=student_id, event_type=event_type,
                kp_id=node_id(slug), resource_id=resource_id,
                result={"seed_profile": PROFILE, "story": story, "progress_signal": "improving" if story == "recovery" and event_index >= 3 else "observed"},
                occurred_at=occurred + timedelta(minutes=index),
            )
            counts["learning_events"] += int(created)
        tutor_slugs = ("sql-injection", "sql-injection", "xss-reflected", "file-upload", "ssrf", "secure-coding")
        for tutor_index, (exchange, slug) in enumerate(zip(SHOWCASE_TUTOR_EXCHANGES, tutor_slugs, strict=True), start=len(event_specs)):
            event_id = _id("learning-event", f"{student_id}:{tutor_index}")
            evidence_available = exchange["evidence_status"] == "available"
            _, created = await _ensure(
                session, LearningEvent, event_id, user_id=student_id, event_type="tutor_curated_exchange",
                kp_id=node_id(slug), resource_id=None,
                result={
                    "seed_profile": PROFILE,
                    "story": story,
                    "source_kind": "curated-demo",
                    "quick_reply_available": student_id == DEMO_USER_ID,
                    "source_boundary": "可恢复的受控课程辅导记录，不是实时模型回答；新提问仍需走 RAG、Evidence 和安全边界。",
                    "evidence_snapshot_id": str(_id("evidence", "student-tutoring")) if evidence_available else None,
                    **exchange,
                },
                occurred_at=RECENT_START + timedelta(days=20 + tutor_index, minutes=index),
            )
            counts["learning_events"] += int(created)


async def _seed_learning_loop(
    session: AsyncSession,
    students: dict[UUID, tuple[str, int, UUID]],
    resources: dict[str, UUID],
    counts: dict[str, int],
) -> None:
    """Seed durable baselines plus one actionable, student-owned loop context.

    These records are deliberately normal learning-path/resource rows.  They
    give the student UI a persistent baseline, a real course event behind a
    candidate, and a separately auditable initial recommendation without
    pretending that a provider has regenerated anything.
    """

    snapshots: dict[UUID, list[dict[str, Any]]] = {}
    version_ids: dict[UUID, UUID] = {}
    for student_id in students:
        path_id = _id("learning-path", str(student_id))
        task_rows = list(
            (
                await session.execute(
                    select(LearningTask, KnowledgeNode)
                    .outerjoin(KnowledgeNode, KnowledgeNode.id == LearningTask.kp_id)
                    .where(LearningTask.path_id == path_id)
                    .order_by(LearningTask.order_index)
                )
            ).all()
        )
        snapshot = [
            {
                "action": "retained",
                "title": task.title,
                "kp_id": str(task.kp_id) if task.kp_id else None,
                "knowledge_point": node.name if node is not None else None,
                "status": "active" if task.status == "in_progress" else task.status,
                "task_type": task.task_type,
                "order_index": task.order_index,
                "expected_minutes": int(dict(task.metadata_ or {}).get("expected_minutes") or 0),
                "metadata": dict(task.metadata_ or {}),
            }
            for task, node in task_rows
        ]
        snapshots[student_id] = snapshot
        version_id = _id("learning-path-version", str(student_id))
        version_ids[student_id] = version_id
        _, created = await _ensure(
            session,
            LearningPathVersion,
            version_id,
            path_id=path_id,
            user_id=student_id,
            course_id=COURSE_WEBSEC_ID,
            parent_version_id=None,
            trigger_event_id=None,
            trigger_workflow_run_id=None,
            version_no=1,
            state="active",
            kind="baseline",
            title="WEBSEC-101 防御学习路径",
            summary="受控课程场景中的已持久化学习路径基线；后续采纳会新建版本而非覆盖此记录。",
            diff={"added_tasks": [], "removed_tasks": []},
            task_snapshot=snapshot,
            metadata_={"seed_profile": PROFILE, "source_boundary": "受控预置学习路径基线，不是实时模型生成。"},
            created_at=SEED_AT,
            updated_at=SEED_AT,
        )
        counts["learning_path_versions"] += int(created)

    student_id = _student_id("hanyue")
    event_id = _id("learning-event", f"{student_id}:2")
    candidate_snapshot: list[dict[str, Any]] = []
    inserted = False
    for item in snapshots[student_id]:
        candidate_snapshot.append(dict(item))
        if item.get("kp_id") == str(node_id("sql-injection")) and item.get("status") != "done":
            candidate_snapshot.append(
                {
                    "action": "added",
                    "title": "输入验证与参数化查询防御性补强复盘",
                    "kp_id": str(node_id("sql-injection")),
                    "knowledge_point": "输入验证与参数化查询",
                    "status": "todo",
                    "task_type": "replan_review",
                    "order_index": len(candidate_snapshot) + 1,
                    "expected_minutes": 35,
                    "metadata": {"seed_profile": PROFILE, "reason": "student_replan"},
                }
            )
            inserted = True
    if not inserted:
        candidate_snapshot.append(
            {
                "action": "added",
                "title": "输入验证与参数化查询防御性补强复盘",
                "kp_id": str(node_id("sql-injection")),
                "knowledge_point": "输入验证与参数化查询",
                "status": "todo",
                "task_type": "replan_review",
                "order_index": len(candidate_snapshot) + 1,
                "expected_minutes": 35,
                "metadata": {"seed_profile": PROFILE, "reason": "student_replan"},
            }
        )
    for index, item in enumerate(candidate_snapshot, start=1):
        item["order_index"] = index

    candidate_id = _id("path-replan-candidate", "hanyue:sql-reinforcement")
    _, created = await _ensure(
        session,
        LearningPathReplanCandidate,
        candidate_id,
        student_id=student_id,
        course_id=COURSE_WEBSEC_ID,
        source_path_version_id=version_ids[student_id],
        accepted_path_version_id=None,
        trigger_event_id=event_id,
        trigger_workflow_run_id=None,
        affected_kp_id=node_id("sql-injection"),
        status="pending",
        reason_code="needs_reinforcement",
        reason_text="近期已评分作答显示输入验证与参数化查询仍需补强；候选只建议增加一项防御性复盘，不会自动修改既有课程或历史进度。",
        expected_minutes=35,
        proposed_task_snapshot=candidate_snapshot,
        recommendation_plan=[
            {
                "resource_id": str(resources["input-validation-guide-v2"]),
                "kp_id": str(node_id("sql-injection")),
                "rationale": "先阅读输入验证与参数化查询防御学习单，再决定是否采纳新的路径版本。",
            }
        ],
        input_fingerprint=sha256(f"{PROFILE}:hanyue:sql-reinforcement:v1".encode()).hexdigest(),
        metadata_={
            "seed_profile": PROFILE,
            "source_boundary": "候选引用受控课程场景中当前学生的真实持久化学习事件；不是实时模型生成结果。",
        },
        created_at=SEED_AT,
        updated_at=SEED_AT,
    )
    counts["learning_path_candidates"] += int(created)

    _, created = await _ensure(
        session,
        CourseResourceRecommendation,
        _id("course-resource-recommendation", "hanyue:input-validation-baseline"),
        student_id=student_id,
        course_id=COURSE_WEBSEC_ID,
        resource_id=resources["input-validation-guide-v2"],
        kp_id=node_id("sql-injection"),
        path_version_id=version_ids[student_id],
        source_candidate_id=None,
        status="scheduled",
        scheduled_at=SEED_AT,
        rationale="基于当前学生已持久化的输入验证作答和学习事件，先推送防御性学习单；学生可接受、暂缓、拒绝或提交反馈。",
        match_context={
            "seed_profile": PROFILE,
            "reason_code": "needs_reinforcement",
            "source_boundary": "受控课程推荐投影，不是实时模型生成。",
        },
        decision_reason=None,
        decided_at=None,
        created_at=SEED_AT,
        updated_at=SEED_AT,
    )
    counts["course_resource_recommendations"] += int(created)

    _, created = await _ensure(
        session,
        CourseResourceRecommendation,
        _id("course-resource-recommendation", "demo-student:input-validation-baseline"),
        student_id=DEMO_USER_ID,
        course_id=COURSE_WEBSEC_ID,
        resource_id=resources["input-validation-guide-v2"],
        kp_id=node_id("sql-injection"),
        path_version_id=version_ids[DEMO_USER_ID],
        source_candidate_id=None,
        status="scheduled",
        scheduled_at=SEED_AT,
        rationale="课程演示学员的已评分输入验证作答与持久化学习事件表明应先复盘参数化查询和结构化选项白名单；学生仍可自行决定后续路径动作。",
        match_context={
            "seed_profile": PROFILE,
            "reason_code": "needs_reinforcement",
            "source_boundary": "受控课程演示账号的持久化推荐投影，不是实时模型生成。",
        },
        decision_reason=None,
        decided_at=None,
        created_at=SEED_AT,
        updated_at=SEED_AT,
    )
    counts["course_resource_recommendations"] += int(created)


async def _aggregate_snapshot(
    session: AsyncSession, *, class_id: UUID, window_start: datetime, window_end: datetime
) -> tuple[int, dict[str, Any], str]:
    student_ids = list(
        (await session.execute(
            select(CourseEnrollment.student_id).where(
                CourseEnrollment.course_id == COURSE_WEBSEC_ID,
                CourseEnrollment.teaching_class_id == class_id,
                CourseEnrollment.status == "enrolled",
            )
        )).scalars()
    )
    rows = (await session.execute(
        select(QuizAttempt, KnowledgeNode)
        .join(QuizItem, QuizItem.id == QuizAttempt.quiz_item_id)
        .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
        .where(
            QuizAttempt.user_id.in_(student_ids), QuizAttempt.created_at >= window_start,
            QuizAttempt.created_at <= window_end, KnowledgeNode.course_id == COURSE_WEBSEC_ID,
        )
    )).all()
    by_node: dict[UUID, list[tuple[float, UUID, str]]] = defaultdict(list)
    names: dict[UUID, str] = {}
    for attempt, node in rows:
        if not isinstance(attempt.score, int | float):
            continue
        by_node[node.id].append((float(attempt.score), attempt.user_id, node.name))
        names[node.id] = node.name
    weak_points: list[dict[str, Any]] = []
    for node_id_value, values in by_node.items():
        average = sum(value for value, _, _ in values) / len(values)
        weak_points.append({
            "knowledge_node_id": str(node_id_value), "knowledge_node_name": names[node_id_value],
            "sample_size": len({student_id for _, student_id, _ in values}), "average_score": round(average, 6),
            "incorrect_rate": round(sum(1 for value, _, _ in values if value < 0.6) / len(values), 6),
        })
    weak_points.sort(key=lambda row: (row["average_score"], -row["sample_size"], row["knowledge_node_id"]))
    aggregate = {
        "weak_knowledge_points": weak_points[:12],
        "source_counts": {"quiz_attempts": len(rows), "enrolled_students": len(student_ids), "scored_students": len({row[0].user_id for row in rows if row[0].score is not None})},
        "limitations": "受控预置场景使用真实 quiz_attempts 聚合；画像和学习事件保持独立来源。",
        "seed_profile": PROFILE,
        "window_label": "baseline" if window_end <= RECENT_START else "recent",
    }
    fingerprint = sha256(json.dumps({"class_id": str(class_id), "window_start": window_start.isoformat(), "window_end": window_end.isoformat(), "aggregate": aggregate}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return len({row[0].user_id for row in rows if row[0].score is not None}), aggregate, fingerprint


async def _seed_snapshots_and_recommendations(
    session: AsyncSession, pairs: list[tuple[UUID, UUID]], counts: dict[str, int]
) -> dict[str, UUID]:
    snapshots: dict[str, UUID] = {}
    for class_key, class_id in (("a", DEMO_TEACHING_CLASS_ID), ("b", SHOWCASE_CLASS_B_ID)):
        for window_key, start, end in (("baseline", BASELINE_START, RECENT_START - timedelta(seconds=1)), ("recent", RECENT_START, RECENT_END)):
            snapshot_id = _id("weakness-snapshot", f"{class_key}:{window_key}")
            sample_size, aggregate, fingerprint = await _aggregate_snapshot(session, class_id=class_id, window_start=start, window_end=end)
            _, created = await _ensure(
                session, ClassWeaknessSnapshot, snapshot_id,
                course_id=COURSE_WEBSEC_ID, teaching_class_id=class_id, group_id=None,
                window_start=start, window_end=end, sample_size=sample_size,
                score_version="teacher-weakness-v1", input_fingerprint=fingerprint, aggregates=aggregate,
                computed_at=end,
            )
            counts["weakness_snapshots"] += int(created)
            snapshots[f"{class_key}:{window_key}"] = snapshot_id
    for version, (key, snapshot_key, pair_index, title, actions, rationale, state) in enumerate((
        ("input", "a:recent", 0, "输入验证分层复盘建议", ["为 A 班补充参数化查询与排序白名单案例", "布置 8 题分层复盘作业", "两周后复核最近窗口的作答变化"], "最近窗口中输入验证相关题目的有效样本达到阈值且均分低于班级其他主线知识点，建议先补先修解释再安排可评分练习。", "adopted"),
        ("xss", "b:recent", 1, "XSS 先修边与输出上下文复盘建议", ["先回看同源策略与 URL/HTML 输出上下文", "在 B 班使用课件复盘 DOM 安全 sink", "保留样本不足的小组为观察状态"], "B 班近期作答显示 XSS 相关理解与 HTTP/同源先修边存在差异，建议以证据化复盘和可编辑草稿推进，不自动改写已发布课程。", "pending"),
    ), start=1):
        run_id, evidence_id = pairs[pair_index]
        recommendation_id = _id("recommendation", key)
        snapshot_id = snapshots[snapshot_key]
        class_id = DEMO_TEACHING_CLASS_ID if snapshot_key.startswith("a:") else SHOWCASE_CLASS_B_ID
        _, created = await _ensure(
            session, TeachingRecommendation, recommendation_id,
            course_id=COURSE_WEBSEC_ID, teaching_class_id=class_id, group_id=None,
            source_snapshot_id=snapshot_id, evidence_snapshot_id=evidence_id, agent_run_id=run_id, version_no=version,
            diff={
                "kind": "curated-demo",
                "title": title,
                "actions": actions,
                "rationale": rationale,
                "expected_impact": "预置建议仅用于课程演示；后续影响必须由新的真实可评分作答快照复核，不以固定文本代替教学结果。",
                "source_boundary": "预置课程建议草稿；教师仍需编辑、确认并走原有审计。",
                **(
                    {
                        "pending_teaching_action": {
                            "id": str(_id("pending-teaching-action", key)),
                            "action_type": "review_assignment",
                            "title": "待审核：输入验证分层复盘作业",
                            "draft": (
                                "为目标教学班整理参数化查询、排序白名单与安全输出编码的防御性复盘任务。"
                                "教师需在审核后选择质量通过题目、明确教学班和截止时间；审核前不得生成学生可见"
                                "作业、课程更新或成绩变化。"
                            ),
                            "status": "pending_review",
                            "created_at": SEED_AT.isoformat(),
                        }
                    }
                    if state == "adopted"
                    else {}
                ),
            },
            status=state, created_by=DEMO_COURSE_TEACHER_ID,
        )
        counts["teaching_recommendations"] += int(created)
        if state == "adopted":
            decision_id = _id("recommendation-decision", key)
            _, created = await _ensure(
                session, TeachingRecommendationDecision, decision_id, recommendation_id=recommendation_id,
                teacher_id=DEMO_COURSE_TEACHER_ID, decision="adopt", reason="教师确认将其转为待审核复盘作业候选。", created_at=SEED_AT,
            )
            counts["recommendation_decisions"] += int(created)
    return snapshots


async def _seed_assets_and_syllabus(session: AsyncSession, pairs: list[tuple[UUID, UUID]], counts: dict[str, int]) -> None:
    for key, source_document_id, state, reason in (
        ("sql-guide", document_id("sql-injection"), "ready", "绑定输入验证与参数化查询课程讲义。"),
        ("xss-guide", document_id("xss-reflected"), "corrected", "已用包含 DOM 输出上下文的补充讲义完成更正。"),
        (
            "defensive-foundations-lecture",
            SHOWCASE_LECTURE_DOCUMENT_ID,
            "ready",
            "绑定受控预置的 Web 安全防御基础讲义；详情保留预置处理与来源边界。",
        ),
    ):
        document = await session.get(Document, source_document_id)
        if document is None:
            raise RuntimeError(f"showcase asset source document missing: {source_document_id}")
        asset = await session.scalar(select(DocumentAsset).where(DocumentAsset.document_id == document.id))
        binding_id = _id("document-binding", key)
        _, created = await _ensure(
            session, CourseDocumentBinding, binding_id, course_id=COURSE_WEBSEC_ID, document_id=document.id,
            bound_by=DEMO_COURSE_TEACHER_ID, purpose="teaching_material", status="active",
        )
        counts["course_document_bindings"] += int(created)
        governance_id = _id("asset-governance", key)
        _, created = await _ensure(
            session, CourseAssetGovernance, governance_id, binding_id=binding_id,
            document_asset_id=asset.id if asset else None, current_resource_id=None, owner_teacher_id=DEMO_COURSE_TEACHER_ID,
            version_no=1, state=state, correction_of_id=None, withdrawn_at=None, withdrawn_by=None,
            deleted_at=None, deleted_by=None, reason=reason,
        )
        counts["course_assets"] += int(created)
    syllabus_id = _id("syllabus", "websec")
    syllabus, created = await _ensure(
        session,
        CourseSyllabus,
        syllabus_id,
        course_id=COURSE_WEBSEC_ID,
        current_published_version_id=None,
    )
    counts["syllabuses"] += int(created)
    version_one_id = _id("syllabus-version", "v1")
    version_two_id = _id("syllabus-version", "v2")
    _, created = await _ensure(
        session, CourseSyllabusVersion, version_one_id, syllabus_id=syllabus_id, version_no=1,
        typed_content=_typed_syllabus_content(), content_schema_version="syllabus-v1", state="published",
        generated_from_agent_run_id=None, evidence_snapshot_id=None, created_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["syllabus_versions"] += int(created)
    if syllabus.current_published_version_id != version_one_id:
        syllabus.current_published_version_id = version_one_id
        await session.flush()
    run_id, evidence_id = pairs[1]
    revised = _typed_syllabus_content() | {"summary": _typed_syllabus_content()["summary"] + " 第二版候选增加了基于近期班级快照的分层复盘说明，仍需教师审核后才可能发布。"}
    _, created = await _ensure(
        session, CourseSyllabusVersion, version_two_id, syllabus_id=syllabus_id, version_no=2,
        typed_content=revised, content_schema_version="syllabus-v1", state="review_pending",
        generated_from_agent_run_id=run_id, evidence_snapshot_id=evidence_id, created_by=DEMO_COURSE_TEACHER_ID,
    )
    counts["syllabus_versions"] += int(created)
    review_id = _id("syllabus-review", "v1")
    _, created = await _ensure(
        session, SyllabusReviewDecision, review_id, version_id=version_one_id, reviewer_id=DEMO_COURSE_TEACHER_ID,
        decision="approve", reason="教师确认第一版作为受控课程基线，不自动覆盖课程目录。", created_at=SEED_AT,
    )
    counts["syllabus_reviews"] += int(created)


def _question_snapshot(item: QuizItem, node: KnowledgeNode) -> dict[str, Any]:
    return {
        "quiz_item_id": str(item.id), "canonical_key": item.canonical_key, "knowledge_node_id": str(node.id),
        "knowledge_node_name": node.name, "type": item.type, "question": item.question,
        "options": item.options if isinstance(item.options, list) else [], "answer": item.answer,
        "explanation": item.explanation, "content_version": item.content_version,
    }


async def _seed_assessments(
    session: AsyncSession, quizzes: dict[str, UUID], pairs: list[tuple[UUID, UUID]], counts: dict[str, int]
) -> None:
    selected_ids = [
        quizzes["http-security-boundary"], quizzes["session-cookie-flags"], quizzes["input-validation-layering"], quizzes["contextual-output-encoding"],
        quizzes["upload-defense-checklist"], quizzes["ssrf-outbound-allowlist"], quizzes["csrf-request-origin"], quizzes["cors-least-privilege"],
    ]
    item_rows = (await session.execute(
        select(QuizItem, KnowledgeNode).join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id).where(QuizItem.id.in_(selected_ids))
    )).all()
    by_id = {item.id: (item, node) for item, node in item_rows}
    if len(by_id) != len(selected_ids):
        raise RuntimeError("showcase assessment items are not ready")
    assignments = (
        ("input-review", "assignment", "WEBSEC-101-INPUT-REVIEW", "输入验证与输出边界复盘作业", DEMO_TEACHING_CLASS_ID, "class", "active", SEED_AT + timedelta(days=21)),
        ("browser-defense", "assignment", "WEBSEC-101-BROWSER-DEFENSE", "浏览器安全边界阶段作业", SHOWCASE_CLASS_B_ID, "class", "active", SEED_AT + timedelta(days=28)),
        ("upload-check", "assignment", "WEBSEC-101-UPLOAD-CHECK", "上传与出站控制验收作业", SHOWCASE_B_GROUP_A_ID, "group", "withdrawn", SEED_AT + timedelta(days=14)),
    )
    class_students = {
        DEMO_TEACHING_CLASS_ID: [student_id for student_id, (*_, class_id) in []],
    }
    enrollment_rows = (await session.execute(
        select(CourseEnrollment.student_id, CourseEnrollment.teaching_class_id).where(
            CourseEnrollment.course_id == COURSE_WEBSEC_ID, CourseEnrollment.status == "enrolled"
        )
    )).all()
    showcase_learner_ids = set(_showcase_learner_ids())
    grouped_students: dict[UUID, list[UUID]] = defaultdict(list)
    for student_id, class_id in enrollment_rows:
        if (
            student_id in showcase_learner_ids
            and class_id in {DEMO_TEACHING_CLASS_ID, SHOWCASE_CLASS_B_ID}
        ):
            grouped_students[class_id].append(student_id)
    for assignment_index, (key, kind, logical_key, title, target_id, target_type, assignment_status, due_at) in enumerate(assignments):
        assessment_id = _id("assessment", key)
        _, created = await _ensure(
            session, Assessment, assessment_id, course_id=COURSE_WEBSEC_ID, owner_teacher_id=DEMO_COURSE_TEACHER_ID,
            kind=kind, logical_key=logical_key, status="published" if assignment_status != "withdrawn" else "withdrawn",
        )
        counts["assessments"] += int(created)
        version_id = _id("assessment-version", key)
        _, created = await _ensure(
            session, AssessmentVersion, version_id, assessment_id=assessment_id, version_no=1, title=title,
            instructions="请结合课程证据解释防御选择；系统评分和 AI 建议均需教师复核。", state="published" if assignment_status != "withdrawn" else "withdrawn",
            created_by=DEMO_COURSE_TEACHER_ID, frozen_at=SEED_AT,
        )
        counts["assessment_versions"] += int(created)
        for position, quiz_id in enumerate(selected_ids, start=1):
            item, node = by_id[quiz_id]
            item_id = _id("assessment-item", f"{key}:{position}")
            _, created = await _ensure(
                session, AssessmentItem, item_id, assessment_version_id=version_id, quiz_item_id=quiz_id,
                position=position, points=10.0, grading_mode="subjective" if position in {3, 4} else "objective",
                question_snapshot=_question_snapshot(item, node),
            )
            counts["assessment_items"] += int(created)
        assignment_id = _id("assessment-assignment", key)
        kwargs = {"teaching_class_id": None, "group_id": None, "student_id": None}
        if target_type == "class":
            kwargs["teaching_class_id"] = target_id
        else:
            kwargs["group_id"] = target_id
            kwargs["teaching_class_id"] = SHOWCASE_CLASS_B_ID
        _, created = await _ensure(
            session, AssessmentAssignment, assignment_id, assessment_version_id=version_id, target_type=target_type,
            due_at=due_at, allow_late=True, status=assignment_status, assigned_by=DEMO_COURSE_TEACHER_ID,
            idempotency_key=f"{PROFILE}:{key}", **kwargs,
        )
        counts["assessment_assignments"] += int(created)
        if assignment_index > 1:
            continue
        student_ids = sorted(grouped_students[target_id], key=str)
        # Keep the default demo learner's assigned work open for the explicit
        # controlled draft. The same number of non-demo submissions remains,
        # so the class snapshot stays representative rather than being
        # replaced by a front-end-only demo state.
        submitted_student_ids = set(
            student_id
            for student_id in student_ids
            if student_id != DEMO_USER_ID
        )
        submitted_student_ids = set(sorted(submitted_student_ids, key=str)[:13])
        # Each class keeps both submitted and not-started states; at least 26
        # of the two class assignments remain real submissions.
        for student_index, student_id in enumerate(student_ids):
            submission_id = _id("assessment-submission", f"{key}:{student_id}")
            submitted = student_id in submitted_student_ids
            status = "submitted" if submitted else "open"
            answer_payload: dict[str, Any] = {}
            for position, quiz_id in enumerate(selected_ids, start=1):
                item, _ = by_id[quiz_id]
                correct = (student_index + position + assignment_index) % 5 != 0
                answer_payload[str(quiz_id)] = item.answer if correct else "需要复盘的回答"
            if student_id == DEMO_USER_ID:
                # The controlled answer set lives in its explicit draft event
                # until the student clicks submit. Do not pre-populate the
                # real open submission itself.
                answer_payload = {}
            _, created = await _ensure(
                session, AssessmentSubmission, submission_id, assignment_id=assignment_id, student_id=student_id,
                answers=answer_payload, submitted_at=SEED_AT + timedelta(days=assignment_index * 3, minutes=student_index) if submitted else None,
                status=status,
            )
            counts["assessment_submissions"] += int(created)
            grade_id = _id("grade", f"{key}:{student_id}")
            if not submitted:
                # A previous profile version could have created a grade before
                # this learner became the reusable controlled draft account.
                # Remove only that stable seed grade so open submission state
                # and published-grade visibility cannot contradict each other.
                existing_grade = await session.get(AssessmentGradeDecision, grade_id)
                if existing_grade is not None:
                    await session.delete(existing_grade)
                    await session.flush()
                continue
            score = round(54 + ((student_index * 7 + assignment_index * 3) % 39) + student_index / 100, 2)
            grade_state = "pending"
            final_score: float | None = None
            objective_score: float | None = round(score * 0.72, 2)
            ai_status = "not_requested"
            ai_score: float | None = None
            ai_run: UUID | None = None
            ai_evidence: UUID | None = None
            override_reason: str | None = None
            published_at: datetime | None = None
            withdrawn_at: datetime | None = None
            if student_index < 6:
                grade_state = "published"
                final_score = score
                override_reason = "教师复核客观题与说明后发布。"
                published_at = SEED_AT + timedelta(days=10, minutes=student_index)
            elif student_index < 10:
                grade_state = "teacher_reviewed"
                final_score = score
                override_reason = "教师覆盖 AI 建议并等待发布。"
                ai_status = "suggested"
                ai_score = round(score - 1.5, 2)
                ai_run, ai_evidence = pairs[2]
            elif student_index == 10:
                grade_state = "withdrawn"
                final_score = score
                override_reason = "教师发现案例引用需更正，已撤回成绩。"
                published_at = SEED_AT + timedelta(days=9)
                withdrawn_at = SEED_AT + timedelta(days=11)
            elif student_index == 11:
                grade_state = "auto_scored"
            else:
                grade_state = "pending"
            _, created = await _ensure(
                session, AssessmentGradeDecision, grade_id, submission_id=submission_id,
                objective_score=objective_score, ai_suggested_score=ai_score, ai_agent_run_id=ai_run,
                ai_evidence_snapshot_id=ai_evidence, ai_suggestion_status=ai_status, final_score=final_score,
                status=grade_state, graded_by=DEMO_COURSE_TEACHER_ID if grade_state != "pending" else None,
                override_reason=override_reason, published_at=published_at, withdrawn_at=withdrawn_at,
            )
            counts["grade_decisions"] += int(created)


async def _seed_demo_comprehensive_assessment(
    session: AsyncSession,
    quizzes: dict[str, UUID],
    counts: dict[str, int],
) -> None:
    """Freeze the 36 persistent, quality-passed WEBSEC items for the demo learner.

    This is a separate student-scoped assessment rather than a widened class
    assignment.  The normal student submission API therefore continues to
    enforce enrolment, assignment scope, published version, and frozen-item
    membership before the assessment workflow can begin.
    """

    selected_ids = _demo_comprehensive_quiz_ids(quizzes)
    if len(selected_ids) != 36 or len(set(selected_ids)) != 36:
        raise RuntimeError("showcase comprehensive assessment requires 36 unique quiz items")
    publishable = await QuizQualityService(session).list_publishable_items(
        course_id=COURSE_WEBSEC_ID
    )
    if not set(selected_ids).issubset({item.id for item in publishable.items}):
        raise RuntimeError(
            "showcase comprehensive assessment requires published quality-passed quiz items"
        )
    item_rows = (
        await session.execute(
            select(QuizItem, KnowledgeNode)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(QuizItem.id.in_(selected_ids))
        )
    ).all()
    by_id = {item.id: (item, node) for item, node in item_rows}
    if len(by_id) != len(selected_ids):
        raise RuntimeError("showcase comprehensive assessment quiz snapshots are not ready")

    key = SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY
    assessment_id = _id("assessment", key)
    _, created = await _ensure(
        session,
        Assessment,
        assessment_id,
        course_id=COURSE_WEBSEC_ID,
        owner_teacher_id=DEMO_COURSE_TEACHER_ID,
        kind="exam",
        logical_key="WEBSEC-101-DEMO-COMPREHENSIVE-36",
        status="published",
    )
    counts["assessments"] += int(created)
    version_id = _id("assessment-version", key)
    _, created = await _ensure(
        session,
        AssessmentVersion,
        version_id,
        assessment_id=assessment_id,
        version_no=1,
        title="WEBSEC-101 阶段综合评估（36 题）",
        instructions=(
            "本阶段评估覆盖 HTTP、认证、输入验证、SQL 注入防御、XSS、上传与 SSRF 等课程主线。"
            "请基于防御、修复和验证思路作答；提交后才会进入 Evidence、QualityCheck 和能力画像回写链路。"
        ),
        state="published",
        created_by=DEMO_COURSE_TEACHER_ID,
        frozen_at=SEED_AT,
    )
    counts["assessment_versions"] += int(created)
    for position, quiz_id in enumerate(selected_ids, start=1):
        item, node = by_id[quiz_id]
        _, created = await _ensure(
            session,
            AssessmentItem,
            _id("assessment-item", f"{key}:{position}"),
            assessment_version_id=version_id,
            quiz_item_id=quiz_id,
            position=position,
            points=5.0,
            grading_mode="subjective" if item.type in {"short_answer", "code"} else "objective",
            question_snapshot=_question_snapshot(item, node),
        )
        counts["assessment_items"] += int(created)
    assignment_id = _id("assessment-assignment", key)
    _, created = await _ensure(
        session,
        AssessmentAssignment,
        assignment_id,
        assessment_version_id=version_id,
        target_type="student",
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        group_id=None,
        student_id=DEMO_USER_ID,
        due_at=SEED_AT + timedelta(days=42),
        allow_late=True,
        status="active",
        assigned_by=DEMO_COURSE_TEACHER_ID,
        idempotency_key=f"{PROFILE}:{key}",
    )
    counts["assessment_assignments"] += int(created)
    _, created = await _ensure(
        session,
        AssessmentSubmission,
        _id("assessment-submission", f"{key}:{DEMO_USER_ID}"),
        assignment_id=assignment_id,
        student_id=DEMO_USER_ID,
        answers={},
        submitted_at=None,
        status="open",
    )
    counts["assessment_submissions"] += int(created)


async def _seed_demo_assessment_draft(session: AsyncSession, counts: dict[str, int]) -> None:
    """Persist one editable demo draft for the existing demo learner only.

    The draft intentionally references the same published, open assignment
    and current-student active quiz artifact that the normal student APIs and
    assessment workflow validate. It is not an answer-key fallback for other
    students and it contains no precomputed score or capability mutation.
    """

    assignment_id = _id("assessment-assignment", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY)
    assignment = await session.get(AssessmentAssignment, assignment_id)
    if assignment is None or assignment.status != "active":
        raise RuntimeError("showcase demo assessment assignment is not active")
    submission = await session.get(
        AssessmentSubmission,
        _id("assessment-submission", f"{SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY}:{DEMO_USER_ID}"),
    )
    if submission is None or submission.status != "open" or submission.answers:
        raise RuntimeError("showcase demo assessment draft requires an empty open submission")
    items = list(
        (
            await session.execute(
                select(AssessmentItem, QuizItem)
                .join(QuizItem, QuizItem.id == AssessmentItem.quiz_item_id)
                .where(AssessmentItem.assessment_version_id == assignment.assessment_version_id)
                .order_by(AssessmentItem.position)
            )
        ).all()
    )
    if len(items) != 36:
        raise RuntimeError("showcase demo assessment draft requires 36 frozen questions")
    answers: dict[str, str | list[str]] = {}
    for assessment_item, quiz_item in items:
        raw_answer = str(quiz_item.answer or "").strip()
        if not raw_answer:
            raise RuntimeError("showcase demo assessment draft encountered a question without an answer")
        answers[str(assessment_item.quiz_item_id)] = (
            [part.strip() for part in raw_answer.split(";") if part.strip()]
            if quiz_item.type == "multi_choice"
            else raw_answer
        )
    if len(answers) != len(items):
        raise RuntimeError("showcase demo assessment draft has duplicate question references")

    resource_id = _id("resource", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY)
    resource_content = {
        "source_type": "curated-demo",
        "artifact_kind": "受控演示测验工件",
        "assessment_logical_key": "WEBSEC-101-DEMO-COMPREHENSIVE-36",
        "assessment_version_id": str(assignment.assessment_version_id),
        "question_count": len(items),
        "question_types": sorted({quiz_item.type for _, quiz_item in items}),
        "difficulty_layers": ["基础边界识别", "防御选择说明", "修复验证与复盘"],
        "knowledge_points": ["HTTP 与会话", "输入验证", "SQL 注入防御", "浏览器输出", "上传与出站控制"],
        "explanation_boundary": "该工件仅为受控课程演示提供可验证的评估来源；分数、能力变化和路径更新不在预置内容中计算。",
        "source_boundary": "受控预置演示测验工件，已持久化到当前 demo 学生的课程资源记录；不是实时模型生成。",
    }
    _, created = await _ensure(
        session,
        GeneratedResource,
        resource_id,
        user_id=DEMO_USER_ID,
        course_id=COURSE_WEBSEC_ID,
        kp_id=node_id("sql-injection"),
        agent_run_id=None,
        workflow_run_id=None,
        step_attempt_id=None,
        parent_resource_id=None,
        lineage_root_id=resource_id,
        version=1,
        resource_type="quiz",
        title="WEBSEC-101 受控演示阶段综合评估工件（36 题）",
        content=resource_content,
        object_key=None,
        evidence_chunk_ids=_evidence_ids(session, chunk_id("sql-injection", 1)),
        quality_score=0.9,
        status="active",
        metadata_={
            "seed_profile": PROFILE,
            "source_kind": "curated-demo",
            "logical_key": SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY,
            "quality_state": "controlled_demo_ready",
            "not_live_generated": True,
        },
    )
    counts["resources"] += int(created)
    _, created = await _ensure(
        session,
        ResourceVersion,
        _id("resource-version", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY),
        resource_id=resource_id,
        version=1,
        content=resource_content,
        object_key=None,
        change_summary="为受控 demo 学生提供 36 道冻结题目的可编辑阶段综合评估草稿来源。",
        metadata_={
            "seed_profile": PROFILE,
            "source_kind": "curated-demo",
            "logical_key": SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY,
        },
    )
    counts["resource_versions"] += int(created)
    _, created = await _ensure(
        session,
        LearningEvent,
        _id("learning-event", SHOWCASE_DEMO_ASSESSMENT_EVENT_KEY),
        user_id=DEMO_USER_ID,
        event_type="assessment_demo_draft",
        kp_id=node_id("sql-injection"),
        resource_id=resource_id,
        result={
            "seed_profile": PROFILE,
            "source_kind": "curated-demo",
            "assessment_profile": "websec_comprehensive_36",
            "assignment_id": str(assignment_id),
            "quiz_resource_id": str(resource_id),
            "answers": answers,
            "source_boundary": "受控预置的 36 道题演示作答仅会填入当前页面的可编辑草稿；须由学生显式提交，分数、能力和路径不会被预先写入。",
        },
        occurred_at=SEED_AT + timedelta(hours=2),
    )
    counts["demo_assessment_drafts"] += int(created)


async def _seed_collaboration(session: AsyncSession, pairs: list[tuple[UUID, UUID]], counts: dict[str, int]) -> None:
    source_documents = [document_id("ssrf"), document_id("secure-coding")]
    signal_ids: list[UUID] = []
    for index, (key, title, slug) in enumerate((
        ("ssrf", "SSRF 出站控制复盘信号", "ssrf"),
        ("secure-coding", "安全修复验证清单更新信号", "secure-coding"),
    )):
        run_id, evidence_id = pairs[4 if index == 0 else 3]
        signal_id = _id("external-signal", key)
        _, created = await _ensure(
            session, ExternalSignal, signal_id, source_document_id=source_documents[index], agent_run_id=run_id,
            evidence_snapshot_id=evidence_id, created_by=DEMO_COURSE_TEACHER_ID, kind="hot",
            title=title, source_fingerprint=sha256(f"{PROFILE}:signal:{key}".encode()).hexdigest(),
            status="validated", ingested_at=SEED_AT + timedelta(hours=index),
        )
        counts["external_signals"] += int(created)
        signal_ids.append(signal_id)
    for index, (key, title, node_slug, state) in enumerate((
        ("ssrf-emphasis", "在近期复盘中强调 SSRF 出站控制", "ssrf", "adopted"),
        ("secure-coding-checklist", "补充安全修复验证清单课程更新候选", "secure-coding", "pending_teacher_decision"),
    )):
        suggestion_id = _id("course-update", key)
        _, created = await _ensure(
            session, CourseUpdateSuggestion, suggestion_id, course_id=COURSE_WEBSEC_ID, signal_id=signal_ids[index],
            agent_run_id=pairs[4 if index == 0 else 3][0], evidence_snapshot_id=pairs[4 if index == 0 else 3][1],
            created_by=DEMO_COURSE_TEACHER_ID, version_no=1,
            title=title,
            diff={"summary": "面向指定教学班的可编辑课程更新草稿。", "target_knowledge_point": node_slug, "student_next_step": "阅读关联资料并完成复盘练习。", "source_boundary": "预置课程建议，非实时模型输出。"},
            status=state,
        )
        counts["course_update_suggestions"] += int(created)
        impact_id = _id("course-update-impact", key)
        _, created = await _ensure(
            session, CourseUpdateImpact, impact_id, suggestion_id=suggestion_id, knowledge_node_id=node_id(node_slug),
            impact_type="emphasize", rationale="近期有效作答与课程 Evidence 均表明该主题需要以防御性案例复盘。",
        )
        counts["course_update_impacts"] += int(created)
        if state == "adopted":
            decision_id = _id("course-update-decision", key)
            _, created = await _ensure(
                session, CourseUpdateDecision, decision_id, suggestion_id=suggestion_id, teacher_id=DEMO_COURSE_TEACHER_ID,
                decision="adopt", reason="教师确认创建待审核教学动作，不自动改写已发布课程。", decided_at=SEED_AT + timedelta(days=1),
            )
            counts["course_update_decisions"] += int(created)
    for index, (key, class_id, subject, body) in enumerate((
        ("input-review", DEMO_TEACHING_CLASS_ID, "输入验证复盘安排", "本周先完成参数化查询与排序白名单学习单，再提交阶段练习。请在资源详情查看来源和检查点。"),
        ("xss-review", SHOWCASE_CLASS_B_ID, "浏览器输出边界复盘安排", "请先回看同源策略与输出上下文，再完成 XSS 防御课件中的检查点。课程内容为预置整理，Evidence 可在详情查看。"),
    )):
        message_id = _id("notice", key)
        _, created = await _ensure(
            session, Message, message_id, sender_user_id=DEMO_COURSE_TEACHER_ID, course_id=COURSE_WEBSEC_ID,
            teaching_class_id=class_id, target_user_id=None, scope_type="class", subject=subject, body=body,
            safety_state="accepted", status="sent", idempotency_key=f"{PROFILE}:notice:{key}",
            payload_fingerprint=sha256(f"{subject}:{body}".encode()).hexdigest(), sent_at=SEED_AT + timedelta(days=index),
            recall_deadline_at=SEED_AT + timedelta(days=index, minutes=30), recalled_at=None, recalled_by=None, recall_reason=None,
        )
        counts["notices"] += int(created)
        target_students = _showcase_learner_ids_for_class(class_id)
        for student_id in target_students:
            delivery_id = _id("notice-delivery", f"{key}:{student_id}")
            _, created = await _ensure(
                session, MessageDelivery, delivery_id, message_id=message_id, recipient_user_id=student_id,
                delivery_state="read" if int(str(student_id.int)[-1]) % 3 == 0 else "unread",
                delivered_at=SEED_AT + timedelta(days=index), read_at=SEED_AT + timedelta(days=index, hours=2) if int(str(student_id.int)[-1]) % 3 == 0 else None,
                recalled_at=None,
            )
            counts["notice_deliveries"] += int(created)


async def _write_manifest(session: AsyncSession, counts: dict[str, int]) -> None:
    summary = {
        "profile": PROFILE,
        "manifest_version": MANIFEST_VERSION,
        "course_code": "WEBSEC-101",
        "source_boundary": "受控预置课程场景；内容通过真实数据库/API 消费，不是实时模型生成或真实在校学生数据。",
        "learning_stories": ["accelerated", "steady", "input_validation", "xss_prerequisite", "recovery"],
        "learners": {
            "fictional_alias_count": len(SHOWCASE_STUDENTS),
            "demo_course_learner": {
                "account": DEMO_USER_EMAIL,
                "display_name": SHOWCASE_DEMO_STUDENT_DISPLAY_NAME,
                "story": SHOWCASE_DEMO_STUDENT_STORY,
                "boundary": "复用现有本地 demo 登录；不是新增账户、真实在校学生或实时生成画像。",
                "assessment_demo_draft": {
                    "assignment": "WEBSEC-101-DEMO-COMPREHENSIVE-36",
                    "question_count": 36,
                    "resource_key": SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY,
                    "boundary": "仅填入可编辑草稿，需学生显式提交；不预置分数、能力变化或成功工作流。",
                },
            },
        },
        "resource_types": sorted({item["type"] for item in _resource_definitions()}),
        "preprocessed_lecture": {
            "title": "WEBSEC-101 Web 安全防御基础讲义",
            "document_id": str(SHOWCASE_LECTURE_DOCUMENT_ID),
            "asset_type": "markdown_full",
            "object_key": SHOWCASE_LECTURE_OBJECT_KEY,
            "processing_boundary": "已持久化的受控预置处理结果；页面不会声称刚刚完成实时 PDF 解析或向量化。",
        },
        "counts": counts,
    }
    _, created = await _ensure(
        session, GovernanceAuditEvent, MANIFEST_ID, actor_user_id=DEMO_COURSE_TEACHER_ID,
        action="showcase_course.seed_manifest", object_type="showcase_seed_manifest", object_id=COURSE_WEBSEC_ID,
        reason="显式受控 WEBSEC-101 课程场景 seed；可验证、可清理且不在生产启动路径运行。",
        result_status="seeded", request_id=f"{PROFILE}:{MANIFEST_VERSION}", metadata_=summary, created_at=SEED_AT,
    )
    counts["manifest_created"] = int(created)


async def _seed(session: AsyncSession) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    await _seed_prerequisites(session)
    await _seed_showcase_lecture(session, counts)
    groups = await _seed_class_and_groups(session, counts)
    students = await _seed_students(session, groups, counts)
    quizzes = await _seed_showcase_quizzes(session, counts)
    pairs = await _seed_runs_and_evidence(session, counts)
    resources = await _seed_resources(session, counts)
    await _seed_learning_data(session, students, quizzes, resources, counts)
    await _seed_learning_loop(session, students, resources, counts)
    await _seed_snapshots_and_recommendations(session, pairs, counts)
    await _seed_assets_and_syllabus(session, pairs, counts)
    await _seed_assessments(session, quizzes, pairs, counts)
    await _seed_demo_comprehensive_assessment(session, quizzes, counts)
    await _seed_demo_assessment_draft(session, counts)
    await _seed_collaboration(session, pairs, counts)
    await _write_manifest(session, counts)
    verification = await _verify(session)
    if not verification["valid"]:
        raise RuntimeError("showcase_course seed verification failed: " + "; ".join(verification["errors"]))
    return {"profile": PROFILE, "manifest_version": MANIFEST_VERSION, "created": dict(counts), "verification": verification}


async def _verify(session: AsyncSession) -> dict[str, Any]:
    errors: list[str] = []
    student_ids = _profile_user_ids()
    showcase_learner_ids = _showcase_learner_ids()
    students = await session.scalar(select(User.id).where(User.id.in_(student_ids)).limit(1))
    student_count = await session.scalar(select(User).where(User.id.in_(student_ids)).count()) if False else None
    del students, student_count
    user_rows = list((await session.execute(select(User.id).where(User.id.in_(student_ids)))).scalars())
    enrollment_rows = list((await session.execute(select(CourseEnrollment).where(CourseEnrollment.student_id.in_(student_ids), CourseEnrollment.status == "enrolled"))).scalars())
    group_rows = list((await session.execute(select(StudentGroupMember).where(StudentGroupMember.student_id.in_(student_ids), StudentGroupMember.status == "active"))).scalars())
    classes = list((await session.execute(select(TeachingClass).where(TeachingClass.id.in_((DEMO_TEACHING_CLASS_ID, SHOWCASE_CLASS_B_ID))))).scalars())
    group_count = await session.scalar(select(StudentGroup.id).where(StudentGroup.id.in_((DEMO_STUDENT_GROUP_ID, SHOWCASE_A_GROUP_B_ID, SHOWCASE_B_GROUP_A_ID, SHOWCASE_B_GROUP_B_ID))))
    del group_count
    demo_user = await session.get(User, DEMO_USER_ID)
    demo_enrollment = await session.get(CourseEnrollment, DEMO_ENROLLMENT_ID)
    demo_member = await session.get(StudentGroupMember, DEMO_GROUP_MEMBER_ID)
    publishable = await QuizQualityService(session).list_publishable_items(course_id=COURSE_WEBSEC_ID)
    attempt_rows = list((await session.execute(select(QuizAttempt).where(QuizAttempt.user_id.in_(showcase_learner_ids), QuizAttempt.score.is_not(None)))).scalars())
    scored_students = {row.user_id for row in attempt_rows}
    pair_rows = (await session.execute(
        select(AgentRun.id, WorkflowEvidenceSnapshot.id)
        .join(WorkflowEvidenceSnapshot, WorkflowEvidenceSnapshot.agent_run_id == AgentRun.id)
        .where(AgentRun.workflow_name == "websec_showcase_seed", AgentRun.status == "succeeded", WorkflowEvidenceSnapshot.content_digest != "")
    )).all()
    resource_ids = [
        *[_id("resource", str(item["key"])) for item in _resource_definitions()],
        _id("resource", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY),
    ]
    resource_rows = list(
        (
            await session.execute(
                select(GeneratedResource).where(GeneratedResource.id.in_(resource_ids))
            )
        ).scalars()
    )
    path_version_rows = list(
        (
            await session.execute(
                select(LearningPathVersion).where(
                    LearningPathVersion.user_id.in_(showcase_learner_ids),
                    LearningPathVersion.course_id == COURSE_WEBSEC_ID,
                )
            )
        ).scalars()
    )
    path_candidate_rows = list(
        (
            await session.execute(
                select(LearningPathReplanCandidate).where(
                    LearningPathReplanCandidate.student_id.in_(student_ids),
                    LearningPathReplanCandidate.course_id == COURSE_WEBSEC_ID,
                )
            )
        ).scalars()
    )
    course_resource_recommendation_rows = list(
        (
            await session.execute(
                select(CourseResourceRecommendation).where(
                    CourseResourceRecommendation.student_id.in_(showcase_learner_ids),
                    CourseResourceRecommendation.course_id == COURSE_WEBSEC_ID,
                )
            )
        ).scalars()
    )
    demo_recommendation = await session.get(
        CourseResourceRecommendation,
        _id("course-resource-recommendation", "demo-student:input-validation-baseline"),
    )
    demo_assessment_submission = await session.get(
        AssessmentSubmission,
        _id(
            "assessment-submission",
            f"{SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY}:{DEMO_USER_ID}",
        ),
    )
    demo_assessment_assignment = await session.get(
        AssessmentAssignment,
        _id("assessment-assignment", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY),
    )
    demo_assessment = await session.get(
        Assessment,
        _id("assessment", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY),
    )
    demo_assessment_version = await session.get(
        AssessmentVersion,
        _id("assessment-version", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY),
    )
    demo_assessment_items = list(
        (
            await session.execute(
                select(AssessmentItem).where(
                    AssessmentItem.assessment_version_id
                    == _id("assessment-version", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY)
                ).order_by(AssessmentItem.position)
            )
        ).scalars()
    )
    demo_capability_dimensions = set(
        (
            await session.execute(
                select(UserCapability.dimension).where(UserCapability.user_id == DEMO_USER_ID)
            )
        ).scalars()
    )
    demo_assessment_draft_event = await session.get(
        LearningEvent,
        _id("learning-event", SHOWCASE_DEMO_ASSESSMENT_EVENT_KEY),
    )
    resource_types = {row.resource_type for row in resource_rows}
    lineage_rows = [row for row in resource_rows if row.parent_resource_id and row.lineage_root_id and row.version > 1]
    resource_by_id = {row.id: row for row in resource_rows}
    doc_resource = resource_by_id.get(_id("resource", "input-validation-guide-v2"))
    ppt_resource = resource_by_id.get(_id("resource", "xss-defense-slides-v2"))
    mindmap_resource = resource_by_id.get(_id("resource", "websec-map-v2"))
    lab_resource = resource_by_id.get(_id("resource", "upload-lab"))
    reading_resource = resource_by_id.get(_id("resource", "ssrf-reading"))
    video_resource = resource_by_id.get(_id("resource", "websec-video-script"))
    demo_assessment_resource = resource_by_id.get(
        _id("resource", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY)
    )
    tutor_event_count = await session.scalar(
        select(func.count(LearningEvent.id)).where(
            LearningEvent.user_id.in_(showcase_learner_ids), LearningEvent.event_type == "tutor_curated_exchange"
        )
    )
    assignment_rows = list((await session.execute(select(AssessmentAssignment).where(AssessmentAssignment.id.in_([_id("assessment-assignment", key) for key in ("input-review", "browser-defense", "upload-check", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY)])))).scalars())
    submission_rows = list((await session.execute(select(AssessmentSubmission).where(AssessmentSubmission.id.in_([_id("assessment-submission", f"{key}:{student_id}") for key in ("input-review", "browser-defense") for student_id in showcase_learner_ids])))).scalars())
    grade_rows = list((await session.execute(select(AssessmentGradeDecision).where(AssessmentGradeDecision.id.in_([_id("grade", f"{key}:{student_id}") for key in ("input-review", "browser-defense") for student_id in showcase_learner_ids])))).scalars())
    snapshot_rows = list((await session.execute(select(ClassWeaknessSnapshot).where(ClassWeaknessSnapshot.id.in_([_id("weakness-snapshot", f"{class_key}:{window}") for class_key in ("a", "b") for window in ("baseline", "recent")])))).scalars())
    recommendation_rows = list((await session.execute(select(TeachingRecommendation).where(TeachingRecommendation.id.in_([_id("recommendation", key) for key in ("input", "xss")])))).scalars())
    syllabus_rows = list((await session.execute(select(CourseSyllabusVersion).where(CourseSyllabusVersion.id.in_([_id("syllabus-version", "v1"), _id("syllabus-version", "v2")])))).scalars())
    notice_rows = list((await session.execute(select(Message).where(Message.id.in_([_id("notice", key) for key in ("input-review", "xss-review")])))).scalars())
    update_rows = list((await session.execute(select(CourseUpdateSuggestion).where(CourseUpdateSuggestion.id.in_([_id("course-update", key) for key in ("ssrf-emphasis", "secure-coding-checklist")])))).scalars())
    asset_rows = list((await session.execute(select(CourseAssetGovernance).where(CourseAssetGovernance.id.in_([_id("asset-governance", key) for key in ("sql-guide", "xss-guide", "defensive-foundations-lecture")])))).scalars())
    lecture_document = await session.get(Document, SHOWCASE_LECTURE_DOCUMENT_ID)
    lecture_asset = await session.get(DocumentAsset, SHOWCASE_LECTURE_ASSET_ID)
    lecture_chunks = list((await session.execute(select(Chunk).where(Chunk.document_id == SHOWCASE_LECTURE_DOCUMENT_ID))).scalars())
    if len(user_rows) < 32: errors.append("虚构学生不足 32 名")
    if len(classes) != 2: errors.append("教学班不足 2 个")
    if len(enrollment_rows) < 32 or len(group_rows) < 32: errors.append("选课或分组关系不完整")
    if (
        demo_user is None
        or demo_user.email != DEMO_USER_EMAIL
        or demo_user.role != "student"
        or demo_user.display_name != SHOWCASE_DEMO_STUDENT_DISPLAY_NAME
    ):
        errors.append("默认 demo 学生未被受控课程场景正确复用")
    if (
        demo_enrollment is None
        or demo_enrollment.course_id != COURSE_WEBSEC_ID
        or demo_enrollment.student_id != DEMO_USER_ID
        or demo_enrollment.teaching_class_id != DEMO_TEACHING_CLASS_ID
        or demo_enrollment.status != "enrolled"
        or demo_member is None
        or demo_member.student_id != DEMO_USER_ID
        or demo_member.group_id != DEMO_STUDENT_GROUP_ID
        or demo_member.status != "active"
    ):
        errors.append("默认 demo 学生缺少有效的 WEBSEC-101 班级或分组关系")
    if len(publishable.items) < 36 or len({item.type for item in publishable.items}) < 4: errors.append("已发布质量通过题目不足 36 道或题型不足 4 类")
    if len(scored_students) < 24: errors.append("有可评分真实作答的学生不足 24 名")
    if len(pair_rows) < 6: errors.append("成功且关联的 AgentRun/Evidence 不足 6 对")
    if len(path_version_rows) < len(showcase_learner_ids): errors.append("学生路径基线版本不足，无法回看或重规划")
    if not any(row.status == "pending" and row.trigger_event_id is not None for row in path_candidate_rows): errors.append("缺少由持久化学习事件触发的可操作重规划候选")
    if not course_resource_recommendation_rows: errors.append("缺少可由学生处置的资源推荐投影")
    if (
        demo_recommendation is None
        or demo_recommendation.student_id != DEMO_USER_ID
        or demo_recommendation.course_id != COURSE_WEBSEC_ID
        or demo_recommendation.status != "scheduled"
    ):
        errors.append("默认 demo 学生缺少可追溯的课程资源推荐")
    if (
        demo_assessment_submission is None
        or demo_assessment_submission.status != "open"
        or bool(demo_assessment_submission.answers)
        or demo_assessment is None
        or demo_assessment.kind != "exam"
        or demo_assessment.status != "published"
        or demo_assessment.logical_key != "WEBSEC-101-DEMO-COMPREHENSIVE-36"
        or demo_assessment_version is None
        or demo_assessment_version.state != "published"
        or demo_assessment_assignment is None
        or demo_assessment_assignment.target_type != "student"
        or demo_assessment_assignment.student_id != DEMO_USER_ID
        or len(demo_assessment_items) != 36
        or [item.quiz_item_id for item in demo_assessment_items]
        != [
            *[UUID(str(item["id"])) for item in WEBSEC_QUIZ_ITEMS],
            *[_quiz_id(str(item["key"])) for item in SHOWCASE_QUIZZES],
        ]
        or "web_security" not in demo_capability_dimensions
        or demo_assessment_resource is None
        or demo_assessment_resource.user_id != DEMO_USER_ID
        or demo_assessment_resource.status != "active"
        or not demo_assessment_resource.evidence_chunk_ids
        or demo_assessment_resource.content.get("question_count") != 36
    ):
        errors.append("默认 demo 学生缺少 36 道冻结题目的可提交综合评估或能力回写基线")
    draft_result = dict(demo_assessment_draft_event.result or {}) if demo_assessment_draft_event else {}
    if (
        demo_assessment_draft_event is None
        or demo_assessment_draft_event.user_id != DEMO_USER_ID
        or draft_result.get("source_kind") != "curated-demo"
        or draft_result.get("assessment_profile") != "websec_comprehensive_36"
        or draft_result.get("assignment_id")
        != str(_id("assessment-assignment", SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY))
        or draft_result.get("quiz_resource_id") != str(_id("resource", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY))
        or len(draft_result.get("answers") or {}) != 36
    ):
        errors.append("默认 demo 学生缺少 36 道题的受控演示作答草稿")
    if resource_types != {"doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"}: errors.append("七类资源未齐全")
    if len(lineage_rows) < 3: errors.append("资源谱系版本不足 3 条")
    if doc_resource is None or not 900 <= len(str(doc_resource.content.get("body") or "")) <= 1600: errors.append("课程讲解文档未满足 900–1600 字教学质量要求")
    if ppt_resource is None or not 10 <= len(ppt_resource.content.get("slides") or []) <= 14: errors.append("课程 PPT 未满足 10–14 页结构化预览要求")
    if mindmap_resource is None or mindmap_resource.content.get("depth") != 3 or len(mindmap_resource.content.get("nodes") or []) < 20: errors.append("课程思维导图未满足三层二十节点要求")
    if lab_resource is None or not {"prerequisites", "task", "deliverables", "acceptance", "common_mistakes", "result_example", "defensive_review"}.issubset(lab_resource.content): errors.append("课程实操缺少前提、验收或防御复盘")
    if reading_resource is None or not {"reading_goal", "summary", "keywords", "estimated_minutes", "source_url", "related_exercise"}.issubset(reading_resource.content): errors.append("课程阅读导引缺少来源或练习")
    if video_resource is None or video_resource.content.get("artifact_kind") != "讲解脚本/分镜" or video_resource.content.get("is_playable_video") is not False: errors.append("讲解脚本被错误标记为可播放视频")
    if int(tutor_event_count or 0) < len(showcase_learner_ids) * len(SHOWCASE_TUTOR_EXCHANGES): errors.append("可恢复辅导记录不足，无法提供证据不足边界")
    if len(assignment_rows) < 4 or len([row for row in submission_rows if row.status in {"submitted", "late"}]) < 24: errors.append("作业或真实提交数量不足")
    if not {"open", "submitted"}.issubset({row.status for row in submission_rows}): errors.append("未开始和已提交状态未同时覆盖")
    if not {"pending", "published", "teacher_reviewed", "withdrawn"}.issubset({row.status for row in grade_rows}): errors.append("评分状态未覆盖待批、发布、教师覆盖和撤回")
    if len(snapshot_rows) < 4 or len(recommendation_rows) < 2: errors.append("两个时间窗快照或教学建议不足")
    if len(syllabus_rows) < 2 or len(notice_rows) < 2 or len(update_rows) < 2 or len(asset_rows) < 2: errors.append("教师治理对象数量不足")
    if lecture_document is None or lecture_document.status != "ready": errors.append("受控预置讲义未持久化为可用知识文档")
    if lecture_asset is None or lecture_asset.object_key != SHOWCASE_LECTURE_OBJECT_KEY: errors.append("受控预置讲义缺少可追溯源资产")
    if len(lecture_chunks) != len(_LECTURE_SECTION_KNOWLEDGE): errors.append("受控预置讲义的教学分块数量不完整")
    if any(not row.metadata_.get("kp_ids") or not row.metadata_.get("chapter") for row in lecture_chunks): errors.append("受控预置讲义块缺少知识点或来源定位")
    for learner_id, label in ((DEMO_USER_ID, "默认 demo 学生"), (_student_id("qinglan"), "既有花名学生")):
        learner = await session.get(User, learner_id)
        if learner is None:
            errors.append(f"{label}不存在，无法验证学生体验投影")
            continue
        try:
            experience = await StudentCourseExperienceService(session).get_experience(
                actor=learner,
                course_id=COURSE_WEBSEC_ID,
            )
        except Exception as exc:  # Verification must report a missing projection as invalid.
            errors.append(f"{label}学生体验投影读取失败：{exc}")
            continue
        if not experience.tasks:
            errors.append(f"{label}缺少 active LearningPath 或 LearningTask")
        if not experience.tutor_exchanges:
            errors.append(f"{label}缺少可恢复的课程辅导记录")
        if experience.assessment.scored_attempt_count <= 0:
            errors.append(f"{label}缺少可评分的课程作答")
        if learner_id == DEMO_USER_ID and experience.assessment_demo_draft is None:
            errors.append("默认 demo 学生体验未投影受控演示作答草稿")
        if experience.data_status != "ready":
            errors.append(f"{label}学生体验仍为 {experience.data_status}：{', '.join(experience.missing_dependencies)}")
    return {
        "profile": PROFILE, "manifest_version": MANIFEST_VERSION, "valid": not errors, "errors": errors,
        "counts": {"students": len(user_rows), "demo_course_learners": int(demo_user is not None), "scenario_learners": len(showcase_learner_ids), "classes": len(classes), "enrollments": len(enrollment_rows), "groups": 4, "publishable_questions": len(publishable.items), "scored_students": len(scored_students), "agent_evidence_pairs": len(pair_rows), "resources": len(resource_rows), "lineage_versions": len(lineage_rows), "path_versions": len(path_version_rows), "path_candidates": len(path_candidate_rows), "resource_recommendations": len(course_resource_recommendation_rows), "assignments": len(assignment_rows), "submitted_or_late": len([row for row in submission_rows if row.status in {"submitted", "late"}]), "demo_assessment_questions": len(demo_assessment_items), "demo_assessment_drafts": int(demo_assessment_draft_event is not None), "snapshots": len(snapshot_rows), "recommendations": len(recommendation_rows), "syllabus_versions": len(syllabus_rows), "notices": len(notice_rows), "course_updates": len(update_rows), "assets": len(asset_rows), "lecture_chunks": len(lecture_chunks)},
    }


async def _delete_by_ids(session: AsyncSession, model: type[Any], ids: Iterable[UUID]) -> int:
    values = list(ids)
    if not values:
        return 0
    result = await session.execute(delete(model).where(model.id.in_(values)))
    return int(result.rowcount or 0)


async def _reset(session: AsyncSession) -> dict[str, int]:
    """Remove only stable rows belonging to this profile, in FK-safe order."""

    student_ids = _profile_user_ids()
    showcase_learner_ids = _showcase_learner_ids()
    standard_assessment_keys = ("input-review", "browser-defense", "upload-check")
    assessment_keys = (*standard_assessment_keys, SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY)
    assessment_ids = [_id("assessment", key) for key in assessment_keys]
    version_ids = [_id("assessment-version", key) for key in assessment_keys]
    assignment_ids = [_id("assessment-assignment", key) for key in assessment_keys]
    submission_ids = [
        *[
            _id("assessment-submission", f"{key}:{student_id}")
            for key in standard_assessment_keys[:2]
            for student_id in showcase_learner_ids
        ],
        _id(
            "assessment-submission",
            f"{SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY}:{DEMO_USER_ID}",
        ),
    ]
    grade_ids = [
        _id("grade", f"{key}:{student_id}")
        for key in standard_assessment_keys[:2]
        for student_id in showcase_learner_ids
    ]
    resource_ids = [
        *[_id("resource", str(item["key"])) for item in _resource_definitions()],
        _id("resource", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY),
    ]
    resource_version_ids = [
        *[_id("resource-version", str(item["key"])) for item in _resource_definitions()],
        _id("resource-version", SHOWCASE_DEMO_ASSESSMENT_RESOURCE_KEY),
    ]
    recommendation_ids = [_id("recommendation", key) for key in ("input", "xss")]
    snapshot_ids = [_id("weakness-snapshot", f"{class_key}:{window}") for class_key in ("a", "b") for window in ("baseline", "recent")]
    signal_ids = [_id("external-signal", key) for key in ("ssrf", "secure-coding")]
    update_ids = [_id("course-update", key) for key in ("ssrf-emphasis", "secure-coding-checklist")]
    notice_ids = [_id("notice", key) for key in ("input-review", "xss-review")]
    run_ids = [_id("agent-run", key) for key in ("teaching-insight", "syllabus-candidate", "subjective-grade", "resource-curation", "course-update", "student-tutoring")]
    workflow_ids = [_id("workflow-run", key) for key in ("teaching-insight", "syllabus-candidate", "subjective-grade", "resource-curation", "course-update", "student-tutoring")]
    evidence_ids = [_id("evidence", key) for key in ("teaching-insight", "syllabus-candidate", "subjective-grade", "resource-curation", "course-update", "student-tutoring")]
    counts: dict[str, int] = defaultdict(int)
    result = await session.execute(
        delete(ResourceFeedback).where(
            ResourceFeedback.student_id.in_(showcase_learner_ids),
            ResourceFeedback.course_id == COURSE_WEBSEC_ID,
        )
    )
    counts["resource_feedback"] += int(result.rowcount or 0)
    result = await session.execute(
        delete(CourseResourceRecommendation).where(
            CourseResourceRecommendation.student_id.in_(student_ids),
            CourseResourceRecommendation.course_id == COURSE_WEBSEC_ID,
        )
    )
    counts["course_resource_recommendations"] += int(result.rowcount or 0)
    counts["course_resource_recommendations"] += await _delete_by_ids(
        session,
        CourseResourceRecommendation,
        [_id("course-resource-recommendation", "demo-student:input-validation-baseline")],
    )
    result = await session.execute(
        delete(LearningPathDecision).where(LearningPathDecision.student_id.in_(student_ids))
    )
    counts["learning_path_decisions"] += int(result.rowcount or 0)
    result = await session.execute(
        delete(LearningPathReplanCandidate).where(
            LearningPathReplanCandidate.student_id.in_(student_ids),
            LearningPathReplanCandidate.course_id == COURSE_WEBSEC_ID,
        )
    )
    counts["learning_path_candidates"] += int(result.rowcount or 0)
    result = await session.execute(
        delete(LearningPathVersion).where(
            LearningPathVersion.user_id.in_(student_ids),
            LearningPathVersion.course_id == COURSE_WEBSEC_ID,
        )
    )
    counts["learning_path_versions"] += int(result.rowcount or 0)
    counts["learning_path_versions"] += await _delete_by_ids(
        session,
        LearningPathVersion,
        [_id("learning-path-version", str(DEMO_USER_ID))],
    )
    counts["notice_deliveries"] += await _delete_by_ids(session, MessageDelivery, [_id("notice-delivery", f"{key}:{student_id}") for key in ("input-review", "xss-review") for student_id in showcase_learner_ids])
    counts["notices"] += await _delete_by_ids(session, Message, notice_ids)
    counts["course_update_decisions"] += await _delete_by_ids(session, CourseUpdateDecision, [_id("course-update-decision", "ssrf-emphasis")])
    counts["course_update_impacts"] += await _delete_by_ids(session, CourseUpdateImpact, [_id("course-update-impact", key) for key in ("ssrf-emphasis", "secure-coding-checklist")])
    counts["course_updates"] += await _delete_by_ids(session, CourseUpdateSuggestion, update_ids)
    counts["external_signals"] += await _delete_by_ids(session, ExternalSignal, signal_ids)
    counts["recommendation_decisions"] += await _delete_by_ids(session, TeachingRecommendationDecision, [_id("recommendation-decision", "input")])
    counts["recommendations"] += await _delete_by_ids(session, TeachingRecommendation, recommendation_ids)
    counts["grades"] += await _delete_by_ids(session, AssessmentGradeDecision, grade_ids)
    counts["submissions"] += await _delete_by_ids(session, AssessmentSubmission, submission_ids)
    counts["assignments"] += await _delete_by_ids(session, AssessmentAssignment, assignment_ids)
    counts["assessment_items"] += await _delete_by_ids(
        session,
        AssessmentItem,
        [
            *[
                _id("assessment-item", f"{key}:{position}")
                for key in standard_assessment_keys
                for position in range(1, 9)
            ],
            *[
                _id(
                    "assessment-item",
                    f"{SHOWCASE_DEMO_COMPREHENSIVE_ASSESSMENT_KEY}:{position}",
                )
                for position in range(1, 37)
            ],
        ],
    )
    counts["assessment_versions"] += await _delete_by_ids(session, AssessmentVersion, version_ids)
    counts["assessments"] += await _delete_by_ids(session, Assessment, assessment_ids)
    counts["syllabus_reviews"] += await _delete_by_ids(session, SyllabusReviewDecision, [_id("syllabus-review", "v1")])
    syllabus = await session.get(CourseSyllabus, _id("syllabus", "websec"))
    if syllabus is not None and syllabus.current_published_version_id in {_id("syllabus-version", "v1"), _id("syllabus-version", "v2")}:
        syllabus.current_published_version_id = None
        await session.flush()
    counts["syllabus_versions"] += await _delete_by_ids(session, CourseSyllabusVersion, [_id("syllabus-version", "v1"), _id("syllabus-version", "v2")])
    if syllabus is not None:
        remaining = await session.scalar(select(CourseSyllabusVersion.id).where(CourseSyllabusVersion.syllabus_id == syllabus.id).limit(1))
        if remaining is None:
            counts["syllabuses"] += await _delete_by_ids(session, CourseSyllabus, [syllabus.id])
    counts["assets"] += await _delete_by_ids(session, CourseAssetGovernance, [_id("asset-governance", key) for key in ("sql-guide", "xss-guide", "defensive-foundations-lecture")])
    counts["bindings"] += await _delete_by_ids(session, CourseDocumentBinding, [_id("document-binding", key) for key in ("sql-guide", "xss-guide", "defensive-foundations-lecture")])
    counts["snapshots"] += await _delete_by_ids(session, ClassWeaknessSnapshot, snapshot_ids)
    counts["resource_versions"] += await _delete_by_ids(session, ResourceVersion, resource_version_ids)
    counts["resources"] += await _delete_by_ids(session, GeneratedResource, resource_ids)
    counts["evidence"] += await _delete_by_ids(session, WorkflowEvidenceSnapshot, evidence_ids)
    counts["agent_runs"] += await _delete_by_ids(session, AgentRun, run_ids)
    counts["workflow_runs"] += await _delete_by_ids(session, WorkflowRun, workflow_ids)
    counts["quiz_attempts"] += await _delete_by_ids(session, QuizAttempt, [_id("quiz-attempt", f"{student_id}:{window}:{slug}") for student_id in showcase_learner_ids for window in ("baseline", "recent") for slug in ("http-basics", "cookie-session", "sql-injection", "xss-reflected", "file-upload", "ssrf")])
    counts["learning_events"] += await _delete_by_ids(
        session,
        LearningEvent,
        [
            *[
                _id("learning-event", f"{student_id}:{index}")
                for student_id in showcase_learner_ids
                for index in range(6 + len(SHOWCASE_TUTOR_EXCHANGES))
            ],
            _id("learning-event", SHOWCASE_DEMO_ASSESSMENT_EVENT_KEY),
        ],
    )
    counts["learning_tasks"] += await _delete_by_ids(session, LearningTask, [_id("learning-task", f"{student_id}:{slug}") for student_id in showcase_learner_ids for slug in ("http-basics", "sql-injection", "xss-reflected", "file-upload", "ssrf")])
    counts["learning_paths"] += await _delete_by_ids(session, LearningPath, [_id("learning-path", str(student_id)) for student_id in showcase_learner_ids])
    counts["quiz_evidence"] += await _delete_by_ids(session, QuizItemEvidence, [_id("quiz-evidence", str(item["key"])) for item in SHOWCASE_QUIZZES])
    # Reports only exist to validate supplemental items; deleting all reports
    # for them is safe and leaves the base WEBSEC seed untouched.
    quiz_ids = [_quiz_id(str(item["key"])) for item in SHOWCASE_QUIZZES]
    report_ids = list((await session.execute(select(QuizQualityReport.id).where(QuizQualityReport.quiz_item_id.in_(quiz_ids)))).scalars())
    counts["quality_reports"] += await _delete_by_ids(session, QuizQualityReport, report_ids)
    counts["quiz_items"] += await _delete_by_ids(session, QuizItem, quiz_ids)
    counts["lecture_chunks"] += await _delete_by_ids(
        session,
        Chunk,
        [_id("lecture-chunk", f"{index:02d}") for index in range(len(_LECTURE_SECTION_KNOWLEDGE))],
    )
    counts["lecture_document_assets"] += await _delete_by_ids(session, DocumentAsset, [SHOWCASE_LECTURE_ASSET_ID])
    counts["lecture_documents"] += await _delete_by_ids(session, Document, [SHOWCASE_LECTURE_DOCUMENT_ID])
    counts["lecture_storage_objects"] += await _delete_by_ids(session, StorageObject, [SHOWCASE_LECTURE_STORAGE_ID])
    counts["group_members"] += await _delete_by_ids(session, StudentGroupMember, [_id("group-member", slug) for slug, *_ in SHOWCASE_STUDENTS])
    counts["enrollments"] += await _delete_by_ids(session, CourseEnrollment, [_id("enrollment", slug) for slug, *_ in SHOWCASE_STUDENTS])
    counts["groups"] += await _delete_by_ids(session, StudentGroup, [SHOWCASE_A_GROUP_B_ID, SHOWCASE_B_GROUP_A_ID, SHOWCASE_B_GROUP_B_ID])
    counts["class_teachers"] += await _delete_by_ids(session, TeachingClassTeacher, [SHOWCASE_CLASS_B_TEACHER_ID])
    counts["classes"] += await _delete_by_ids(session, TeachingClass, [SHOWCASE_CLASS_B_ID])
    await session.execute(delete(UserCapability).where(UserCapability.user_id.in_(student_ids)))
    await session.execute(delete(UserProfile).where(UserProfile.user_id.in_(student_ids)))
    counts["students"] += await _delete_by_ids(session, User, student_ids)
    counts["demo_student_capabilities"] += await _delete_by_ids(
        session,
        UserCapability,
        _demo_showcase_capability_ids(),
    )
    demo_profile = await session.get(UserProfile, DEMO_USER_ID)
    if (
        demo_profile is not None
        and dict(demo_profile.dimensions or {}).get("seed_profile") == PROFILE
        and dict(demo_profile.dimensions or {}).get("showcase_account") == SHOWCASE_DEMO_STUDENT_SLUG
    ):
        dimensions = dict(demo_profile.dimensions or {})
        for key in SHOWCASE_DEMO_PROFILE_KEYS:
            dimensions.pop(key, None)
        demo_profile.dimensions = dimensions
        counts["demo_student_profile_overlay"] += 1
    demo_user = await session.get(User, DEMO_USER_ID)
    if demo_user is not None and demo_user.display_name == SHOWCASE_DEMO_STUDENT_DISPLAY_NAME:
        demo_user.display_name = DEMO_USER_NAME
        counts["demo_student_display_overlay"] += 1
    counts["manifest"] += await _delete_by_ids(session, GovernanceAuditEvent, [MANIFEST_ID])
    return dict(counts)


async def run(session: AsyncSession | None = None, *, require_opt_in: bool = False) -> dict[str, Any]:
    if require_opt_in:
        _require_explicit_opt_in()
    if session is not None:
        return await _seed(session)
    _require_explicit_opt_in()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as own_session:
        result = await _seed(own_session)
        await own_session.commit()
    return result


async def verify(session: AsyncSession | None = None) -> dict[str, Any]:
    if session is not None:
        return await _verify(session)
    _require_explicit_opt_in()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as own_session:
        return await _verify(own_session)


async def reset(session: AsyncSession | None = None, *, require_opt_in: bool = False) -> dict[str, int]:
    if require_opt_in:
        _require_explicit_opt_in()
    if session is not None:
        return await _reset(session)
    _require_explicit_opt_in()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as own_session:
        result = await _reset(own_session)
        await own_session.commit()
    return result


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Controlled WEBSEC-101 showcase-course seed")
    parser.add_argument("command", choices=("seed", "verify", "reset"))
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    args = _parse_args()
    if args.command == "seed":
        print(asyncio.run(run(require_opt_in=True)))
    elif args.command == "verify":
        print(asyncio.run(verify()))
    else:
        print(asyncio.run(reset(require_opt_in=True)))
