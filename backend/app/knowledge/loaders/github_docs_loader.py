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


async def github_docs_import(
    sources: list[GitHubDocsSource],
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
) -> CourseLoadResult:
    specs = [
        WebSourceSpec(
            url=source.url,
            title=source.title or f"{source.owner}/{source.repo} {source.path}",
            platform="github",
            author=f"{source.owner}/{source.repo} maintainers",
            license=source.license,
            rights_note="开源仓库公开文档；遵守仓库许可证，保留来源链接。",
            source_type="github_docs",
            reliability=0.8,
            html_text=source.html_text,
            metadata={
                "repo": f"{source.owner}/{source.repo}",
                "ref": source.ref,
                "path": source.path,
            },
        )
        for source in sources
    ]
    return await generic_web_import(
        specs,
        session=session,
        domain=domain,
        storage_prefix="course_websec/github",
        client=client,
        policy=policy,
    )
