#!/usr/bin/env python3
"""Validate packaged registry metadata against bundled data payloads."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from importlib import import_module
import math
from pathlib import Path
import sys
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_ALLOWED_USAGE_ROLES = {"target", "support"}
_ALLOWED_STORAGE_KINDS = {"element_scalar_csv", "element_radial_csv_zip"}
_RADIAL_REQUIRED_TEXT_FIELDS = (
    "member",
    "radius_column",
    "density_column_pattern",
    "native_coordinate_unit",
    "native_density_unit",
    "interpolation_contract",
    "charge_scope",
    "source_project",
    "source_release",
    "source_dataset_id",
    "basis_id",
    "profile_data_version",
    "electronic_method",
    "scf_model",
    "relativity",
    "data_license",
    "data_license_url",
    "concept_doi",
    "version_doi",
)
_RADIAL_REQUIRED_SHA256_FIELDS = (
    "source_profiles_sha256",
    "source_metadata_sha256",
    "basis_sha256",
)


def _load_atomref_module():
    return import_module("atomref")


def _get_builtin_set(ref):
    registry = import_module("atomref.registry")
    return registry.get_builtin_set(ref)


def _canonical_token(value: str) -> str:
    registry = import_module("atomref.registry")
    return registry._canonicalize_alias_token(value)


def _iter_dataset_refs() -> Iterable[object]:
    ar = _load_atomref_module()
    for quantity in ar.list_quantities():
        for info in ar.list_dataset_infos(quantity):
            yield info.ref


def _validate_alias_collisions(errors: list[str]) -> None:
    ar = _load_atomref_module()
    for quantity in ar.list_quantities():
        seen: dict[str, str] = {}
        for info in ar.list_dataset_infos(quantity):
            set_id = info.ref.set_id
            for token in (set_id, *info.aliases):
                key = _canonical_token(token)
                previous = seen.get(key)
                if previous is not None and previous != set_id:
                    msg = (
                        f"alias collision in {quantity!r}: {token!r} resolves to both "
                        f"{previous!r} and {set_id!r}"
                    )
                    errors.append(msg)
                else:
                    seen[key] = set_id


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _validate_radial_storage(ref, info, errors: list[str]) -> None:
    storage = info.storage
    if storage is None:
        return

    if storage.get("format") != "wide_csv_zip":
        errors.append(
            f"unsupported radial storage format for {ref!r}: "
            f"{storage.get('format')!r}"
        )

    for field in _RADIAL_REQUIRED_TEXT_FIELDS:
        value = storage.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"missing or invalid radial metadata {field!r} for {ref!r}"
            )

    hexadecimal = frozenset("0123456789abcdef")
    for field in _RADIAL_REQUIRED_SHA256_FIELDS:
        value = storage.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in hexadecimal for character in value)
        ):
            errors.append(f"invalid radial SHA-256 {field!r} for {ref!r}")

    retained_rows = storage.get("retained_rows")
    if (
        not isinstance(retained_rows, int)
        or isinstance(retained_rows, bool)
        or retained_rows <= 0
    ):
        errors.append(f"invalid retained_rows for {ref!r}: {retained_rows!r}")

    public_limit = storage.get("public_max_radius_bohr")
    if not _is_finite_number(public_limit) or float(public_limit) <= 0.0:
        errors.append(
            f"invalid public_max_radius_bohr for {ref!r}: {public_limit!r}"
        )

    bracket = storage.get("retained_bracketing_radius_bohr")
    if not _is_finite_number(bracket):
        errors.append(
            f"invalid retained_bracketing_radius_bohr for {ref!r}: {bracket!r}"
        )
    elif _is_finite_number(public_limit) and float(bracket) <= float(public_limit):
        errors.append(
            f"radial bracket does not exceed the public limit for {ref!r}"
        )

    tolerance = storage.get("monotonicity_relative_tolerance")
    if not _is_finite_number(tolerance) or float(tolerance) < 0.0:
        errors.append(
            f"invalid monotonicity_relative_tolerance for {ref!r}: "
            f"{tolerance!r}"
        )

    if storage.get("native_density_unit") != info.units:
        errors.append(
            f"radial native density unit mismatch for {ref!r}: "
            f"{storage.get('native_density_unit')!r} != {info.units!r}"
        )


def _validate_radial_values(ref, info, dataset, errors: list[str]) -> None:
    storage = info.storage
    if storage is None:
        return

    radii = dataset.radii
    if not radii:
        errors.append(f"radial dataset has no radii for {ref!r}")
    else:
        if any(not math.isfinite(radius) or radius <= 0.0 for radius in radii):
            errors.append(
                f"radial dataset has nonpositive or non-finite radii: {ref!r}"
            )
        if any(right <= left for left, right in zip(radii, radii[1:])):
            errors.append(f"radial dataset radii do not strictly increase: {ref!r}")

    retained_rows = storage.get("retained_rows")
    if (
        isinstance(retained_rows, int)
        and not isinstance(retained_rows, bool)
        and len(radii) != retained_rows
    ):
        errors.append(
            f"radial row-count mismatch for {ref!r}: loaded {len(radii)}, "
            f"declared {retained_rows}"
        )

    public_limit = storage.get("public_max_radius_bohr")
    bracket = storage.get("retained_bracketing_radius_bohr")
    if _is_finite_number(public_limit) and radii:
        if len(radii) < 2 or not (
            radii[-2] <= float(public_limit) < radii[-1]
        ):
            errors.append(
                f"radial grid does not retain exactly one public-limit bracket "
                f"for {ref!r}"
            )
    if _is_finite_number(bracket) and radii and radii[-1] != float(bracket):
        errors.append(
            f"radial bracket mismatch for {ref!r}: loaded {radii[-1]!r}, "
            f"declared {bracket!r}"
        )

    tolerance = storage.get("monotonicity_relative_tolerance")
    usable_tolerance = (
        float(tolerance)
        if _is_finite_number(tolerance) and float(tolerance) >= 0.0
        else None
    )
    for z, profile in enumerate(dataset.profiles_by_z):
        if z == 0 or profile is None:
            continue
        if len(profile) != len(radii):
            errors.append(
                f"radial profile length mismatch for {ref!r}, Z={z}: "
                f"{len(profile)} != {len(radii)}"
            )
            continue
        if any(not math.isfinite(value) or value <= 0.0 for value in profile):
            errors.append(
                f"radial profile has nonpositive or non-finite values for "
                f"{ref!r}, Z={z}"
            )
        if usable_tolerance is not None and any(
            current > previous
            and not math.isclose(
                current,
                previous,
                rel_tol=usable_tolerance,
                abs_tol=0.0,
            )
            for previous, current in zip(profile, profile[1:])
        ):
            errors.append(
                f"radial profile increases beyond tolerance for {ref!r}, Z={z}"
            )


def _validate_dataset_metadata(errors: list[str]) -> None:
    ar = _load_atomref_module()
    quantities = set(ar.list_quantities())
    by_role: dict[str, list[str]] = defaultdict(list)

    for ref in _iter_dataset_refs():
        quantity_info = ar.get_quantity_info(ref.quantity)
        info = ar.get_dataset_info(ref)
        dataset = _get_builtin_set(ref)

        if info.ref != ref:
            errors.append(f"dataset ref mismatch: requested {ref!r}, got {info.ref!r}")

        if info.domain != quantity_info.domain:
            msg = (
                f"domain mismatch for {ref!r}: quantity={quantity_info.domain!r}, "
                f"dataset={info.domain!r}"
            )
            errors.append(msg)

        if info.units != quantity_info.units:
            msg = (
                f"units mismatch for {ref!r}: quantity={quantity_info.units!r}, "
                f"dataset={info.units!r}"
            )
            errors.append(msg)

        if info.usage_role not in _ALLOWED_USAGE_ROLES:
            errors.append(f"invalid usage_role for {ref!r}: {info.usage_role!r}")
        else:
            by_role[info.usage_role].append(ref.quantity)

        if not info.references:
            errors.append(f"missing references for {ref!r}")

        if info.storage is None:
            errors.append(f"missing storage metadata for {ref!r}")
        else:
            kind = info.storage.get("kind")
            filename = info.storage.get("filename")
            if kind not in _ALLOWED_STORAGE_KINDS:
                errors.append(f"unsupported storage kind for {ref!r}: {kind!r}")
            if not isinstance(filename, str) or not filename:
                errors.append(f"invalid storage filename for {ref!r}: {filename!r}")
            if kind == "element_scalar_csv":
                column = info.storage.get("column")
                fmt = info.storage.get("format")
                if not isinstance(column, str) or not column:
                    errors.append(f"invalid storage column for {ref!r}: {column!r}")
                if fmt != "dense_by_z_csv":
                    errors.append(f"unsupported storage format for {ref!r}: {fmt!r}")
            elif kind == "element_radial_csv_zip":
                member = info.storage.get("member")
                radius_column = info.storage.get("radius_column")
                density_pattern = info.storage.get("density_column_pattern")
                if not isinstance(member, str) or not member:
                    errors.append(
                        f"invalid radial archive member for {ref!r}: {member!r}"
                    )
                if not isinstance(radius_column, str) or not radius_column:
                    errors.append(
                        f"invalid radial radius column for {ref!r}: {radius_column!r}"
                    )
                if not isinstance(density_pattern, str) or "{z" not in density_pattern:
                    errors.append(
                        f"invalid radial density-column pattern for {ref!r}: "
                        f"{density_pattern!r}"
                    )
                _validate_radial_storage(ref, info, errors)

        values_by_z = (
            dataset.values_by_z
            if isinstance(dataset, ar.ElementScalarSet)
            else dataset.profiles_by_z
        )
        coverage = info.coverage
        if coverage is None:
            errors.append(f"missing coverage metadata for {ref!r}")
            max_z = len(values_by_z) - 1
        else:
            max_z = (
                coverage.z_max
                if coverage.z_max is not None
                else len(values_by_z) - 1
            )

        covered_z = tuple(
            z
            for z, value in enumerate(values_by_z)
            if z > 0 and value is not None and z <= max_z
        )
        covered_set = set(covered_z)
        missing_z = tuple(z for z in range(1, max_z + 1) if z not in covered_set)
        has_placeholders = (
            isinstance(dataset, ar.ElementScalarSet)
            and info.placeholder_value is not None
            and any(
                value is not None and abs(value - info.placeholder_value) < 1e-12
                for value in dataset.values_by_z[1 : max_z + 1]
            )
        )

        if isinstance(dataset, ar.ElementRadialSet):
            _validate_radial_values(ref, info, dataset, errors)

        if coverage is not None:
            expected = {
                "n_values": len(covered_z),
                "z_min": min(covered_z) if covered_z else None,
                "z_max": max(covered_z) if covered_z else None,
                "has_placeholders": has_placeholders,
            }
            actual = asdict(coverage)
            for key, value in expected.items():
                if actual[key] != value:
                    msg = (
                        f"coverage mismatch for {ref!r}: {key} is {actual[key]!r}, "
                        f"expected {value!r}"
                    )
                    errors.append(msg)
            if actual["covered_z"] and tuple(actual["covered_z"]) != covered_z:
                msg = (
                    f"coverage mismatch for {ref!r}: covered_z is "
                    f"{actual['covered_z']!r}, expected {covered_z!r}"
                )
                errors.append(msg)
            if actual["missing_z"] and tuple(actual["missing_z"]) != missing_z:
                msg = (
                    f"coverage mismatch for {ref!r}: missing_z is "
                    f"{actual['missing_z']!r}, expected {missing_z!r}"
                )
                errors.append(msg)

        if ref.quantity not in quantities:
            errors.append(f"dataset refers to unknown quantity: {ref!r}")

    for quantity in quantities:
        if quantity not in by_role.get("target", []) and quantity != "atomic_radius":
            errors.append(f"quantity {quantity!r} has no target datasets")


def main() -> int:
    errors: list[str] = []
    _validate_alias_collisions(errors)
    _validate_dataset_metadata(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Registry validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
