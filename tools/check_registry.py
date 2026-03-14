#!/usr/bin/env python3
"""Validate packaged registry metadata against bundled CSV tables."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
import sys
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import atomref as ar
from atomref.registry import get_builtin_set

_ALLOWED_USAGE_ROLES = {"target", "support"}


def _canonical_token(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _iter_dataset_refs() -> Iterable[ar.DatasetRef]:
    for quantity in ar.list_quantities():
        for set_id in ar.list_dataset_ids(quantity):
            yield ar.DatasetRef(quantity, set_id)


def _validate_alias_collisions(errors: list[str]) -> None:
    for quantity in ar.list_quantities():
        seen: dict[str, str] = {}
        for set_id in ar.list_dataset_ids(quantity):
            info = ar.get_dataset_info(ar.DatasetRef(quantity, set_id))
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


def _validate_dataset_metadata(errors: list[str]) -> None:
    quantities = set(ar.list_quantities())
    by_role: dict[str, list[str]] = defaultdict(list)

    for ref in _iter_dataset_refs():
        quantity_info = ar.get_quantity_info(ref.quantity)
        info = ar.get_dataset_info(ref)
        dataset = get_builtin_set(ref)

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
            filename = info.storage.get("filename")
            column = info.storage.get("column")
            fmt = info.storage.get("format")
            if not isinstance(filename, str) or not filename:
                errors.append(f"invalid storage filename for {ref!r}: {filename!r}")
            if not isinstance(column, str) or not column:
                errors.append(f"invalid storage column for {ref!r}: {column!r}")
            if fmt != "dense_by_z_csv":
                errors.append(f"unsupported storage format for {ref!r}: {fmt!r}")

        coverage = info.coverage
        if coverage is None:
            errors.append(f"missing coverage metadata for {ref!r}")
            max_z = len(dataset.values_by_z) - 1
        else:
            max_z = (
                coverage.z_max
                if coverage.z_max is not None
                else len(dataset.values_by_z) - 1
            )

        covered_z = tuple(
            z
            for z, value in enumerate(dataset.values_by_z)
            if z > 0 and value is not None and z <= max_z
        )
        covered_set = set(covered_z)
        missing_z = tuple(z for z in range(1, max_z + 1) if z not in covered_set)
        has_placeholders = info.placeholder_value is not None and any(
            value is not None and abs(value - info.placeholder_value) < 1e-12
            for value in dataset.values_by_z[1 : max_z + 1]
        )

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
