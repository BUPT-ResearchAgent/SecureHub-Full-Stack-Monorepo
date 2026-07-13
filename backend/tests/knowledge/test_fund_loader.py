"""Manifest-level checks that do not require PostgreSQL or provider access."""

from __future__ import annotations

from urllib.parse import urlparse

from app.knowledge.loaders.fund_loader import FUND_DOMAIN, FUND_SOURCE_MANIFEST, _source_text


def test_fund_manifest_has_three_official_source_candidates_with_required_metadata() -> None:
    assert FUND_DOMAIN == "fund"
    assert len(FUND_SOURCE_MANIFEST) >= 3
    assert len({item.slug for item in FUND_SOURCE_MANIFEST}) == len(FUND_SOURCE_MANIFEST)
    assert len({item.source_url for item in FUND_SOURCE_MANIFEST}) == len(FUND_SOURCE_MANIFEST)

    for item in FUND_SOURCE_MANIFEST:
        parsed = urlparse(item.source_url)
        assert parsed.scheme == "https"
        assert parsed.netloc and "example." not in parsed.netloc
        assert item.fund_name and item.level and item.direction and item.deadline
        assert item.rights_note and item.license
        assert item.published_at == "未标注"
        assert item.updated_at == "未标注"
        source_text = _source_text(item)
        assert item.source_url in source_text
        assert item.deadline in source_text
        assert "资助金额" in source_text  # Explicitly refuses to invent it.
