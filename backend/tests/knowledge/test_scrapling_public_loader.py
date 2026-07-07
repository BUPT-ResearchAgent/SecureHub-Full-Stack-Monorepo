# Status: real

from pathlib import Path

from sqlalchemy import select

import pytest

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import
from app.knowledge.loaders.owasp_loader import owasp_import
from app.knowledge.loaders.scrapling_public_importer import (
    PLATFORM_SOURCES,
    build_arg_parser,
    build_sources,
    load_cache_dir,
    load_source_file,
    main_async,
)
from app.services.knowledge.crawling.crawler_policy import (
    CrawlPolicy,
    CrawlPolicyError,
    CrawlRequest,
)
from app.services.knowledge.retrieval_service import RetrievalService


OWASP_SQLI_HTML = """
<html>
  <head><title>OWASP SQL Injection</title></head>
  <body>
    <main>
      <h1>SQL Injection</h1>
      <p>SQL injection occurs when untrusted input is included in a query.</p>
      <p>Prepared statements and parameterized queries separate data from SQL syntax.</p>
    </main>
  </body>
</html>
"""

NOISY_OWASP_SQLI_HTML = """
<html>
  <head>
    <title>OWASP SQL Injection</title>
    <style>#banner img { max-width: 30em; }</style>
    <script>
      mlistr += "<li><a href='/sitemap'>SITEMAP</a></li>";
      $('#midmenu').html(mlistr);
      $(".accordion").click(function () {});
    </script>
  </head>
  <body>
    <nav>Store Donate Join Search</nav>
    <header>This website uses cookies to analyze our traffic.</header>
    <main id="main">
      <h1>SQL Injection</h1>
      <h2>Overview</h2>
      <p>A SQL injection attack consists of insertion or injection of a SQL query
      via input data from the client to the application.</p>
      <p>Parameterized queries separate untrusted data from SQL syntax and reduce
      the risk of SQL injection vulnerabilities.</p>
    </main>
    <footer>Copyright and navigation links</footer>
  </body>
</html>
"""


@pytest.mark.anyio
async def test_generic_web_import_normalizes_public_page(sqlite_session) -> None:
    result = await generic_web_import(
        [
            WebSourceSpec(
                url="https://owasp.org/www-community/attacks/SQL_Injection",
                html_text=OWASP_SQLI_HTML,
                platform="owasp",
                author="OWASP",
                license="CC BY-SA 4.0",
                rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
                reliability=0.9,
            )
        ],
        session=sqlite_session,
        storage_prefix="course_websec/test/web",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    hits = await RetrievalService(sqlite_session).retrieve(
        "SQL injection parameterized queries",
        domain="course_websec",
        top_k=3,
        filters={"platform": "owasp"},
    )

    assert result.document_ids
    assert result.asset_count == 2
    assert documents[0].metadata_["platform"] == "owasp"
    assert documents[0].metadata_["rights_note"]
    assert {asset.asset_type for asset in assets} == {"raw_html", "markdown_full"}
    assert all(obj.object_key.startswith("course_websec/test/web/") for obj in objects)
    assert hits
    assert hits[0].metadata["platform"] == "owasp"


@pytest.mark.anyio
async def test_owasp_loader_uses_offline_specs(sqlite_session) -> None:
    result = await owasp_import(
        [
            WebSourceSpec(
                url="https://owasp.org/www-community/attacks/SQL_Injection",
                title="OWASP SQL Injection",
                html_text=OWASP_SQLI_HTML,
                platform="owasp",
                author="OWASP",
                license="CC BY-SA 4.0",
                rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
            )
        ],
        session=sqlite_session,
        storage_prefix="course_websec/test/owasp",
    )

    assert result.domain == "course_websec"
    assert result.chunk_count >= 1


@pytest.mark.anyio
async def test_public_loader_strips_page_chrome_before_chunking(sqlite_session) -> None:
    await generic_web_import(
        [
            WebSourceSpec(
                url="https://owasp.org/www-community/attacks/SQL_Injection",
                title="OWASP SQL Injection",
                html_text=NOISY_OWASP_SQLI_HTML,
                platform="owasp",
                author="OWASP",
                license="CC BY-SA 4.0",
                rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
            )
        ],
        session=sqlite_session,
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()

    assert "SQL injection attack consists" in documents[0].raw_text
    assert "Parameterized queries" in documents[0].raw_text
    assert "$('#midmenu')" not in documents[0].raw_text
    assert "#banner img" not in documents[0].raw_text
    assert "Store Donate Join" not in documents[0].raw_text


def test_crawler_policy_rejects_bypass_and_proxy_options() -> None:
    policy = CrawlPolicy()

    with pytest.raises(CrawlPolicyError):
        policy.validate_request(
            CrawlRequest(
                url="https://example.com",
                options={"solve_cloudflare": True},
            )
        )

    with pytest.raises(CrawlPolicyError):
        policy.validate_request(
            CrawlRequest(
                url="https://example.com",
                options={"proxy": "socks5://127.0.0.1:1080"},
            )
        )


def test_scrapling_public_importer_resolves_websec_preset() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(["--preset", "websec-core", "--limit", "2"])
    sources = build_sources(args)

    assert len(sources) == 2
    assert sources[0].platform == "owasp"
    assert sources[0].xpath
    assert sources[1].url == "https://owasp.org/www-community/attacks/xss/"


def test_scrapling_public_importer_loads_jsonl_source_file(tmp_path) -> None:
    source_file = tmp_path / "sources.jsonl"
    source_file.write_text(
        "\n".join(
            [
                (
                    '{"url":"https://example.test/websec",'
                    '"title":"Example WebSec",'
                    '"platform":"example",'
                    '"xpath":"//main",'
                    '"metadata":{"topic":"xss"}}'
                )
            ]
        ),
        encoding="utf-8",
    )

    sources = load_source_file(source_file)

    assert len(sources) == 1
    assert sources[0].title == "Example WebSec"
    assert sources[0].platform == "example"
    assert sources[0].xpath == "//main"
    assert sources[0].metadata == {"topic": "xss"}


@pytest.mark.anyio
async def test_scrapling_public_importer_dry_run_skips_database(capsys) -> None:
    summary = await main_async(["--preset", "websec-core", "--limit", "1", "--dry-run"])
    output = capsys.readouterr().out

    assert summary.requested_count == 1
    assert summary.imported == []
    assert "dry-run platform=owasp" in output


@pytest.mark.anyio
async def test_owasp_ingestion_full_pipeline_from_cache(sqlite_session) -> None:
    sources = _load_cached_sources("owasp", minimum=3)
    result = await generic_web_import(sources, session=sqlite_session, storage_prefix="course_websec/test/owasp")
    await sqlite_session.commit()

    assert len(result.document_ids) >= 3
    await _assert_full_pipeline(sqlite_session, platform="owasp", minimum_documents=3)


@pytest.mark.anyio
async def test_portswigger_ingestion_full_pipeline_from_cache(sqlite_session) -> None:
    sources = _load_cached_sources("portswigger", minimum=3)
    result = await generic_web_import(
        sources,
        session=sqlite_session,
        storage_prefix="course_websec/test/portswigger",
    )
    await sqlite_session.commit()

    assert len(result.document_ids) >= 3
    await _assert_full_pipeline(sqlite_session, platform="portswigger", minimum_documents=3)


@pytest.mark.anyio
async def test_github_docs_ingestion_full_pipeline_from_cache(sqlite_session) -> None:
    sources = _load_cached_sources("github", minimum=3)
    result = await generic_web_import(sources, session=sqlite_session, storage_prefix="course_websec/test/github")
    await sqlite_session.commit()

    assert len(result.document_ids) >= 3
    await _assert_full_pipeline(sqlite_session, platform="github", minimum_documents=3)


@pytest.mark.anyio
async def test_scrapling_documents_have_required_metadata(sqlite_session) -> None:
    cached_sources: list[WebSourceSpec] = []
    for platform in ("owasp", "portswigger", "github"):
        cached_sources.extend(_load_cached_sources(platform, minimum=3)[:3])
    await generic_web_import(cached_sources, session=sqlite_session, storage_prefix="course_websec/test/replay")
    await sqlite_session.commit()

    documents = (
        await sqlite_session.execute(select(Document).where(Document.metadata_["collection_mode"].as_string() == "scrapling"))
    ).scalars().all()
    assert documents
    for document in documents:
        for key in ("platform", "source_url", "fetched_at", "rights_note", "collection_mode", "title"):
            assert document.metadata_.get(key), f"document {document.id} missing {key}"


def _load_cached_sources(platform: str, *, minimum: int) -> list[WebSourceSpec]:
    cache_dir = _repo_root() / "data" / "storage" / "course_websec" / platform
    sources = load_cache_dir(cache_dir, candidates=PLATFORM_SOURCES[platform])
    unique_by_url = {source.url: source for source in sources}
    cached = list(unique_by_url.values())
    if len(cached) < minimum:
        pytest.skip(f"need at least {minimum} cached {platform} pages, found {len(cached)}")
    return cached[:minimum]


async def _assert_full_pipeline(sqlite_session, *, platform: str, minimum_documents: int) -> None:
    documents = (
        await sqlite_session.execute(select(Document).where(Document.metadata_["platform"].as_string() == platform))
    ).scalars().all()
    assert len(documents) >= minimum_documents

    for document in documents:
        assert document.raw_text and len(document.raw_text) >= 80
        for key in ("platform", "source_url", "fetched_at", "rights_note", "collection_mode", "title"):
            assert document.metadata_.get(key), f"document {document.id} missing {key}"

        assets = (
            await sqlite_session.execute(select(DocumentAsset).where(DocumentAsset.document_id == document.id))
        ).scalars().all()
        assert {asset.asset_type for asset in assets} >= {"raw_html", "markdown_full"}

        chunks = (
            await sqlite_session.execute(select(Chunk).where(Chunk.document_id == document.id))
        ).scalars().all()
        assert chunks
        assert all(chunk.metadata_.get("platform") == platform for chunk in chunks)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
