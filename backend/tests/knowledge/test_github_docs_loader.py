# Status: real

from sqlalchemy import select

import pytest

from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
from app.knowledge.loaders.github_docs_loader import GitHubDocsSource, github_docs_import
from app.services.knowledge.retrieval_service import RetrievalService


GITHUB_DOCS_HTML = """
<html>
  <head><title>Secure Coding Checklist</title></head>
  <body>
    <article>
      <h1>Secure Coding Checklist</h1>
      <p>安全编码 checklist starts from threat modeling, input validation,
      output encoding, authentication, authorization and dependency review.</p>
      <p>Every GitHub README or docs page should keep a clear fix workflow:
      issue, commit, regression test, evidence note and residual risk.</p>
      <p>For Web security labs, SQL injection uses parameterized queries,
      XSS uses context-aware output encoding, CSRF uses tokens and SameSite,
      and upload handlers isolate object_key storage outside the web root.</p>
    </article>
  </body>
</html>
"""


@pytest.mark.anyio
async def test_github_docs_import_e2e_offline_fixture(sqlite_session) -> None:
    result = await github_docs_import(
        [
            GitHubDocsSource(
                owner="securehub-demo",
                repo="websec-labs",
                path="docs/secure-coding.md",
                ref="main",
                title="SecureHub WebSec Secure Coding Docs",
                license="MIT",
                html_text=GITHUB_DOCS_HTML,
            )
        ],
        session=sqlite_session,
    )
    await sqlite_session.commit()

    document = await sqlite_session.get(Document, result.document_ids[0])
    assets = (
        await sqlite_session.execute(
            select(DocumentAsset).where(DocumentAsset.document_id == result.document_ids[0])
        )
    ).scalars().all()
    objects = (
        await sqlite_session.execute(
            select(StorageObject).where(
                StorageObject.object_key.like("course_websec/github/%")
            )
        )
    ).scalars().all()
    hits = await RetrievalService(sqlite_session).retrieve(
        "GitHub README 安全编码 checklist 修复闭环",
        domain="course_websec",
        top_k=5,
        filters={"platform": "github"},
    )

    assert result.domain == "course_websec"
    assert result.document_ids
    assert result.asset_count == 1
    assert result.chunk_count >= 1
    assert document is not None
    assert document.source_type == "github_docs"
    assert document.metadata_["platform"] == "github"
    assert document.metadata_["source_url"] == (
        "https://raw.githubusercontent.com/"
        "securehub-demo/websec-labs/main/docs/secure-coding.md"
    )
    assert document.metadata_["repo"] == "securehub-demo/websec-labs"
    assert document.metadata_["path"] == "docs/secure-coding.md"
    assert document.metadata_["rights_note"]
    assert assets
    assert assets[0].asset_type == "raw_html"
    assert assets[0].object_key.startswith("course_websec/github/")
    assert objects
    assert objects[0].object_key == assets[0].object_key
    assert hits
    assert all(hit.metadata["platform"] == "github" for hit in hits)
    assert any("安全编码" in hit.snippet or "fix workflow" in hit.snippet for hit in hits)
