#!/usr/bin/env python3
"""Run the full release-preparation checks for the repository.

This helper is intended for local release preparation. It runs the same checks
that are exercised separately in CI, then builds source and wheel artifacts,
validates them, and smoke-tests the built wheel in an isolated virtual
environment for each supported user installation.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
MKDOCS_ENV = {"NO_MKDOCS_2_WARNING": "true"}
NOTEBOOK_CHECK_TIMEOUT_SECONDS = 16 * 60


def _run(
    *args: str,
    cwd: Path = REPO_ROOT,
    extra_env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> None:
    """Run one subprocess command in the selected working directory."""

    print(f"+ [cwd={cwd}]", " ".join(args), flush=True)
    environment = None
    if extra_env is not None:
        environment = os.environ.copy()
        environment.update(extra_env)
    subprocess.run(
        args,
        cwd=cwd,
        env=environment,
        check=True,
        timeout=timeout,
    )


def _build_docs() -> None:
    """Build strict docs without Material's inapplicable MkDocs 2 banner."""

    _run("mkdocs", "build", "--strict", extra_env=MKDOCS_ENV)


def _check_types() -> None:
    """Run mypy with the same Python environment as this release check."""

    _run(sys.executable, "-m", "mypy", "src/atomref")


def _check_notebooks() -> None:
    """Run the internally bounded checker with a final release-gate timeout."""

    _run(
        sys.executable,
        "tools/check_notebooks.py",
        timeout=NOTEBOOK_CHECK_TIMEOUT_SECONDS,
    )


def _fresh_build_dirs() -> None:
    """Remove build artifacts from previous runs."""

    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


def _assert_clean_worktree() -> None:
    """Require artifacts to be built from the exact committed source tree."""

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise RuntimeError(
            "release artifacts must be built from a clean committed worktree"
        )


def _normalize_source_modes(source_root: Path) -> None:
    """Set conventional modes in a disposable source-archive extraction."""

    source_root.chmod(0o755)
    for path in source_root.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            path.chmod(0o644)


def _extract_source_archive(
    source_archive: tarfile.TarFile,
    source_root: Path,
) -> None:
    """Extract a trusted Git archive with an explicit safe filter when available."""

    if hasattr(tarfile, "data_filter"):
        source_archive.extractall(source_root, filter="data")
    else:  # pragma: no cover - extraction filters were added after Python 3.10
        source_archive.extractall(source_root)


def _build_from_committed_head() -> None:
    """Build artifacts from a normalized temporary extraction of ``HEAD``."""

    _assert_clean_worktree()
    with tempfile.TemporaryDirectory(prefix="atomref-release-source-") as tmp:
        temporary_root = Path(tmp)
        archive = temporary_root / "atomref-head.tar"
        source_root = temporary_root / "source"
        source_root.mkdir()
        _run(
            "git",
            "archive",
            "--format=tar",
            f"--output={archive}",
            "HEAD",
        )
        with tarfile.open(archive, mode="r:") as source_archive:
            _extract_source_archive(source_archive, source_root)
        _normalize_source_modes(source_root)
        _run(
            sys.executable,
            "-m",
            "build",
            "--outdir",
            str(DIST_DIR),
            cwd=source_root,
        )


def main() -> int:
    """Run lint, tests, docs, build, metadata, and artifact checks."""

    parser = argparse.ArgumentParser(
        description="Run the full release-preparation checks for the repository.",
    )
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        help="skip the strict MkDocs build step",
    )
    parser.add_argument(
        "--skip-install-checks",
        action="store_true",
        help="skip clean base, notebooks, and all wheel installation checks",
    )
    args = parser.parse_args()

    _assert_clean_worktree()
    _run("flake8", "src", "tests", "tools")
    _check_types()
    _run("cffconvert", "--validate")
    _run(sys.executable, "tools/check_registry.py")
    _check_notebooks()
    _run(sys.executable, "tools/gen_readme.py", "--check")
    _run(sys.executable, "-m", "pytest", "-q")
    if not args.skip_docs:
        _build_docs()

    _fresh_build_dirs()
    _build_from_committed_head()
    _run(sys.executable, "-m", "twine", "check", "dist/*")
    dist_check = [sys.executable, "tools/check_dist.py", "dist"]
    if not args.skip_install_checks:
        dist_check.append("--check-installs")
    _run(*dist_check)
    _assert_clean_worktree()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
