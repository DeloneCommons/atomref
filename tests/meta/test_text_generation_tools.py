from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools" / "export_notebooks.py"

spec = importlib.util.spec_from_file_location("export_notebooks_tool", MODULE_PATH)
assert spec is not None and spec.loader is not None
export_notebooks = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = export_notebooks
spec.loader.exec_module(export_notebooks)


def test_export_notebooks_check_ignores_crlf(tmp_path: Path) -> None:
    """Notebook export checks should ignore Windows vs Unix newline differences."""

    output_dir = tmp_path / "docs"
    output_dir.mkdir()

    for notebook_name, output_name in export_notebooks.NOTEBOOK_OUTPUTS.items():
        rendered = export_notebooks._export_markdown(
            export_notebooks.NOTEBOOKS / notebook_name
        )
        (output_dir / output_name).write_text(
            rendered.replace("\n", "\r\n"),
            encoding="utf-8",
            newline="",
        )

    assert export_notebooks.export_notebooks(output_dir, check=True) == 0
