from __future__ import annotations

import hashlib
import importlib.util
import io
import subprocess
import sys
from pathlib import Path
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_DIST_PATH = REPO_ROOT / "tools" / "check_dist.py"
RELEASE_CHECK_PATH = REPO_ROOT / "tools" / "release_check.py"
SNAPSHOT_PATH = REPO_ROOT / "src" / "atomref" / "data" / (
    "proatomic_density_neutral.zip"
)
VALID_WHEEL_METADATA = b"""\
Metadata-Version: 2.4
Name: atomref
Version: 0.2.1
Provides-Extra: all
Provides-Extra: dev
Provides-Extra: docs
Provides-Extra: notebooks
Provides-Extra: test
Requires-Dist: build>=1.2; extra == 'dev'
Requires-Dist: mkdocs-material>=9.5; extra == 'docs'
Requires-Dist: ipykernel>=6.29; extra == 'notebooks'
Requires-Dist: pytest>=7; extra == 'test'
Requires-Dist: build>=1.2; extra == 'all'
Requires-Dist: mkdocs-material>=9.5; extra == 'all'
Requires-Dist: ipykernel>=6.29; extra == 'all'
Requires-Dist: pytest>=7; extra == 'all'

"""

spec = importlib.util.spec_from_file_location("check_dist_tool", CHECK_DIST_PATH)
assert spec is not None and spec.loader is not None
check_dist = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check_dist
spec.loader.exec_module(check_dist)

release_spec = importlib.util.spec_from_file_location(
    "release_check_tool", RELEASE_CHECK_PATH
)
assert release_spec is not None and release_spec.loader is not None
release_check = importlib.util.module_from_spec(release_spec)
sys.modules[release_spec.name] = release_check
release_spec.loader.exec_module(release_check)


def _snapshot_with_modified_csv(payload: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
        csv_payload = bytearray(archive.read(check_dist.PROATOMIC_SNAPSHOT_MEMBER))
    csv_payload[len(csv_payload) // 2] ^= 1

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(check_dist.PROATOMIC_SNAPSHOT_MEMBER, csv_payload)
    return output.getvalue()


def test_dist_check_accepts_pinned_proatomic_snapshot() -> None:
    check_dist._assert_proatomic_snapshot(
        SNAPSHOT_PATH.read_bytes(),
        member=SNAPSHOT_PATH.name,
        label="source tree",
    )


def test_dist_check_requires_release_tools_and_legacy_data() -> None:
    assert "atomref/data/xh_bond_length.csv" in check_dist.REQUIRED_WHEEL_MEMBERS
    assert "src/atomref/data/xh_bond_length.csv" in (
        check_dist.REQUIRED_SDIST_SUFFIXES
    )
    assert ".flake8" in check_dist.REQUIRED_SDIST_SUFFIXES
    assert "tools/check_registry.py" in check_dist.REQUIRED_SDIST_SUFFIXES
    assert "tools/check_dist.py" in check_dist.REQUIRED_SDIST_SUFFIXES
    assert "CITATION.cff" in check_dist.REQUIRED_SDIST_SUFFIXES
    assert ".zenodo.json" in check_dist.REQUIRED_SDIST_SUFFIXES
    assert "docs/notebooks/05-proatomic-density-and-ias.ipynb" in (
        check_dist.REQUIRED_SDIST_SUFFIXES
    )
    assert "tools/export_notebooks.py" not in check_dist.REQUIRED_SDIST_SUFFIXES
    assert "dist-info/licenses/COPYING" in check_dist.REQUIRED_WHEEL_MEMBERS


def test_sdist_root_readme_cannot_be_satisfied_by_tools_readme() -> None:
    with pytest.raises(check_dist.DistCheckError, match="root-level 'README.md'"):
        check_dist._sdist_root_member(
            {"atomref-9.9.9/tools/README.md"},
            "README.md",
            label="test sdist",
        )


def test_sdist_layout_rejects_obsolete_notebook_paths() -> None:
    members = {
        "atomref-0.2.1/docs/notebooks/01-quickstart.ipynb",
        "atomref-0.2.1/notebooks/01-quickstart.ipynb",
    }

    with pytest.raises(check_dist.DistCheckError, match="exactly one source"):
        check_dist._assert_sdist_layout(members, label="test sdist")


def test_sdist_layout_rejects_generated_notebook_markdown() -> None:
    members = {
        f"atomref-0.2.1/{name}" for name in check_dist.EXPECTED_SDIST_NOTEBOOKS
    }
    members.add("atomref-0.2.1/docs/notebooks/01-quickstart.md")

    with pytest.raises(check_dist.DistCheckError, match="obsolete members"):
        check_dist._assert_sdist_layout(members, label="test sdist")


def test_wheel_metadata_accepts_empty_runtime_and_complete_all_extra() -> None:
    check_dist._assert_wheel_metadata(
        VALID_WHEEL_METADATA,
        member="atomref.dist-info/METADATA",
        label="test wheel",
    )


def test_wheel_metadata_rejects_incomplete_all_extra() -> None:
    payload = VALID_WHEEL_METADATA.replace(
        b"Requires-Dist: pytest>=7; extra == 'all'\n",
        b"",
    )

    with pytest.raises(check_dist.DistCheckError, match="all extra must equal"):
        check_dist._assert_wheel_metadata(
            payload,
            member="atomref.dist-info/METADATA",
            label="test wheel",
        )


def test_dist_check_accepts_conventional_regular_file_modes() -> None:
    check_dist._assert_regular_file_modes(
        [("atomref/module.py", 0o100644), ("atomref/data/table.csv", 0o644)],
        label="test artifact",
    )


def test_dist_check_rejects_executable_payload_file_modes() -> None:
    with pytest.raises(check_dist.DistCheckError, match="module.py=0755"):
        check_dist._assert_regular_file_modes(
            [("atomref/module.py", 0o100755)],
            label="test artifact",
        )


def test_wheel_metadata_rejects_runtime_dependencies() -> None:
    payload = (
        VALID_WHEEL_METADATA.rstrip()
        + b"\nRequires-Dist: numpy>=2\n\n"
    )

    with pytest.raises(check_dist.DistCheckError, match="runtime requirements"):
        check_dist._assert_wheel_metadata(
            payload,
            member="atomref.dist-info/METADATA",
            label="test wheel",
        )


def test_dist_check_rejects_changed_snapshot_archive() -> None:
    payload = SNAPSHOT_PATH.read_bytes() + b"altered"

    with pytest.raises(check_dist.DistCheckError, match="snapshot SHA-256"):
        check_dist._assert_proatomic_snapshot(
            payload,
            member=SNAPSHOT_PATH.name,
            label="test wheel",
        )


def test_dist_check_independently_rejects_changed_inner_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _snapshot_with_modified_csv(SNAPSHOT_PATH.read_bytes())
    monkeypatch.setattr(
        check_dist,
        "EXPECTED_PROATOMIC_SNAPSHOT_SHA256",
        hashlib.sha256(payload).hexdigest(),
    )

    with pytest.raises(check_dist.DistCheckError, match="inner CSV SHA-256"):
        check_dist._assert_proatomic_snapshot(
            payload,
            member=SNAPSHOT_PATH.name,
            label="test sdist",
        )


# Keeping this as a subprocess test ensures the helper stays importable and
# exposes a stable CLI entry point without running the expensive full release
# workflow inside the unit test suite.
def test_release_check_help() -> None:
    result = subprocess.run(
        [sys.executable, "tools/release_check.py", "--help"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "release-preparation checks" in result.stdout
    assert "--skip-install-checks" in result.stdout


def test_release_docs_build_suppresses_material_banner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def record(*args: str, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(release_check, "_run", record)
    release_check._build_docs()

    assert calls == [
        (
            ("mkdocs", "build", "--strict"),
            {"extra_env": {"NO_MKDOCS_2_WARNING": "true"}},
        )
    ]


def test_release_command_merges_extra_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def record(args: tuple[str, ...], **kwargs: object) -> None:
        captured["args"] = args
        captured.update(kwargs)

    monkeypatch.setenv("ATOMREF_PARENT_ENV", "preserved")
    monkeypatch.setattr(release_check.subprocess, "run", record)
    release_check._run(
        "mkdocs",
        "build",
        extra_env={"NO_MKDOCS_2_WARNING": "true"},
    )

    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["ATOMREF_PARENT_ENV"] == "preserved"
    assert environment["NO_MKDOCS_2_WARNING"] == "true"


@pytest.mark.parametrize(
    "workflow",
    [REPO_ROOT / ".github/workflows/ci.yml", REPO_ROOT / ".github/workflows/docs.yml"],
)
def test_docs_workflows_suppress_material_banner(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")

    assert 'NO_MKDOCS_2_WARNING: "true"' in text
