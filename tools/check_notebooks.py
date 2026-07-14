#!/usr/bin/env python3
"""Validate notebook JSON structure and execute notebook code cells."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

NOTEBOOKS = REPO_ROOT / "notebooks"
REQUIRED_NOTEBOOKS = (
    "01-quickstart.ipynb",
    "02-policies-and-assessment.ipynb",
    "03-custom-sets-and-discovery.ipynb",
    "04-ias-method-selection-study.ipynb",
    "05-proatomic-density-and-ias.ipynb",
)

RELEASE_NOTEBOOK_REQUIREMENTS = {
    "04-ias-method-selection-study.ipynb": {
        "markdown": (
            "# Choosing a practical neutral-proatom IAS proxy",
            "## Numerical policy examined here",
            "## Representative pairwise results",
            "## Why homonuclear symmetry overrides raw shell minima",
            "## Decision recorded by this study",
        ),
        "output_cells": (6, 8, 10, 12, 14, 16),
        "plot_cells": (),
    },
    "05-proatomic-density-and-ias.ipynb": {
        "markdown": (
            "# Neutral proatomic density and pairwise IAS-proxy workflows",
            "## Dataset discovery and provenance",
            "## Profile retrieval and scalar evaluation",
            "## Radial-density profiles",
            "## Ordinary heteronuclear pair: boundary and minimum",
            "## Component and summed line densities",
            "## Exact homonuclear midpoint",
            "## Low-density gap",
            "## No resolved interior minimum",
            "## Mode selection, statuses, and limitations",
        ),
        "output_cells": (3, 5, 7, 9, 11, 13, 15, 17, 19),
        "plot_cells": (9, 13),
    },
}


class NotebookCheckError(RuntimeError):
    """Raised when a notebook is malformed or fails to execute."""


def iter_notebooks() -> tuple[Path, ...]:
    """Return the notebooks that are expected to ship with the project."""

    return tuple(NOTEBOOKS / name for name in REQUIRED_NOTEBOOKS)


def load_notebook(path: Path) -> dict[str, object]:
    """Load one notebook JSON document."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise NotebookCheckError(f"{path.name}: expected top-level JSON object")
    return data


def _cell_source(cell: dict[str, object], *, path: Path, index: int) -> str:
    """Return normalized source text for one notebook cell."""

    source = cell.get("source", [])
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    raise NotebookCheckError(f"{path.name}: cell {index} has invalid source")


def iter_code_cells(data: dict[str, object], *, path: Path) -> tuple[str, ...]:
    """Return notebook code-cell sources in order."""

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
        code.append(_cell_source(cell, path=path, index=index + 1))
    if not code:
        raise NotebookCheckError(f"{path.name}: contains no code cells")
    return tuple(code)


def validate_saved_release_notebook(
    data: dict[str, object],
    *,
    path: Path,
) -> None:
    """Validate the small saved-state contract for release notebooks."""

    requirements = RELEASE_NOTEBOOK_REQUIREMENTS.get(path.name)
    if requirements is None:
        return
    if data.get("nbformat") != 4:
        raise NotebookCheckError(f"{path.name}: expected notebook format 4")

    cells = data.get("cells")
    if not isinstance(cells, list):
        raise NotebookCheckError(f"{path.name}: missing notebook cell list")

    markdown_parts: list[str] = []
    execution_counts: list[int] = []
    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict):
            raise NotebookCheckError(f"{path.name}: cell {index} is not an object")
        source = _cell_source(cell, path=path, index=index)
        if cell.get("cell_type") == "markdown":
            markdown_parts.append(source)
            continue
        if cell.get("cell_type") != "code" or not source.strip():
            continue

        count = cell.get("execution_count")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise NotebookCheckError(
                f"{path.name}: nonempty code cell {index} lacks an execution count"
            )
        execution_counts.append(count)

        if index == 1 or not isinstance(cells[index - 2], dict):
            raise NotebookCheckError(
                f"{path.name}: code cell {index} lacks preceding Markdown"
            )
        previous = cells[index - 2]
        if previous.get("cell_type") != "markdown" or not _cell_source(
            previous,
            path=path,
            index=index - 1,
        ).strip():
            raise NotebookCheckError(
                f"{path.name}: code cell {index} lacks preceding Markdown"
            )

        outputs = cell.get("outputs")
        if not isinstance(outputs, list):
            raise NotebookCheckError(f"{path.name}: cell {index} has invalid outputs")
        if any(
            isinstance(output, dict) and output.get("output_type") == "error"
            for output in outputs
        ):
            raise NotebookCheckError(f"{path.name}: cell {index} saved an error")

    expected_counts = list(range(1, len(execution_counts) + 1))
    if execution_counts != expected_counts:
        raise NotebookCheckError(
            f"{path.name}: execution counts are not sequential from 1"
        )

    markdown = "\n".join(markdown_parts)
    missing_markdown = [
        heading for heading in requirements["markdown"] if heading not in markdown
    ]
    if missing_markdown:
        raise NotebookCheckError(
            f"{path.name}: missing required Markdown: {', '.join(missing_markdown)}"
        )

    for cell_number in requirements["output_cells"]:
        cell = cells[cell_number - 1]
        outputs = cell.get("outputs") if isinstance(cell, dict) else None
        if not isinstance(outputs, list) or not outputs:
            raise NotebookCheckError(
                f"{path.name}: expected saved output in cell {cell_number}"
            )

    for cell_number in requirements["plot_cells"]:
        cell = cells[cell_number - 1]
        outputs = cell.get("outputs") if isinstance(cell, dict) else None
        has_png = isinstance(outputs, list) and any(
            isinstance(output, dict)
            and output.get("output_type") == "display_data"
            and isinstance(output.get("data"), dict)
            and "image/png" in output["data"]
            for output in outputs
        )
        if not has_png:
            raise NotebookCheckError(
                f"{path.name}: expected an embedded PNG in cell {cell_number}"
            )


def execute_notebook(path: Path) -> None:
    """Execute all code cells from one notebook in a shared namespace."""

    if not path.exists():
        raise NotebookCheckError(f"missing notebook: {path}")
    data = load_notebook(path)
    validate_saved_release_notebook(data, path=path)
    namespace = {"__name__": "__main__"}
    for index, source in enumerate(iter_code_cells(data, path=path), start=1):
        if not source.strip():
            continue
        try:
            code = compile(source, f"{path.name}::cell{index}", "exec")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exec(code, namespace, namespace)
        except Exception as exc:  # noqa: BLE001
            raise NotebookCheckError(
                f"{path.name}: execution failed in code cell {index}: {exc}"
            ) from exc


def main() -> int:
    """Validate and execute every required notebook."""

    notebooks = iter_notebooks()
    previous_cwd = Path.cwd()
    previous_backend = os.environ.get("MPLBACKEND")
    previous_config = os.environ.get("MPLCONFIGDIR")
    with tempfile.TemporaryDirectory(prefix="atomref-notebooks-") as tmp:
        isolated_root = Path(tmp)
        shutil.copytree(SRC, isolated_root / "src")
        matplotlib_config = isolated_root / "matplotlib"
        matplotlib_config.mkdir()
        try:
            os.environ["MPLBACKEND"] = "Agg"
            os.environ["MPLCONFIGDIR"] = str(matplotlib_config)
            os.chdir(isolated_root)
            for notebook in notebooks:
                execute_notebook(notebook)
                pyplot = sys.modules.get("matplotlib.pyplot")
                if pyplot is not None:
                    pyplot.close("all")
        finally:
            os.chdir(previous_cwd)
            if previous_backend is None:
                os.environ.pop("MPLBACKEND", None)
            else:
                os.environ["MPLBACKEND"] = previous_backend
            if previous_config is None:
                os.environ.pop("MPLCONFIGDIR", None)
            else:
                os.environ["MPLCONFIGDIR"] = previous_config
    print(f"Validated {len(notebooks)} notebook(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
