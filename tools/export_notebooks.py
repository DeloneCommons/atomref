#!/usr/bin/env python3
"""Export bundled notebooks to Markdown pages for the docs."""

from __future__ import annotations

from contextlib import redirect_stdout
import argparse
import io
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

NOTEBOOKS = REPO_ROOT / "notebooks"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "notebooks"
NOTEBOOK_OUTPUTS = {
    "01-quickstart.ipynb": "01-quickstart.md",
    "02-policies-and-assessment.ipynb": "02-policies-and-assessment.md",
    "03-custom-sets-and-discovery.ipynb": "03-custom-sets-and-discovery.md",
}
HEADER = (
    "<!-- This file is generated from the matching notebook. -->\n"
    "<!-- Regenerate with: python tools/export_notebooks.py -->\n\n"
)


class NotebookExportError(RuntimeError):
    """Raised when notebook export fails."""


def _load_notebook(path: Path) -> dict[str, object]:
    """Load one notebook JSON document."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise NotebookExportError(f"{path.name}: expected top-level JSON object")
    return data


def _cell_source(cell: dict[str, object], *, path: Path, index: int) -> str:
    """Return normalized source text for one notebook cell."""

    source = cell.get("source", [])
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    raise NotebookExportError(f"{path.name}: invalid source in cell {index}")


def _export_markdown(path: Path) -> str:
    """Render one notebook as Markdown, executing code cells for output."""

    data = _load_notebook(path)
    cells = data.get("cells")
    if not isinstance(cells, list):
        raise NotebookExportError(f"{path.name}: missing notebook cell list")

    namespace = {"__name__": "__main__"}
    parts: list[str] = [HEADER]
    parts.append(
        f"[Open the original notebook on GitHub]"
        f"(https://github.com/DeloneCommons/atomref/blob/main/notebooks/{path.name})\n"
    )

    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict):
            raise NotebookExportError(f"{path.name}: cell {index} is not an object")
        source = _cell_source(cell, path=path, index=index)
        cell_type = cell.get("cell_type")
        if cell_type == "markdown":
            text = source.strip()
            if text:
                parts.append(f"{text}\n")
            continue
        if cell_type != "code":
            continue
        code_text = source.rstrip()
        parts.append("```python\n")
        parts.append(f"{code_text}\n")
        parts.append("```\n")
        if not code_text.strip():
            continue

        stdout = io.StringIO()
        try:
            code = compile(code_text, f"{path.name}::cell{index}", "exec")
            with redirect_stdout(stdout):
                exec(code, namespace, namespace)
        except Exception as exc:  # noqa: BLE001
            raise NotebookExportError(
                f"{path.name}: execution failed in code cell {index}: {exc}"
            ) from exc

        output = stdout.getvalue().rstrip()
        if output:
            parts.append("**Output**\n\n")
            parts.append("```text\n")
            parts.append(f"{output}\n")
            parts.append("```\n")

    return "\n".join(part.rstrip() for part in parts if part).rstrip() + "\n"


def export_notebooks(output_dir: Path, *, check: bool = False) -> int:
    """Export bundled notebooks or verify that exported pages are in sync."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for notebook_name, output_name in NOTEBOOK_OUTPUTS.items():
        notebook_path = NOTEBOOKS / notebook_name
        rendered = _export_markdown(notebook_path)
        output_path = output_dir / output_name
        if check:
            current = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if current != rendered:
                print(
                    f"{output_path} is out of sync with {notebook_path.name}",
                    file=sys.stderr,
                )
                return 1
        else:
            output_path.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    """Export notebook Markdown pages or check that they are current."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 when exported pages are out of sync",
    )
    args = parser.parse_args()
    return export_notebooks(args.output_dir, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
