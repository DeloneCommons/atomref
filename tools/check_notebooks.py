#!/usr/bin/env python3
"""Smoke-execute notebooks with standard Jupyter tooling in a temporary tree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


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
CELL_TIMEOUT_SECONDS = 300
KERNEL_STARTUP_TIMEOUT_SECONDS = 60
WORKER_TIMEOUT_SECONDS = 420
WORKER_TERMINATION_TIMEOUT_SECONDS = 10
CHECK_TIMEOUT_SECONDS = 15 * 60
IS_WINDOWS = os.name == "nt"


class NotebookCheckError(RuntimeError):
    """Raised when a notebook smoke check cannot be prepared or completed."""


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


def _worker_environment(temporary_root: Path) -> dict[str, str]:
    """Return an isolated environment for one notebook worker."""

    environment = os.environ.copy()
    environment.update(
        {
            "IPYTHONDIR": str(temporary_root / "ipython"),
            "JUPYTER_CONFIG_DIR": str(temporary_root / "jupyter"),
            "JUPYTER_RUNTIME_DIR": str(temporary_root / "jupyter-runtime"),
            "MPLBACKEND": "Agg",
            "MPLCONFIGDIR": str(temporary_root / "matplotlib"),
            "PYTHONPYCACHEPREFIX": str(temporary_root / "pycache"),
        }
    )
    pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = str(temporary_root.parent.parent / "src")
    if pythonpath:
        environment["PYTHONPATH"] += os.pathsep + pythonpath
    return environment


def _worker_group_options() -> dict[str, object]:
    """Return platform-specific options that isolate a worker process group."""

    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_worker(process: subprocess.Popen[bytes]) -> None:
    """Force-terminate and reap one expired worker and its process group/tree."""

    if process.poll() is not None:
        return

    containment_error: BaseException | None = None
    if IS_WINDOWS:
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=WORKER_TERMINATION_TIMEOUT_SECONDS,
            )
            if result.returncode:
                containment_error = NotebookCheckError(
                    f"taskkill exited with status {result.returncode}"
                )
        except (OSError, subprocess.TimeoutExpired) as error:
            containment_error = error
        if containment_error is not None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
    else:
        # nbclient handles SIGTERM by starting kernel cleanup. Cleanup is the
        # phase being contained here, so an expired worker must be killed.
        # Jupyter's parent-death handling remains responsible for its
        # separately sessioned kernel once this owning worker disappears.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    try:
        process.wait(timeout=WORKER_TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=WORKER_TERMINATION_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            raise NotebookCheckError(
                f"worker process {process.pid} could not be reaped after forced "
                "termination"
            ) from error

    if containment_error is not None:
        raise NotebookCheckError(
            f"could not confirm termination of Windows worker tree {process.pid}; "
            "the direct worker was force-terminated"
        ) from containment_error


def _run_worker(
    path: Path,
    *,
    working_dir: Path,
    runtime_root: Path,
    wall_timeout: float = WORKER_TIMEOUT_SECONDS,
) -> None:
    """Run one temporary notebook in a bounded isolated child process."""

    runtime_root.mkdir(parents=True, exist_ok=True)
    # The standard CLI owns every Jupyter object and cleanup handler. The
    # supervisor only waits for and, when necessary, terminates this process.
    command = [
        sys.executable,
        "-m",
        "jupyter",
        "execute",
        f"--timeout={CELL_TIMEOUT_SECONDS}",
        f"--startup_timeout={KERNEL_STARTUP_TIMEOUT_SECONDS}",
        "--Application.log_level=INFO",
        "--inplace",
        str(path),
    ]
    process = subprocess.Popen(
        command,
        cwd=working_dir,
        env=_worker_environment(runtime_root),
        **_worker_group_options(),
    )
    try:
        returncode = process.wait(timeout=wall_timeout)
    except subprocess.TimeoutExpired as error:
        try:
            _terminate_worker(process)
        except NotebookCheckError as containment_error:
            raise NotebookCheckError(
                f"{path.name}: worker exceeded the {wall_timeout:g}-second "
                "wall-clock timeout and forced containment also failed: "
                f"{containment_error}"
            ) from error
        raise NotebookCheckError(
            f"{path.name}: worker exceeded the {wall_timeout:g}-second "
            "wall-clock timeout during Jupyter kernel startup, cell execution, "
            "kernel cleanup, or process exit; worker containment completed"
        ) from error
    if returncode:
        raise NotebookCheckError(
            f"{path.name}: Jupyter startup, execution, or cleanup failed; "
            f"worker exited with status {returncode}"
        )


def smoke_execute(paths: list[Path]) -> int:
    """Execute selected notebooks only after copying them into a temporary tree."""

    notebooks = _resolve_notebooks(paths)
    deadline = time.monotonic() + CHECK_TIMEOUT_SECONDS
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

        for index, notebook in enumerate(copied, start=1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise NotebookCheckError(
                    f"{notebook.name}: the complete notebook smoke check exceeded "
                    f"its {CHECK_TIMEOUT_SECONDS}-second wall-clock timeout before "
                    "this worker could start"
                )
            print(
                f"[{index}/{len(copied)}] {notebook.name}: phase=Jupyter "
                "startup/execution/cleanup",
                flush=True,
            )
            _run_worker(
                notebook,
                working_dir=temporary_notebooks,
                runtime_root=temporary_root / "runtime" / notebook.stem,
                wall_timeout=min(WORKER_TIMEOUT_SECONDS, remaining),
            )
            print(
                f"[{index}/{len(copied)}] {notebook.name}: phase=process exit; "
                "worker exited cleanly",
                flush=True,
            )

    print(
        f"Smoke-executed {len(notebooks)} notebook(s) in temporary kernels.",
        flush=True,
    )
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
