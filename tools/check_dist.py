"""Verify that built distributions contain the project's key files."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import io
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


REQUIRED_WHEEL_MEMBERS = {
    "atomref/data/periodic_table.csv",
    "atomref/data/covalent.csv",
    "atomref/data/proatomic_density_neutral.zip",
    "atomref/data/van_der_waals.csv",
    "atomref/data/xh_bond_length.csv",
    "atomref/data/registry.json",
    "atomref/py.typed",
    "dist-info/METADATA",
    "dist-info/licenses/COPYING",
    "dist-info/licenses/LICENSE",
    "dist-info/licenses/NOTICE.md",
}

EXPECTED_SDIST_NOTEBOOKS = {
    "docs/notebooks/01-quickstart.ipynb",
    "docs/notebooks/02-policies-and-assessment.ipynb",
    "docs/notebooks/03-custom-sets-and-discovery.ipynb",
    "docs/notebooks/04-ias-method-selection-study.ipynb",
    "docs/notebooks/05-proatomic-density-and-ias.ipynb",
}

REQUIRED_SDIST_SUFFIXES = {
    "src/atomref/data/periodic_table.csv",
    "src/atomref/data/covalent.csv",
    "src/atomref/data/proatomic_density_neutral.zip",
    "src/atomref/data/van_der_waals.csv",
    "src/atomref/data/xh_bond_length.csv",
    "src/atomref/data/registry.json",
    "src/atomref/py.typed",
    "README.md",
    "CHANGELOG.md",
    "DEV_PLAN.md",
    "CITATION.cff",
    "COPYING",
    "LICENSE",
    "NOTICE.md",
    "pyproject.toml",
    ".flake8",
    "docs/index.md",
    *EXPECTED_SDIST_NOTEBOOKS,
    "docs/guide/notebooks.md",
    "docs/guide/proatomic_density.md",
    "docs/dev/architecture.md",
    "docs/dev/data_curation.md",
    "docs/dev/ias_method_selection.md",
    "docs/api/index.md",
    "docs/api/proatoms.md",
    "docs/assets/ias-method-study/c-o-method-comparison.png",
    "docs/assets/ias-method-study/cutoff-radii.png",
    "docs/assets/ias-method-study/li-li-symmetry.png",
    "tools/build_proatomic_density_snapshot.py",
    "tools/check_notebooks.py",
    "tools/check_registry.py",
    "tools/check_dist.py",
    "tools/gen_readme.py",
    "tools/release_check.py",
    "tools/README.md",
}

FORBIDDEN_SDIST_MEMBERS = {
    "docs/dev/dev_plan.md",
    "tools/export_notebooks.py",
}

EXPECTED_VERSION = "0.2.1"
EXPECTED_REGULAR_FILE_MODE = 0o644
COMPONENT_EXTRAS = {"test", "notebooks", "docs", "dev"}
REQUIRED_EXTRAS = COMPONENT_EXTRAS | {"all"}
EXTRA_MARKER = re.compile(r"\bextra\s*==\s*(['\"])([-a-zA-Z0-9_.]+)\1")

NOTEBOOKS_IMPORTS = """\
import ipykernel
import matplotlib
import mkdocs
import mkdocs_jupyter
import nbclient
import nbformat
"""

ALL_IMPORTS = f"""\
{NOTEBOOKS_IMPORTS}
import build
import flake8
import material
import mkdocstrings
import mkdocstrings_handlers.python
import pymdownx
import pytest
import twine
try:
    import tomllib
except ModuleNotFoundError:
    import tomli
"""

EXTRA_IMPORTS = {
    "notebooks": NOTEBOOKS_IMPORTS,
    "all": ALL_IMPORTS,
}

API_SMOKE = """\
import atomref as ar

assert ar.__version__ == "0.2.1"
assert ar.get_covalent_radius("C") == 0.76
assert ar.get_vdw_radius("C") == 1.77
assert ar.get_xh_bond_length("N") is not None
assert "atomic_radius" in ar.list_quantities()
assert "rahm2016" in ar.list_dataset_ids(
    "atomic_radius", usage_role="support"
)
ref = ar.DatasetRef(
    "proatomic_density",
    "pbe0_sfx2c_dyallv4z_h-lr_neutral_v2",
)
dataset = ar.get_builtin_set(ref)
assert dataset.get("O") is not None
rho = ar.get_proatomic_density(
    "O",
    0.75,
    radius_unit="angstrom",
    density_unit="electron/bohr^3",
)
assert rho is not None and rho > 0
boundary = ar.estimate_proatomic_boundary("C", "O", 1.43)
assert boundary.position_from_a is not None
minimum = ar.estimate_promolecular_density_minimum("C", "O", 1.43)
assert minimum.requested_mode == "minimum"
selected = ar.estimate_ias_position("C", "O", 1.43, mode="boundary")
assert selected == boundary
"""

ATTRIBUTION_MARKERS = {
    "CC BY 4.0",
    "10.5281/zenodo.21291021",
    "10.5281/zenodo.21291022",
    "pbe0_sfx2c_dyallv4z_h-lr_spherical_v2",
}

PROATOMIC_SNAPSHOT_MEMBER = "proatomic_density_neutral.csv"
EXPECTED_PROATOMIC_SNAPSHOT_SHA256 = (
    "1ec0318c8bc8f6e71eb3125cf1d4387e4593d7bee8ff5ee5270fbcc32c70ec6b"
)
EXPECTED_PROATOMIC_CSV_SHA256 = (
    "8478da862233c8874e36d65bb5eb762cdb9cbcb0e0278733c0f425ae00c2dcfe"
)
REPO_ROOT = Path(__file__).resolve().parents[1]


class DistCheckError(RuntimeError):
    """Raised when a built distribution violates the release contract."""


def _assert_regular_file_modes(
    members: list[tuple[str, int]],
    *,
    label: str,
) -> None:
    """Require conventional non-executable modes for regular payload files."""

    unexpected = [
        (name, stat.S_IMODE(mode))
        for name, mode in members
        if stat.S_IMODE(mode) != EXPECTED_REGULAR_FILE_MODE
    ]
    if unexpected:
        details = ", ".join(
            f"{name}={mode:04o}" for name, mode in unexpected
        )
        raise DistCheckError(
            f"{label} regular files must use mode "
            f"{EXPECTED_REGULAR_FILE_MODE:04o}: {details}"
        )


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


def _sdist_relative_members(actual: set[str], *, label: str) -> set[str]:
    """Remove the generated source-distribution root from member names."""

    roots = {name.split("/", 1)[0] for name in actual if name}
    if len(roots) != 1:
        raise DistCheckError(
            f"{label} must contain exactly one generated root directory"
        )
    root = next(iter(roots))
    prefix = f"{root}/"
    return {name[len(prefix) :] for name in actual if name.startswith(prefix)}


def _assert_sdist_layout(actual: set[str], *, label: str) -> None:
    """Reject duplicate notebooks and obsolete generated documentation paths."""

    relative = _sdist_relative_members(actual, label=label)
    obsolete = {
        name
        for name in relative
        if name in FORBIDDEN_SDIST_MEMBERS
        or (
            name.startswith("docs/notebooks/")
            and name.endswith(".md")
        )
        or ".ipynb_checkpoints/" in name
    }
    if obsolete:
        joined = ", ".join(sorted(obsolete))
        raise DistCheckError(f"{label} contains obsolete members: {joined}")

    notebooks = {name for name in relative if name.endswith(".ipynb")}
    if notebooks != EXPECTED_SDIST_NOTEBOOKS:
        missing = sorted(EXPECTED_SDIST_NOTEBOOKS - notebooks)
        unexpected = sorted(notebooks - EXPECTED_SDIST_NOTEBOOKS)
        details: list[str] = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise DistCheckError(
            f"{label} must contain exactly one source for each notebook "
            f"({'; '.join(details)})"
        )


def _member_matching_suffix(
    actual: set[str],
    suffix: str,
    *,
    label: str,
) -> str:
    """Return the unique archive member ending in ``suffix``."""

    matches = sorted(name for name in actual if name.endswith(suffix))
    if len(matches) != 1:
        raise DistCheckError(
            f"{label} must contain exactly one member ending in {suffix!r}"
        )
    return matches[0]


def _sdist_root_member(actual: set[str], filename: str, *, label: str) -> str:
    """Return one file directly below the sdist's generated root directory."""

    matches = sorted(
        name
        for name in actual
        if name.count("/") == 1 and name.rsplit("/", 1)[-1] == filename
    )
    if len(matches) != 1:
        raise DistCheckError(
            f"{label} must contain exactly one root-level {filename!r}"
        )
    return matches[0]


def _assert_attribution(text: str, *, member: str, label: str) -> None:
    """Raise when a packaged metadata file omits required data attribution."""

    missing = sorted(marker for marker in ATTRIBUTION_MARKERS if marker not in text)
    if missing:
        joined = ", ".join(missing)
        raise DistCheckError(
            f"{label} member {member!r} is missing attribution markers: {joined}"
        )


def _decode_utf8(payload: bytes, *, member: str, label: str) -> str:
    """Decode one distribution member as UTF-8 with a focused error."""

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DistCheckError(
            f"{label} member {member!r} is not valid UTF-8"
        ) from exc


def _assert_wheel_metadata(payload: bytes, *, member: str, label: str) -> None:
    """Validate release version, empty core requirements, and extras."""

    try:
        metadata = BytesParser(policy=policy.default).parsebytes(payload)
    except (TypeError, ValueError) as exc:
        raise DistCheckError(
            f"{label} member {member!r} is not valid package metadata"
        ) from exc

    if metadata.get("Name") != "atomref":
        raise DistCheckError(f"{label} has unexpected project metadata name")
    if metadata.get("Version") != EXPECTED_VERSION:
        raise DistCheckError(
            f"{label} has unexpected version {metadata.get('Version')!r}; "
            f"expected {EXPECTED_VERSION!r}"
        )

    provided_extras = set(metadata.get_all("Provides-Extra", []))
    missing_extras = REQUIRED_EXTRAS - provided_extras
    if missing_extras:
        joined = ", ".join(sorted(missing_extras))
        raise DistCheckError(f"{label} is missing extras: {joined}")

    requirements = metadata.get_all("Requires-Dist", [])
    unconditional = [
        requirement
        for requirement in requirements
        if not EXTRA_MARKER.findall(requirement)
    ]
    if unconditional:
        joined = ", ".join(unconditional)
        raise DistCheckError(
            f"{label} must not declare runtime requirements: {joined}"
        )

    by_extra: dict[str, set[str]] = {
        extra: set() for extra in REQUIRED_EXTRAS
    }
    for requirement in requirements:
        requirement_text = requirement.split(";", 1)[0].strip()
        extras = {match[1] for match in EXTRA_MARKER.findall(requirement)}
        for extra in REQUIRED_EXTRAS & extras:
            by_extra[extra].add(requirement_text)

    empty_extras = sorted(
        extra for extra in COMPONENT_EXTRAS if not by_extra[extra]
    )
    if empty_extras:
        joined = ", ".join(empty_extras)
        raise DistCheckError(f"{label} has empty component extras: {joined}")

    expected_all = set().union(
        *(by_extra[extra] for extra in COMPONENT_EXTRAS)
    )
    if by_extra["all"] != expected_all:
        missing = sorted(expected_all - by_extra["all"])
        unexpected = sorted(by_extra["all"] - expected_all)
        details: list[str] = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise DistCheckError(
            f"{label} all extra must equal the union of test, notebooks, "
            f"docs, and dev ({'; '.join(details)})"
        )


def _assert_proatomic_snapshot(payload: bytes, *, member: str, label: str) -> None:
    """Require the exact pinned consumer ZIP and scientific CSV fingerprints."""

    archive_digest = hashlib.sha256(payload).hexdigest()
    if archive_digest != EXPECTED_PROATOMIC_SNAPSHOT_SHA256:
        raise DistCheckError(
            f"{label} member {member!r} has unexpected proatomic snapshot "
            f"SHA-256: {archive_digest}"
        )

    try:
        with zipfile.ZipFile(io.BytesIO(payload), mode="r") as snapshot:
            members = snapshot.infolist()
            if len(members) != 1 or members[0].filename != PROATOMIC_SNAPSHOT_MEMBER:
                raise DistCheckError(
                    f"{label} member {member!r} has an invalid nested snapshot"
                )
            csv_payload = snapshot.read(members[0])
    except (RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise DistCheckError(
            f"{label} member {member!r} is not a valid snapshot ZIP"
        ) from exc

    csv_digest = hashlib.sha256(csv_payload).hexdigest()
    if csv_digest != EXPECTED_PROATOMIC_CSV_SHA256:
        raise DistCheckError(
            f"{label} member {member!r} has unexpected inner CSV SHA-256: "
            f"{csv_digest}"
        )


def check_wheel(path: Path) -> None:
    """Validate the contents of one built wheel."""

    with zipfile.ZipFile(path) as zf:
        _assert_regular_file_modes(
            [
                (member.filename, member.external_attr >> 16)
                for member in zf.infolist()
                if not member.is_dir()
            ],
            label=path.name,
        )
        names = set(zf.namelist())
        matched = _members_matching_suffixes(names, REQUIRED_WHEEL_MEMBERS)
        _assert_members_present(matched, REQUIRED_WHEEL_MEMBERS, label=path.name)

        snapshot_member = _member_matching_suffix(
            names,
            "atomref/data/proatomic_density_neutral.zip",
            label=path.name,
        )
        _assert_proatomic_snapshot(
            zf.read(snapshot_member),
            member=snapshot_member,
            label=path.name,
        )

        metadata_member = _member_matching_suffix(
            names,
            "dist-info/METADATA",
            label=path.name,
        )
        _assert_wheel_metadata(
            zf.read(metadata_member),
            member=metadata_member,
            label=path.name,
        )

        for suffix in (
            "atomref/data/registry.json",
            "dist-info/licenses/NOTICE.md",
        ):
            member = _member_matching_suffix(names, suffix, label=path.name)
            text = _decode_utf8(zf.read(member), member=member, label=path.name)
            _assert_attribution(text, member=member, label=path.name)


def check_sdist(path: Path) -> None:
    """Validate the contents of one built source distribution."""

    with tarfile.open(path, "r:gz") as tf:
        members = tf.getmembers()
        _assert_regular_file_modes(
            [
                (member.name, member.mode)
                for member in members
                if member.isreg()
            ],
            label=path.name,
        )
        names = {member.name for member in members}
        matched = _members_matching_suffixes(names, REQUIRED_SDIST_SUFFIXES)
        _assert_members_present(matched, REQUIRED_SDIST_SUFFIXES, label=path.name)
        _assert_sdist_layout(names, label=path.name)

        for filename in ("README.md", "CITATION.cff"):
            root_member = _sdist_root_member(names, filename, label=path.name)
            root_file = tf.extractfile(root_member)
            if root_file is None:
                raise DistCheckError(
                    f"{path.name} member {root_member!r} is not a regular file"
                )
            if root_file.read() != (REPO_ROOT / filename).read_bytes():
                raise DistCheckError(
                    f"{path.name} member {root_member!r} does not exactly "
                    f"match the source {filename}"
                )

        snapshot_member = _member_matching_suffix(
            names,
            "src/atomref/data/proatomic_density_neutral.zip",
            label=path.name,
        )
        snapshot_file = tf.extractfile(snapshot_member)
        if snapshot_file is None:
            raise DistCheckError(
                f"{path.name} member {snapshot_member!r} is not a regular file"
            )
        _assert_proatomic_snapshot(
            snapshot_file.read(),
            member=snapshot_member,
            label=path.name,
        )

        for suffix in ("src/atomref/data/registry.json", "NOTICE.md"):
            member = _member_matching_suffix(names, suffix, label=path.name)
            extracted = tf.extractfile(member)
            if extracted is None:
                raise DistCheckError(
                    f"{path.name} member {member!r} is not a regular file"
                )
            text = _decode_utf8(
                extracted.read(),
                member=member,
                label=path.name,
            )
            _assert_attribution(text, member=member, label=path.name)


def _venv_python(env_dir: Path) -> Path:
    """Return the Python executable created in ``env_dir``."""

    bindir = "Scripts" if sys.platform.startswith("win") else "bin"
    return env_dir / bindir / "python"


def _run_checked(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    label: str,
) -> None:
    """Run one clean-install subprocess with a focused failure message."""

    display_args = list(args)
    if "-c" in display_args:
        code_index = display_args.index("-c") + 1
        if code_index < len(display_args):
            display_args[code_index] = "<documented API smoke example>"
    print("+", " ".join(display_args))
    try:
        subprocess.run(args, cwd=cwd, env=env, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DistCheckError(f"{label} clean-install check failed") from exc


def check_clean_installations(wheel: Path) -> None:
    """Install base, notebooks, and all variants in clean environments."""

    wheel = wheel.resolve()
    if not wheel.is_file():
        raise DistCheckError(f"wheel does not exist: {wheel}")

    clean_env = os.environ.copy()
    clean_env.pop("PYTHONHOME", None)
    clean_env.pop("PYTHONPATH", None)

    with tempfile.TemporaryDirectory(prefix="atomref-artifact-installs-") as tmp:
        root = Path(tmp)
        outside_checkout = root / "outside-checkout"
        outside_checkout.mkdir()

        for extra in (None, "notebooks", "all"):
            label = "base" if extra is None else extra
            env_dir = root / f"venv-{label}"
            venv.EnvBuilder(with_pip=True).create(env_dir)
            python = _venv_python(env_dir)

            if extra is None:
                install_target = str(wheel)
            else:
                install_target = f"atomref[{extra}] @ {wheel.as_uri()}"

            install = [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
            ]
            if extra is None:
                install.append("--no-deps")
            install.append(install_target)
            _run_checked(
                install,
                cwd=outside_checkout,
                env=clean_env,
                label=label,
            )
            _run_checked(
                [str(python), "-m", "pip", "check"],
                cwd=outside_checkout,
                env=clean_env,
                label=label,
            )

            smoke = API_SMOKE
            if extra is not None:
                smoke = f"{EXTRA_IMPORTS[extra]}\n{smoke}"
            _run_checked(
                [str(python), "-c", smoke],
                cwd=outside_checkout,
                env=clean_env,
                label=label,
            )

            print(f"Validated clean {label} installation from {wheel.name}.")


def main() -> None:
    """Validate wheel and sdist artifacts found in a distribution directory."""

    parser = argparse.ArgumentParser()
    parser.add_argument("dist_dir", type=Path, nargs="?", default=Path("dist"))
    parser.add_argument(
        "--check-installs",
        action="store_true",
        help=(
            "install the built wheel as base, notebooks, and all variants in "
            "separate clean virtual environments"
        ),
    )
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
    if args.check_installs:
        if len(wheels) != 1:
            raise DistCheckError(
                "clean-install checks require exactly one wheel in the "
                "distribution directory"
            )
        check_clean_installations(wheels[0])


if __name__ == "__main__":
    main()
