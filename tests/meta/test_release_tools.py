from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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
