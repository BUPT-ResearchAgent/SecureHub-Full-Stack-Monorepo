# Status: real

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.loaders.course_loader import CourseLoadResult
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import
from app.services.knowledge.crawling.crawler_policy import CrawlPolicy
from app.services.knowledge.crawling.scrapling_client import ScraplingClient


OWASP_CONTENT_XPATH = (
    "//*[@id='main']|//main|//article|"
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' page-content ')]|"
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' content ')]"
)


DEFAULT_OWASP_WEBSEC_SOURCES = [
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/SQL_Injection",
        title="OWASP SQL Injection",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/xss/",
        title="OWASP Cross Site Scripting",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
]


async def owasp_import(
    sources: list[WebSourceSpec] | None = None,
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    return await generic_web_import(
        sources or DEFAULT_OWASP_WEBSEC_SOURCES,
        session=session,
        domain=domain,
        storage_prefix="course_websec/owasp",
        client=client,
        policy=policy,
    )
