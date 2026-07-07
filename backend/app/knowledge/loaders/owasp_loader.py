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
        metadata={"topic": "sql_injection"},
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
        metadata={"topic": "xss"},
    ),
    # UNREACHABLE 2026-07-07: public fetch returned 404.
    WebSourceSpec(
        url="https://owasp.org/www-community/OWASP_Top_Ten",
        title="OWASP Top 10 Overview",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "owasp_top_ten"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/csrf",
        title="OWASP Cross-Site Request Forgery",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "csrf"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload",
        title="OWASP Unrestricted File Upload",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "file_upload"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/Server_Side_Request_Forgery",
        title="OWASP Server Side Request Forgery",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "ssrf"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/Session_hijacking_attack",
        title="OWASP Session Hijacking Attack",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "session_hijacking"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/Broken_Access_Control",
        title="OWASP Broken Access Control",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "access_control"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/Command_Injection",
        title="OWASP Command Injection",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "command_injection"},
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data",
        title="OWASP Deserialization of Untrusted Data",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "deserialization"},
    ),
    # UNREACHABLE 2026-07-07: public fetch returned 404.
    WebSourceSpec(
        url="https://owasp.org/www-community/vulnerabilities/Insecure_Cryptographic_Storage",
        title="OWASP Insecure Cryptographic Storage",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
        metadata={"topic": "crypto_storage"},
    ),
]


async def owasp_import(
    sources: list[WebSourceSpec] | None = None,
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/owasp",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    return await generic_web_import(
        sources or DEFAULT_OWASP_WEBSEC_SOURCES,
        session=session,
        domain=domain,
        storage_prefix=storage_prefix,
        client=client,
        policy=policy,
    )
