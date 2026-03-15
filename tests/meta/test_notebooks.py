from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "tools" / "check_notebooks.py"
EXPORT_SCRIPT = REPO_ROOT / "tools" / "export_notebooks.py"
NOTEBOOKS = REPO_ROOT / "notebooks"
EXPORTED_NOTEBOOKS = REPO_ROOT / "docs" / "notebooks"


def test_notebook_files_exist() -> None:
    expected = {
        "01-quickstart.ipynb",
        "02-policies-and-assessment.ipynb",
        "03-custom-sets-and-discovery.ipynb",
    }
    actual = {path.name for path in NOTEBOOKS.glob("*.ipynb")}
    assert expected.issubset(actual)


def test_notebooks_validate_and_execute() -> None:
    subprocess.run([sys.executable, str(CHECK_SCRIPT)], cwd=REPO_ROOT, check=True)


def test_exported_notebook_pages_are_in_sync() -> None:
    expected = {
        "01-quickstart.md",
        "02-policies-and-assessment.md",
        "03-custom-sets-and-discovery.md",
    }
    actual = {path.name for path in EXPORTED_NOTEBOOKS.glob("*.md")}
    assert expected.issubset(actual)
    subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--check"],
        cwd=REPO_ROOT,
        check=True,
    )
