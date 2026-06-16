# Status: real

"""Contract alignment guard for ``EvidenceChunkDTO``.

Frozen by ``docs/api/evidence-contract.md`` (v1, 2026-06-16). Any field
add / rename / required-tier change must be co-edited with this test +
the FE ``EvidenceChunkDTO`` in ``frontend/src/lib/sse.types.ts``.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.evidence import CollectionMode, EvidenceChunkDTO


CONTRACT_FIELDS: set[str] = {
    # identity
    "chunk_id",
    "document_id",
    # body
    "chunk_text",
    "score",
    # source identity
    "platform",
    "rights_note",
    # source link (conditional)
    "source_url",
    # optional display
    "title",
    "author",
    "published_at",
    "fetched_at",
    "collection_mode",
    "asset_type",
    "page_no",
    "chapter",
    "timestamp",
    "license",
    "reliability",
}

REQUIRED_FIELDS: set[str] = {
    "chunk_id",
    "document_id",
    "chunk_text",
    "score",
    "platform",
    "rights_note",
}


def test_evidence_chunk_fields_match_contract() -> None:
    assert set(EvidenceChunkDTO.model_fields) == CONTRACT_FIELDS, (
        "EvidenceChunkDTO field set drifted from contract; "
        "update docs/api/evidence-contract.md §2 alongside the schema."
    )

    required = {
        name
        for name, field in EvidenceChunkDTO.model_fields.items()
        if field.is_required()
    }
    assert required == REQUIRED_FIELDS, (
        "EvidenceChunkDTO required-tier drifted; "
        "see docs/api/evidence-contract.md §1."
    )


def test_collection_mode_enum_values_match_contract() -> None:
    assert {member.value for member in CollectionMode} == {
        "manual",
        "api",
        "scrapling",
        "mediacrawler",
        "mindspider_reference",
    }


def test_source_url_required_when_platform_not_manual() -> None:
    with pytest.raises(ValidationError) as excinfo:
        EvidenceChunkDTO(
            chunk_id="c1",
            document_id="d1",
            chunk_text="text",
            score=0.5,
            platform="owasp",
            rights_note="CC BY-SA 4.0",
            source_url=None,
        )
    assert "source_url" in str(excinfo.value)


def test_source_url_optional_for_manual_platform() -> None:
    dto = EvidenceChunkDTO(
        chunk_id="c1",
        document_id="d1",
        chunk_text="text",
        score=0.5,
        platform="manual",
        rights_note="教师手工录入",
        source_url=None,
    )
    assert dto.source_url is None


def test_score_clamped_to_unit_range() -> None:
    with pytest.raises(ValidationError):
        EvidenceChunkDTO(
            chunk_id="c1",
            document_id="d1",
            chunk_text="text",
            score=1.5,
            platform="manual",
            rights_note="x",
        )


def test_new_contract_schemas_do_not_use_unbounded_any_dicts() -> None:
    schema_dir = Path(__file__).parents[2] / "app" / "schemas"
    checked = [
        "agent.py",
        "resource.py",
        "evidence.py",
        "course.py",
        "rag.py",
    ]
    for filename in checked:
        assert "dict[str, Any]" not in (schema_dir / filename).read_text(encoding="utf-8")
