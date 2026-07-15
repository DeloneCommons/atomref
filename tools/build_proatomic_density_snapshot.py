#!/usr/bin/env python3
"""Build the deterministic neutral H-Lr proatomic-density snapshot.

This maintainer-only tool consumes the pinned local atomref-proatoms 2.0.0
dataset.  It performs no network access and keeps the complete upstream source
outside the atomref package.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Mapping
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from atomref.elements import iter_elements  # noqa: E402


SOURCE_DATASET_ID = "pbe0_sfx2c_dyallv4z_h-lr_spherical_v2"
SOURCE_DATA_VERSION = "2.0.0"
SOURCE_SCHEMA_VERSION = "atomref.proatoms.profile_dataset.v1"
PROFILES_SHA256 = "b5520ab009542d52098dd6dbb920966d8d13377a4a5004f584a7bd15cd41c299"
METADATA_SHA256 = "32c833ca69fa0f7eb9ed32841aafc638123ff872861e636156610e417fc4c514"
BASIS_ID = "dyall-v4z"
BASIS_SHA256 = "0ee543855f8b1e7fbe9868d4abb844d8e8cc8b8c2694067b2b40de014bb4be94"

OUTPUT_PATH = REPO_ROOT / "src" / "atomref" / "data" / (
    "proatomic_density_neutral.zip"
)
ARCHIVE_MEMBER = "proatomic_density_neutral.csv"
RADIUS_COLUMN = "r_bohr"
PUBLIC_MAX_RADIUS_BOHR = 20.0
EXPECTED_LAST_BELOW_BOHR = 19.865456344881434
EXPECTED_BRACKET_BOHR = 20.1644204667093
EXPECTED_RETAINED_ROWS = 1127
EXPECTED_Z = tuple(range(1, 104))

# Scale-free tolerance used only when rejecting numerical upward noise.  The
# pinned table is strictly decreasing, and its smallest relative decrease is
# about 4.20e-12, more than four times this tolerance.
MONOTONIC_REL_TOL = 1.0e-12


class SnapshotError(RuntimeError):
    """Raised when pinned input or generated output violates the contract."""


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Generated snapshot bytes and concise validation facts."""

    csv_bytes: bytes
    archive_bytes: bytes
    selected_profiles: int
    retained_rows: int
    last_below_bohr: float
    bracket_bohr: float


def _sha256(data: bytes) -> str:
    """Return the lowercase SHA-256 hex digest for ``data``."""

    return hashlib.sha256(data).hexdigest()


def _read_pinned(path: Path, *, expected_sha256: str, label: str) -> bytes:
    """Read one source file and reject any byte-level identity mismatch."""

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read {label}: {path}") from exc
    actual = _sha256(data)
    if actual != expected_sha256:
        raise SnapshotError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, got {actual}"
        )
    return data


def _mapping(value: object, *, what: str) -> Mapping[str, object]:
    """Require a string-keyed JSON object."""

    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise SnapshotError(f"invalid metadata: {what} must be an object")
    return value


def _integer(value: object, *, what: str) -> int:
    """Require a JSON integer while rejecting booleans."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise SnapshotError(f"invalid metadata: {what} must be an integer")
    return value


def _expect(mapping: Mapping[str, object], key: str, expected: object) -> None:
    """Require one exact metadata identity value."""

    actual = mapping.get(key)
    if actual != expected:
        raise SnapshotError(
            f"invalid metadata {key!r}: expected {expected!r}, got {actual!r}"
        )


def _load_metadata(data: bytes) -> Mapping[str, object]:
    """Parse and validate pinned dataset and scientific identity metadata."""

    try:
        raw = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError("metadata.json is not valid UTF-8 JSON") from exc
    metadata = _mapping(raw, what="top level")

    expected_top_level = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "profile_data_version": SOURCE_DATA_VERSION,
        "dataset_id": SOURCE_DATASET_ID,
        "basis_id": BASIS_ID,
        "basis_sha256": BASIS_SHA256,
        "density_model": (
            "self_consistent_fractional_occupation_spherical_uks"
        ),
    }
    for key, expected in expected_top_level.items():
        _expect(metadata, key, expected)

    method = _mapping(metadata.get("method"), what="method")
    for key, expected in {
        "scf_type": "UKS",
        "xc": "PBE0",
        "relativity": "sf-X2C-1e",
        "spherical_basis": True,
        "basis_id": BASIS_ID,
        "basis_sha256": BASIS_SHA256,
    }.items():
        _expect(method, key, expected)

    units = _mapping(metadata.get("units"), what="units")
    _expect(units, "r", "bohr")
    _expect(units, "rho", "electron/bohr^3")

    profile_grid = _mapping(metadata.get("profile_grid"), what="profile_grid")
    for key, expected in {
        "type": "log",
        "r_min_bohr": 1.0e-6,
        "r_max_bohr": 60.0,
        "n": 1200,
    }.items():
        _expect(profile_grid, key, expected)
    return metadata


def _element_symbols_by_z() -> dict[int, str]:
    """Return the H-Lr symbol mapping from atomref's element registry."""

    symbols = {
        element.z: element.symbol
        for element in iter_elements()
        if element.z in EXPECTED_Z
    }
    if tuple(sorted(symbols)) != EXPECTED_Z:
        raise SnapshotError("atomref element registry does not cover exact Z=1..103")
    return symbols


def _select_neutral_columns(
    metadata: Mapping[str, object],
) -> tuple[tuple[int, str], ...]:
    """Select exactly one metadata-declared neutral CSV column per H-Lr Z."""

    states = _mapping(metadata.get("states"), what="states")
    columns = _mapping(metadata.get("columns"), what="columns")
    symbols_by_z = _element_symbols_by_z()

    selected_states: dict[int, tuple[str, Mapping[str, object]]] = {}
    for state_id, value in states.items():
        state = _mapping(value, what=f"state {state_id!r}")
        charge = _integer(state.get("charge"), what=f"state {state_id!r} charge")
        if charge != 0:
            continue
        z = _integer(state.get("z"), what=f"state {state_id!r} z")
        if z in selected_states:
            other = selected_states[z][0]
            raise SnapshotError(
                f"multiple neutral states for Z={z}: {other!r} and {state_id!r}"
            )
        selected_states[z] = (state_id, state)

    if tuple(sorted(selected_states)) != EXPECTED_Z:
        actual = tuple(sorted(selected_states))
        raise SnapshotError(
            f"neutral-state coverage must be exact Z=1..103, got {actual!r}"
        )

    columns_by_state: dict[str, list[tuple[str, Mapping[str, object]]]] = {}
    for column_name, value in columns.items():
        column = _mapping(value, what=f"column {column_name!r}")
        state_id = column.get("state_id")
        if not isinstance(state_id, str) or not state_id:
            raise SnapshotError(
                f"invalid metadata: column {column_name!r} has no state_id"
            )
        columns_by_state.setdefault(state_id, []).append((column_name, column))

    selected_columns: list[tuple[int, str]] = []
    for z in EXPECTED_Z:
        state_id, state = selected_states[z]
        matches = columns_by_state.get(state_id, [])
        if len(matches) != 1:
            raise SnapshotError(
                f"selected state {state_id!r} maps to {len(matches)} CSV columns"
            )
        column_name, column = matches[0]
        expected_column = f"rho_e_bohr3__{state_id}"
        if column_name != expected_column:
            raise SnapshotError(
                f"selected state {state_id!r} uses unexpected column {column_name!r}"
            )

        for key in ("symbol", "z", "charge", "electron_count", "multiplicity"):
            if state.get(key) != column.get(key):
                raise SnapshotError(
                    f"state/column metadata disagree for {state_id!r}: {key}"
                )
        if state.get("symbol") != symbols_by_z[z]:
            raise SnapshotError(
                f"selected symbol for Z={z} disagrees with atomref element registry"
            )
        electron_count = _integer(
            state.get("electron_count"),
            what=f"state {state_id!r} electron_count",
        )
        if electron_count != z:
            raise SnapshotError(f"selected state {state_id!r} is not neutral")
        selected_columns.append((z, column_name))
    return tuple(selected_columns)


def _parse_retained_csv(
    profiles_data: bytes,
    metadata: Mapping[str, object],
    selected_columns: tuple[tuple[int, str], ...],
) -> tuple[bytes, float, float, int]:
    """Validate source rows and return the decimal-preserving consumer CSV."""

    try:
        source_text = profiles_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotError("profiles.csv is not valid UTF-8") from exc

    source_handle = io.StringIO(source_text, newline="")
    reader = csv.reader(source_handle)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise SnapshotError("profiles.csv is empty") from exc
    except csv.Error as exc:
        raise SnapshotError("profiles.csv header is invalid") from exc

    if not header or header[0] != RADIUS_COLUMN:
        raise SnapshotError(f"profiles.csv must start with {RADIUS_COLUMN!r}")
    if len(header) != len(set(header)):
        raise SnapshotError("profiles.csv contains duplicate columns")

    columns = _mapping(metadata.get("columns"), what="columns")
    if tuple(header[1:]) != tuple(columns):
        raise SnapshotError("profiles.csv header disagrees with column metadata")
    header_index = {name: index for index, name in enumerate(header)}
    missing = [name for _, name in selected_columns if name not in header_index]
    if missing:
        raise SnapshotError(f"selected CSV columns are missing: {missing!r}")

    output_rows: list[list[str]] = []
    previous_radius: float | None = None
    previous_density: dict[int, float] = {}
    last_below: float | None = None
    bracket: float | None = None

    try:
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise SnapshotError(
                    f"profiles.csv row {row_number} has {len(row)} cells; "
                    f"expected {len(header)}"
                )
            radius_text = row[0]
            try:
                radius = float(radius_text)
            except ValueError as exc:
                raise SnapshotError(
                    f"invalid radius in profiles.csv row {row_number}"
                ) from exc
            if not math.isfinite(radius) or radius <= 0.0:
                raise SnapshotError(
                    f"radius must be finite and positive in row {row_number}"
                )
            if previous_radius is not None and radius <= previous_radius:
                raise SnapshotError(
                    f"radii must strictly increase at profiles.csv row {row_number}"
                )

            consumer_row = [radius_text]
            for z, column_name in selected_columns:
                density_text = row[header_index[column_name]]
                try:
                    density = float(density_text)
                except ValueError as exc:
                    raise SnapshotError(
                        f"invalid density for Z={z} in row {row_number}"
                    ) from exc
                if not math.isfinite(density) or density <= 0.0:
                    raise SnapshotError(
                        f"density must be finite and positive for Z={z} "
                        f"in row {row_number}"
                    )
                previous = previous_density.get(z)
                if (
                    previous is not None
                    and density > previous
                    and not math.isclose(
                        density,
                        previous,
                        rel_tol=MONOTONIC_REL_TOL,
                        abs_tol=0.0,
                    )
                ):
                    raise SnapshotError(
                        f"density increases beyond tolerance for Z={z} "
                        f"in row {row_number}"
                    )
                previous_density[z] = density
                consumer_row.append(density_text)

            output_rows.append(consumer_row)
            previous_radius = radius
            if radius <= PUBLIC_MAX_RADIUS_BOHR:
                last_below = radius
            else:
                bracket = radius
                break
    except csv.Error as exc:
        raise SnapshotError("profiles.csv is invalid") from exc

    if last_below != EXPECTED_LAST_BELOW_BOHR:
        raise SnapshotError(
            f"unexpected last radius below 20 bohr: {last_below!r}"
        )
    if bracket != EXPECTED_BRACKET_BOHR:
        raise SnapshotError(f"unexpected radius bracket above 20 bohr: {bracket!r}")
    if len(output_rows) != EXPECTED_RETAINED_ROWS:
        raise SnapshotError(
            f"unexpected retained row count: {len(output_rows)}; "
            f"expected {EXPECTED_RETAINED_ROWS}"
        )

    output_handle = io.StringIO(newline="")
    writer = csv.writer(output_handle, lineterminator="\n")
    writer.writerow([RADIUS_COLUMN, *(f"z{z:03d}" for z in EXPECTED_Z)])
    writer.writerows(output_rows)
    return (
        output_handle.getvalue().encode("utf-8"),
        last_below,
        bracket,
        len(output_rows),
    )


def build_deterministic_zip(csv_bytes: bytes) -> bytes:
    """Return the canonical single-member ZIP bytes for a consumer CSV."""

    member = zipfile.ZipInfo(
        filename=ARCHIVE_MEMBER,
        date_time=(1980, 1, 1, 0, 0, 0),
    )
    member.compress_type = zipfile.ZIP_DEFLATED
    member.create_system = 3
    member.external_attr = 0o100644 << 16
    member.internal_attr = 0
    member.extra = b""
    member.comment = b""

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.comment = b""
        archive.writestr(
            member,
            csv_bytes,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    return buffer.getvalue()


def build_snapshot(profiles_csv: Path, metadata_json: Path) -> Snapshot:
    """Build and fully validate the pinned neutral consumer snapshot."""

    profiles_data = _read_pinned(
        profiles_csv,
        expected_sha256=PROFILES_SHA256,
        label="profiles.csv",
    )
    metadata_data = _read_pinned(
        metadata_json,
        expected_sha256=METADATA_SHA256,
        label="metadata.json",
    )
    metadata = _load_metadata(metadata_data)
    selected_columns = _select_neutral_columns(metadata)
    csv_bytes, last_below, bracket, retained_rows = _parse_retained_csv(
        profiles_data,
        metadata,
        selected_columns,
    )
    archive_bytes = build_deterministic_zip(csv_bytes)
    return Snapshot(
        csv_bytes=csv_bytes,
        archive_bytes=archive_bytes,
        selected_profiles=len(selected_columns),
        retained_rows=retained_rows,
        last_below_bohr=last_below,
        bracket_bohr=bracket,
    )


def _resolve_source_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """Resolve either a source directory or two explicit source paths."""

    if args.source_dir is not None:
        if args.profiles_csv is not None or args.metadata_json is not None:
            raise SnapshotError(
                "use --source-dir or explicit --profiles-csv/--metadata-json, not both"
            )
        return args.source_dir / "profiles.csv", args.source_dir / "metadata.json"
    if args.profiles_csv is None or args.metadata_json is None:
        raise SnapshotError(
            "provide --source-dir or both --profiles-csv and --metadata-json"
        )
    return args.profiles_csv, args.metadata_json


def _write_output(path: Path, data: bytes) -> None:
    """Write generated bytes, creating only the selected output directory."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError as exc:
        raise SnapshotError(f"cannot write output: {path}") from exc


def _check_output(path: Path, expected: bytes) -> None:
    """Require the committed output to match regenerated bytes exactly."""

    try:
        actual = path.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read output for check: {path}") from exc
    if actual != expected:
        raise SnapshotError(
            f"snapshot differs: expected SHA-256 {_sha256(expected)}, "
            f"got {_sha256(actual)}"
        )


def _parser() -> argparse.ArgumentParser:
    """Create the snapshot-builder command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Build or check the pinned neutral H-Lr proatomic-density snapshot."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help=(
            "local upstream dataset directory containing profiles.csv and "
            "metadata.json"
        ),
    )
    parser.add_argument("--profiles-csv", type=Path, help="explicit profiles.csv path")
    parser.add_argument(
        "--metadata-json",
        type=Path,
        help="explicit metadata.json path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"output ZIP path (default: {OUTPUT_PATH})",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the snapshot")
    mode.add_argument("--check", action="store_true", help="check exact output bytes")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local snapshot builder in write or byte-check mode."""

    parser = _parser()
    args = parser.parse_args(argv)
    try:
        profiles_csv, metadata_json = _resolve_source_paths(args)
        snapshot = build_snapshot(profiles_csv, metadata_json)
        if args.write:
            _write_output(args.output, snapshot.archive_bytes)
            action = "wrote"
        else:
            _check_output(args.output, snapshot.archive_bytes)
            action = "verified"
    except SnapshotError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Source: atomref-proatoms {SOURCE_DATA_VERSION} / {SOURCE_DATASET_ID}"
    )
    print(
        f"Inputs: profiles sha256={PROFILES_SHA256}; "
        f"metadata sha256={METADATA_SHA256}"
    )
    print(
        f"Selection: {snapshot.selected_profiles} neutral profiles, "
        f"Z={EXPECTED_Z[0]}..{EXPECTED_Z[-1]}"
    )
    print(
        f"Rows: {snapshot.retained_rows}; 20-bohr bracket "
        f"{snapshot.last_below_bohr!r} < 20 < {snapshot.bracket_bohr!r}"
    )
    print(
        f"Output: {action} {args.output} "
        f"({len(snapshot.archive_bytes)} bytes, "
        f"sha256={_sha256(snapshot.archive_bytes)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
