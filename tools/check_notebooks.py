#!/usr/bin/env python3
"""Smoke-execute notebooks with standard Jupyter tooling in a temporary tree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import nbformat
from nbclient import NotebookClient


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
NOTEBOOK_DIR = REPO_ROOT / "docs" / "notebooks"
REQUIRED_NOTEBOOKS = (
    "01-quickstart.ipynb",
    "02-policies-and-assessment.ipynb",
    "03-custom-sets-and-discovery.ipynb",
    "04-ias-method-selection-study.ipynb",
    "05-proatomic-density-and-ias.ipynb",
)
DEFAULT_TIMEOUT_SECONDS = 300


class NotebookCheckError(RuntimeError):
    """Raised when the requested notebook smoke check cannot be prepared."""


def default_notebooks() -> tuple[Path, ...]:
    """Return the five notebooks shipped as documentation."""

    return tuple(NOTEBOOK_DIR / name for name in REQUIRED_NOTEBOOKS)


def _resolve_notebooks(paths: list[Path]) -> tuple[Path, ...]:
    """Resolve requested notebooks and reject missing or ambiguous inputs."""

    notebooks = tuple(
        path.resolve() for path in (paths if paths else list(default_notebooks()))
    )
    names: set[str] = set()
    for path in notebooks:
        if not path.is_file():
            raise NotebookCheckError(f"missing notebook: {path}")
        if path.suffix != ".ipynb":
            raise NotebookCheckError(f"not a Jupyter notebook: {path}")
        if path.name in names:
            raise NotebookCheckError(
                f"notebook names must be unique for temporary execution: {path.name}"
            )
        names.add(path.name)
    if not notebooks:
        raise NotebookCheckError("no notebooks selected")
    return notebooks


def _execute_temporary_copy(path: Path, *, working_dir: Path) -> None:
    """Execute and write one temporary notebook copy, failing on cell errors."""

    with path.open(encoding="utf-8") as stream:
        notebook = nbformat.read(stream, as_version=4)
    kernel_name = notebook.get("metadata", {}).get("kernelspec", {}).get(
        "name", "python3"
    )
    client = NotebookClient(
        notebook,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        kernel_name=kernel_name,
        resources={"metadata": {"path": str(working_dir)}},
        allow_errors=False,
    )
    executed = client.execute()
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        nbformat.write(executed, stream)


def smoke_execute(paths: list[Path]) -> int:
    """Execute selected notebooks only after copying them into a temporary tree."""

    notebooks = _resolve_notebooks(paths)
    with tempfile.TemporaryDirectory(prefix="atomref-notebooks-") as tmp:
        temporary_root = Path(tmp)
        temporary_notebooks = temporary_root / "docs" / "notebooks"
        temporary_notebooks.mkdir(parents=True)
        shutil.copytree(
            SRC,
            temporary_root / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.py[co]"),
        )
        copied = []
        for source in notebooks:
            destination = temporary_notebooks / source.name
            shutil.copy2(source, destination)
            copied.append(destination)

        environment = {
            "IPYTHONDIR": str(temporary_root / "ipython"),
            "JUPYTER_CONFIG_DIR": str(temporary_root / "jupyter"),
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(temporary_root / "matplotlib"),
            "PYTHONPYCACHEPREFIX": str(temporary_root / "pycache"),
        }
        pythonpath = os.environ.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(temporary_root / "src")
        if pythonpath:
            environment["PYTHONPATH"] += os.pathsep + pythonpath

        with patch.dict(os.environ, environment, clear=False):
            for notebook in copied:
                _execute_temporary_copy(
                    notebook,
                    working_dir=temporary_notebooks,
                )

    print(f"Smoke-executed {len(notebooks)} notebook(s) in temporary kernels.")
    return 0


def main() -> int:
    """Parse notebook paths and run the temporary Jupyter smoke check."""

    parser = argparse.ArgumentParser(
        description=(
            "Smoke-execute documentation notebooks in a disposable tree without "
            "changing or comparing committed outputs."
        )
    )
    parser.add_argument(
        "notebooks",
        nargs="*",
        type=Path,
        help="optional notebook paths; defaults to every shipped notebook",
    )
    args = parser.parse_args()
    return smoke_execute(args.notebooks)


if __name__ == "__main__":
    raise SystemExit(main())
