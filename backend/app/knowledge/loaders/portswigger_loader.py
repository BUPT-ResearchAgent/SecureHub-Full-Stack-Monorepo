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
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "sql_injection"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/cross-site-scripting",
        title="PortSwigger Cross-site scripting",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "xss"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/csrf",
        title="PortSwigger CSRF",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "csrf"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/file-upload",
        title="PortSwigger File Upload Vulnerabilities",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "file_upload"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/ssrf",
        title="PortSwigger SSRF",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "ssrf"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/authentication",
        title="PortSwigger Authentication",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "authentication"},
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/access-control",
        title="PortSwigger Access Control",
        platform="portswigger",
        author="PortSwigger",
        license="PortSwigger EULA (educational use)",
        rights_note="PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页",
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
        metadata={"topic": "access_control"},
    ),
]


async def portswigger_import(
    sources: list[WebSourceSpec] | None = None,
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/portswigger",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    return await generic_web_import(
        sources or DEFAULT_PORTSWIGGER_WEBSEC_SOURCES,
        session=session,
        domain=domain,
        storage_prefix=storage_prefix,
        client=client,
        policy=policy,
    )
