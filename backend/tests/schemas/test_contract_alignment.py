# Status: real

from pathlib import Path

from app.schemas.evidence import EvidenceChunkDTO


def test_evidence_chunk_fields_match_contract() -> None:
    expected_fields = {
        "chunk_id",
        "document_id",
        "source_url",
        "platform",
        "author",
        "published_at",
        "fetched_at",
        "rights_note",
        "asset_type",
        "excerpt",
        "page_no",
        "chapter",
        "timestamp",
        "reliability",
    }
    assert set(EvidenceChunkDTO.model_fields) == expected_fields

    required = {
        name for name, field in EvidenceChunkDTO.model_fields.items() if field.is_required()
    }
    assert required == {"chunk_id", "document_id", "excerpt"}


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
