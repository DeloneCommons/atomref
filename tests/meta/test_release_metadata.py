from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ZENODO_METADATA = REPO_ROOT / ".zenodo.json"
CITATION_METADATA = REPO_ROOT / "CITATION.cff"


def test_zenodo_metadata_describes_software_and_mixed_licenses() -> None:
    metadata = json.loads(ZENODO_METADATA.read_text(encoding="utf-8"))

    assert set(metadata) == {
        "title",
        "upload_type",
        "access_right",
        "description",
        "creators",
        "license",
        "keywords",
        "related_identifiers",
    }
    assert metadata["upload_type"] == "software"
    assert metadata["license"] == "LGPL-3.0-or-later"
    assert metadata["creators"] == [{"name": "Chernyshov, Ivan Yu."}]
    assert "CC BY 4.0" in metadata["description"]
    assert {
        "scheme": "doi",
        "identifier": "10.5281/zenodo.21291022",
        "relation": "isDerivedFrom",
        "resource_type": "dataset",
    } in metadata["related_identifiers"]


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
    ):
        assert required_line in text
    assert "preferred-citation:" not in text
