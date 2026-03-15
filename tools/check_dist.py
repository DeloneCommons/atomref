"""Verify that built distributions contain the project's key files."""

from __future__ import annotations

import argparse
from pathlib import Path
import tarfile
import zipfile


REQUIRED_WHEEL_MEMBERS = {
    "atomref/data/periodic_table.csv",
    "atomref/data/covalent.csv",
    "atomref/data/van_der_waals.csv",
    "atomref/data/registry.json",
    "atomref/py.typed",
}

REQUIRED_SDIST_SUFFIXES = {
    "src/atomref/data/periodic_table.csv",
    "src/atomref/data/covalent.csv",
    "src/atomref/data/van_der_waals.csv",
    "src/atomref/data/registry.json",
    "src/atomref/py.typed",
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "notebooks/01-quickstart.ipynb",
    "notebooks/02-policies-and-assessment.ipynb",
    "notebooks/03-custom-sets-and-discovery.ipynb",
    "docs/notebooks/01-quickstart.md",
    "docs/notebooks/02-policies-and-assessment.md",
    "docs/notebooks/03-custom-sets-and-discovery.md",
    "tools/check_notebooks.py",
    "tools/export_notebooks.py",
    "tools/README.md",
}


class DistCheckError(RuntimeError):
    """Raised when a built distribution is missing required members."""


def _assert_members_present(
    actual: set[str],
    required: set[str],
    *,
    label: str,
) -> None:
    """Raise when ``required`` contains members not present in ``actual``."""

    missing = sorted(required - actual)
    if missing:
        joined = ", ".join(missing)
        raise DistCheckError(f"{label} is missing required members: {joined}")


def _members_matching_suffixes(actual: set[str], suffixes: set[str]) -> set[str]:
    """Return suffixes that match at least one member name from ``actual``."""

    matched: set[str] = set()
    for suffix in suffixes:
        if any(name.endswith(suffix) for name in actual):
            matched.add(suffix)
    return matched


def check_wheel(path: Path) -> None:
    """Validate the contents of one built wheel."""

    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    matched = {
        member
        for member in REQUIRED_WHEEL_MEMBERS
        if any(name.endswith(member) for name in names)
    }
    _assert_members_present(matched, REQUIRED_WHEEL_MEMBERS, label=path.name)


def check_sdist(path: Path) -> None:
    """Validate the contents of one built source distribution."""

    with tarfile.open(path, "r:gz") as tf:
        names = {member.name for member in tf.getmembers()}
    matched = _members_matching_suffixes(names, REQUIRED_SDIST_SUFFIXES)
    _assert_members_present(matched, REQUIRED_SDIST_SUFFIXES, label=path.name)


def main() -> None:
    """Validate wheel and sdist artifacts found in a distribution directory."""

    parser = argparse.ArgumentParser()
    parser.add_argument("dist_dir", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()

    dist_dir = args.dist_dir
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if not wheels:
        raise DistCheckError(f"no wheel files found in {dist_dir}")
    if not sdists:
        raise DistCheckError(f"no source distributions found in {dist_dir}")

    for wheel in wheels:
        check_wheel(wheel)
    for sdist in sdists:
        check_sdist(sdist)


if __name__ == "__main__":
    main()
