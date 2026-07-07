# Source Rights Note

Status: real

## Scope

This note covers C-owned demo evidence for `course_websec`: OWASP, PortSwigger Web Security Academy, GitHub Docs fixtures, PDF/MinerU fixtures, and the minimal MediaCrawler export fixture.

## Source Boundaries

| Source | Allowed Use | Boundary |
|---|---|---|
| OWASP | Use short excerpts, summaries, and links for course evidence. Preserve platform, source URL, author, license, and rights note. | Do not mirror full pages as product-owned content. Attribute OWASP community material and keep links visible in evidence. |
| PortSwigger Web Security Academy | Use minimal learning summaries and source links as WebSec evidence. | Do not republish labs or full training content. Keep usage to indexing, retrieval, and citation in demo output. |
| GitHub Docs / repository docs fixture | Use repository docs only when the license allows it; store source URL, repo, ref, path, and license metadata. | Do not imply SecureHub owns third-party repository content. Do not remove license context. |
| PortSwigger Web Security Academy 6-C-1 live crawl | Public Learn chapter landing pages are cached as `raw_html` plus `markdown_full` only for classroom retrieval and citation. | Treat as PortSwigger EULA educational use: no lab answer harvesting, no paid/private content, no republication as SecureHub-owned courseware. |
| OWASP CheatSheetSeries raw markdown | Raw files are fetched from `raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/*.md`; metadata records repo, ref, path, CC BY-SA 4.0, and source URL. | Keep attribution to OWASP CheatSheetSeries contributors, preserve the raw source URL, and do not remove license or provenance context from evidence. |
| PDF / MinerU fixture | Use offline PDF/MinerU metadata and a small markdown stub for ingestion and evidence display. | Do not store unknown copyrighted full PDFs as bundled content. Keep original source and page/chapter metadata. |
| Chinese textbooks via MinerU | Use local RAG chunks and chapter metadata for SecureHub internal teaching demo retrieval. | Do not commit or push textbook PDFs or full Markdown. Do not present textbook text as SecureHub-owned content. See `docs/demo/textbook-rights-policy.md`. |
| MediaCrawler fixture | Consume one small offline export sample for B 站 retrieval tests. Keep platform link, author, and rights note. | Do not crawl public sites in CI, do not use login state, do not bypass CAPTCHA or platform risk controls, and do not batch rehost platform content. |
| MindSpider reference | P2 reference-only material for process comparison. | Do not connect to the production ingestion chain, do not add an agent, and do not add platform-specific tables. |

## Storage Rules

- Source materials go through `storage_objects`, `documents`, `document_assets`, and `chunks`.
- Generated learning artifacts go through `generated_resources` and `storage_objects`; they must not be written back into `documents`.
- All domain extensions, including `fund`, `policy`, `job`, and `competition`, must reuse unified `documents/chunks` with `domain` filters.
- Required evidence metadata: `platform`, `source_url`, `author`, `rights_note`, `collection_mode`, `asset_type`.
- PDF evidence should include `page_no` or `chapter` when available.
- Textbook evidence should include `chapter`, `heading_path`, `book_title`, and `license=proprietary-educational-use` when available.

## Demo Wording

Use "引用 / 摘要 / evidence" for third-party material. Avoid "原创资料库" for external content. SecureHub owns the organization, retrieval, citation, quality gate, and generated resource workflow; original sources remain attributed to their authors or platforms.
