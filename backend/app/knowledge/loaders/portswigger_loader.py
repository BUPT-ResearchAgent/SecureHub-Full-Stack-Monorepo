# Status: real

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.loaders.course_loader import CourseLoadResult
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import
from app.services.knowledge.crawling.crawler_policy import CrawlPolicy
from app.services.knowledge.crawling.scrapling_client import ScraplingClient


PORTSWIGGER_CONTENT_XPATH = (
    "//main|//article|//*[@id='main-content']|//*[@id='content']|"
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' main-content ')]|"
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' article-content ')]|"
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' content ')]"
)


DEFAULT_PORTSWIGGER_WEBSEC_SOURCES = [
    WebSourceSpec(
        url="https://portswigger.net/web-security/sql-injection",
        title="PortSwigger SQL injection",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/cross-site-scripting",
        title="PortSwigger Cross-site scripting",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
]


async def portswigger_import(
    sources: list[WebSourceSpec] | None = None,
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    return await generic_web_import(
        sources or DEFAULT_PORTSWIGGER_WEBSEC_SOURCES,
        session=session,
        domain=domain,
        storage_prefix="course_websec/portswigger",
        client=client,
        policy=policy,
    )
