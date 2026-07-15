from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CITATION_METADATA = REPO_ROOT / "CITATION.cff"


def test_citation_metadata_targets_the_versioned_software_repository() -> None:
    text = CITATION_METADATA.read_text(encoding="utf-8")

    for required_line in (
        "cff-version: 1.2.0",
        'title: "atomref"',
        "type: software",
        'version: "0.2.1"',
        "date-released: 2026-07-15",
        'repository-code: "https://github.com/DeloneCommons/atomref"',
        'license: "LGPL-3.0-or-later"',
        "CC BY 4.0",
        "NOTICE.md",
    ):
        assert required_line in text
    assert "preferred-citation:" not in text


def test_citation_cff_is_the_only_repository_deposit_metadata_file() -> None:
    assert CITATION_METADATA.is_file()
    assert not (REPO_ROOT / ".zenodo.json").exists()
