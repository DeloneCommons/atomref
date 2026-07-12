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
SNAPSHOT_PATH = REPO_ROOT / "src" / "atomref" / "data" / (
    "proatomic_density_neutral.zip"
)

spec = importlib.util.spec_from_file_location("check_dist_tool", CHECK_DIST_PATH)
assert spec is not None and spec.loader is not None
check_dist = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check_dist
spec.loader.exec_module(check_dist)


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
