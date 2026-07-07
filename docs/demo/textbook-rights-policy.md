# Textbook Rights Policy

Status: real

## Scope

This policy covers the three Chinese textbooks imported in 6-C-2 for `course_websec` RAG retrieval:

| Textbook | Publisher | License metadata |
|---|---|---|
| 现代密码学教程（第2版） | 北京邮电大学出版社 | `proprietary-educational-use` |
| 网络安全原理与实践 | 清华大学出版社 | `proprietary-educational-use` |
| 汇编语言（第3版） | 清华大学出版社 | `proprietary-educational-use` |

## Allowed Use

- Store RAG chunks in the local development database for SecureHub teaching demo retrieval.
- Show short evidence snippets with textbook title, chapter, and heading path.
- Keep metadata such as title, author, publisher, year, ISBN, chapter count, and chunk count in git.

## Prohibited Use

- Do not commit or push textbook PDFs.
- Do not commit or push MinerU `full.md` outputs.
- Do not publish reconstructed full chapters or full-book Markdown as SecureHub content.
- Do not remove textbook attribution from EvidenceDrawer or generated answers.

## Required Metadata

Every textbook document must include:

- `platform=mineru`
- `source_type=pdf_mineru`
- `license=proprietary-educational-use`
- `rights_note=教材版权归原作者与出版社；本项目仅在 SecureHub 内部教学演示 RAG 检索场景使用，不对外分发原文，展示时保留章节引用与来源标注。`
- `title_zh`, `author`, `publisher`, `year`, and `isbn` when known

Every textbook chunk must include:

- `source_type=pdf_mineru`
- `asset_id`
- `book_title`
- `chapter`
- `chapter_index`
- `heading_path`
- `heading_level`
- `section_hint` when available

## Git Hygiene

`.gitignore` excludes:

- `data/storage/course_websec/mineru/**/*.pdf`
- `data/storage/course_websec/mineru/**/full.md`
- `data/storage/course_websec/mineru/**/chapters/`
- the equivalent `mineru_ingested` PDF/full/chapter paths

The local database may contain chunks for retrieval, but the repository must only carry code, metadata, tests, and policy documents.
