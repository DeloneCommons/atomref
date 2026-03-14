from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check_notebooks.py"
NOTEBOOKS = REPO_ROOT / "notebooks"


def test_notebook_files_exist() -> None:
    expected = {
        "01-quickstart.ipynb",
        "02-policies-and-assessment.ipynb",
        "03-custom-sets-and-discovery.ipynb",
    }
    actual = {path.name for path in NOTEBOOKS.glob("*.ipynb")}
    assert expected.issubset(actual)


def test_notebooks_validate_and_execute() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)
