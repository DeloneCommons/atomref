#!/usr/bin/env python3
"""Validate notebook JSON structure and execute notebook code cells."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

NOTEBOOKS = REPO_ROOT / "notebooks"
REQUIRED_NOTEBOOKS = (
    "01-quickstart.ipynb",
    "02-policies-and-assessment.ipynb",
    "03-custom-sets-and-discovery.ipynb",
)


class NotebookCheckError(RuntimeError):
    """Raised when a notebook is malformed or fails to execute."""


def iter_notebooks() -> tuple[Path, ...]:
    return tuple(NOTEBOOKS / name for name in REQUIRED_NOTEBOOKS)


def load_notebook(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise NotebookCheckError(f"{path.name}: expected top-level JSON object")
    return data


def iter_code_cells(data: dict[str, object], *, path: Path) -> tuple[str, ...]:
    cells = data.get("cells")
    if not isinstance(cells, list):
        raise NotebookCheckError(f"{path.name}: missing notebook cell list")

    code: list[str] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            raise NotebookCheckError(f"{path.name}: cell {index} is not an object")
        cell_type = cell.get("cell_type")
        if cell_type != "code":
            continue
        source = cell.get("source", [])
        if isinstance(source, str):
            text = source
        elif isinstance(source, list) and all(isinstance(line, str) for line in source):
            text = "".join(source)
        else:
            raise NotebookCheckError(
                f"{path.name}: cell {index} has invalid code source"
            )
        code.append(text)
    if not code:
        raise NotebookCheckError(f"{path.name}: contains no code cells")
    return tuple(code)


def execute_notebook(path: Path) -> None:
    if not path.exists():
        raise NotebookCheckError(f"missing notebook: {path}")
    data = load_notebook(path)
    namespace = {"__name__": "__main__"}
    for index, source in enumerate(iter_code_cells(data, path=path), start=1):
        if not source.strip():
            continue
        try:
            code = compile(source, f"{path.name}::cell{index}", "exec")
            with redirect_stdout(io.StringIO()):
                exec(code, namespace, namespace)
        except Exception as exc:  # noqa: BLE001
            raise NotebookCheckError(
                f"{path.name}: execution failed in code cell {index}: {exc}"
            ) from exc


def main() -> int:
    notebooks = iter_notebooks()
    for notebook in notebooks:
        execute_notebook(notebook)
    print(f"Validated {len(notebooks)} notebook(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
