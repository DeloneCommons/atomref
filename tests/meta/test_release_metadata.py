from __future__ import annotations

from pathlib import Path
import re

from atomref import __version__


REPO_ROOT = Path(__file__).resolve().parents[2]
CITATION_METADATA = REPO_ROOT / "CITATION.cff"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def _top_level_scalar(text: str, key: str) -> str:
    """Return one simple top-level CFF scalar after schema validation."""

    match = re.search(
        rf"^{re.escape(key)}:\s*(?P<value>.+)$",
        text,
        flags=re.MULTILINE,
    )
    assert match is not None, f"missing top-level CFF field: {key}"
    value = match.group("value").strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _current_changelog_release() -> tuple[str, str]:
    """Return the first version and date recorded in the changelog."""

    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        r"^## (?P<version>\d+\.\d+\.\d+) - "
        r"(?P<date>\d{4}-\d{2}-\d{2})$",
        text,
        flags=re.MULTILINE,
    )
    assert match is not None
    return match.group("version"), match.group("date")


def test_citation_metadata_targets_the_versioned_software_repository() -> None:
    text = CITATION_METADATA.read_text(encoding="utf-8")
    changelog_version, changelog_date = _current_changelog_release()

    assert _top_level_scalar(text, "cff-version") == "1.2.0"
    assert _top_level_scalar(text, "title") == "atomref"
    assert _top_level_scalar(text, "type") == "software"
    assert _top_level_scalar(text, "version") == __version__ == changelog_version
    assert _top_level_scalar(text, "date-released") == changelog_date
    assert _top_level_scalar(text, "repository-code") == (
        "https://github.com/DeloneCommons/atomref"
    )
    assert _top_level_scalar(text, "license") == "LGPL-3.0-or-later"


def test_citation_abstract_describes_the_mixed_license_and_hash_locations() -> None:
    text = CITATION_METADATA.read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    assert "CC BY 4.0" in normalized
    assert (
        "NOTICE.md for the exact licensing boundary, attribution, and source DOIs."
        in normalized
    )
    assert (
        "The exact source commit and SHA-256 hashes are recorded in the packaged "
        "registry metadata."
        in normalized
    )
    assert re.search(r"^preferred-citation:", text, flags=re.MULTILINE) is None


def test_citation_cff_is_the_only_repository_deposit_metadata_file() -> None:
    assert CITATION_METADATA.is_file()
    assert not (REPO_ROOT / ".zenodo.json").exists()
