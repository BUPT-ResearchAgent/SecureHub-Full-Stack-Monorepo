# Status: real

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.loaders.course_loader import CourseLoadResult
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import
from app.services.knowledge.crawling.crawler_policy import CrawlPolicy
from app.services.knowledge.crawling.scrapling_client import ScraplingClient


@dataclass(slots=True)
class GitHubDocsSource:
    owner: str
    repo: str
    path: str = "README.md"
    ref: str = "main"
    title: str | None = None
    license: str = "repository license"
    html_text: str | None = None

    @property
    def url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{self.ref}/{self.path}"


DEFAULT_GITHUB_WEBSEC_SOURCES = [
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md",
        title="OWASP SQL Injection Prevention Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md",
        title="OWASP Cross Site Scripting Prevention Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md",
        title="OWASP Cross-Site Request Forgery Prevention Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/File_Upload_Cheat_Sheet.md",
        title="OWASP File Upload Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md",
        title="OWASP Server Side Request Forgery Prevention Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/Authentication_Cheat_Sheet.md",
        title="OWASP Authentication Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
    GitHubDocsSource(
        owner="OWASP",
        repo="CheatSheetSeries",
        ref="master",
        path="cheatsheets/Access_Control_Cheat_Sheet.md",
        title="OWASP Access Control Cheat Sheet",
        license="CC BY-SA 4.0",
    ),
]


async def github_docs_import(
    sources: list[GitHubDocsSource] | None = None,
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/github",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    specs = [
        WebSourceSpec(
            url=source.url,
            title=source.title or f"{source.owner}/{source.repo} {source.path}",
            platform="github",
            author=(
                "OWASP CheatSheetSeries Contributors"
                if source.owner == "OWASP" and source.repo == "CheatSheetSeries"
                else f"{source.owner}/{source.repo} maintainers"
            ),
            license=source.license,
            rights_note=(
                "OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取"
                if source.owner == "OWASP" and source.repo == "CheatSheetSeries"
                else "开源仓库公开文档；遵守仓库许可证，保留来源链接。"
            ),
            source_type="github_docs",
            reliability=0.95 if source.owner == "OWASP" and source.repo == "CheatSheetSeries" else 0.8,
            html_text=source.html_text,
            metadata={
                "repo": f"{source.owner}/{source.repo}",
                "ref": source.ref,
                "path": source.path,
                "topic": _topic_from_path(source.path),
            },
        )
        for source in (sources or DEFAULT_GITHUB_WEBSEC_SOURCES)
    ]
    return await generic_web_import(
        specs,
        session=session,
        domain=domain,
        storage_prefix=storage_prefix,
        client=client,
        policy=policy,
    )


def _topic_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1].removesuffix(".md").lower()
    if "sql_injection" in name:
        return "sql_injection"
    if "cross_site_scripting" in name:
        return "xss"
    if "request_forgery" in name:
        return "csrf"
    if "file_upload" in name:
        return "file_upload"
    if "server_side_request_forgery" in name:
        return "ssrf"
    if "authentication" in name:
        return "authentication"
    if "access_control" in name:
        return "access_control"
    return name
