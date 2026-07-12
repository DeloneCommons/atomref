"""Verify that built distributions contain the project's key files."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import tarfile
import zipfile


REQUIRED_WHEEL_MEMBERS = {
    "atomref/data/periodic_table.csv",
    "atomref/data/covalent.csv",
    "atomref/data/proatomic_density_neutral.zip",
    "atomref/data/van_der_waals.csv",
    "atomref/data/registry.json",
    "atomref/py.typed",
    "dist-info/licenses/NOTICE.md",
}

REQUIRED_SDIST_SUFFIXES = {
    "src/atomref/data/periodic_table.csv",
    "src/atomref/data/covalent.csv",
    "src/atomref/data/proatomic_density_neutral.zip",
    "src/atomref/data/van_der_waals.csv",
    "src/atomref/data/registry.json",
    "src/atomref/py.typed",
    "README.md",
    "CHANGELOG.md",
    "DEV_PLAN.md",
    "LICENSE",
    "NOTICE.md",
    "pyproject.toml",
    "notebooks/01-quickstart.ipynb",
    "notebooks/02-policies-and-assessment.ipynb",
    "notebooks/03-custom-sets-and-discovery.ipynb",
    "docs/notebooks/01-quickstart.md",
    "docs/notebooks/02-policies-and-assessment.md",
    "docs/notebooks/03-custom-sets-and-discovery.md",
    "tools/build_proatomic_density_snapshot.py",
    "tools/check_notebooks.py",
    "tools/export_notebooks.py",
    "tools/gen_readme.py",
    "tools/release_check.py",
    "tools/README.md",
}

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
        names = {member.name for member in tf.getmembers()}
        matched = _members_matching_suffixes(names, REQUIRED_SDIST_SUFFIXES)
        _assert_members_present(matched, REQUIRED_SDIST_SUFFIXES, label=path.name)

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
