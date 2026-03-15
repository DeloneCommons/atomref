from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

import atomref as ar
from atomref.registry import _canonicalize_alias_token, get_builtin_set

_ALLOWED_USAGE_ROLES = {"target", "support"}


def test_dataset_aliases_are_unique_within_each_quantity() -> None:
    for quantity in ar.list_quantities():
        seen: dict[str, str] = {}
        for set_id in ar.list_dataset_ids(quantity):
            info = ar.get_dataset_info(ar.DatasetRef(quantity, set_id))
            for token in (set_id, *info.aliases):
                key = _canonicalize_alias_token(token)
                previous = seen.get(key)
                assert previous in (None, set_id)
                seen[key] = set_id


def test_every_built_in_dataset_loads_and_matches_coverage_metadata() -> None:
    for quantity in ar.list_quantities():
        quantity_info = ar.get_quantity_info(quantity)
        for set_id in ar.list_dataset_ids(quantity):
            ref = ar.DatasetRef(quantity, set_id)
            info = ar.get_dataset_info(ref)
            dataset = get_builtin_set(ref)

            assert info.domain == quantity_info.domain
            assert info.units == quantity_info.units
            assert info.usage_role in _ALLOWED_USAGE_ROLES
            assert info.references
            assert info.coverage is not None

            max_z = (
                info.coverage.z_max
                if info.coverage.z_max is not None
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

            coverage = asdict(info.coverage)
            assert coverage["n_values"] == len(covered_z)
            assert coverage["z_min"] == (min(covered_z) if covered_z else None)
            assert coverage["z_max"] == (max(covered_z) if covered_z else None)
            assert coverage["has_placeholders"] is has_placeholders
            if coverage["covered_z"]:
                assert tuple(coverage["covered_z"]) == covered_z
            if coverage["missing_z"]:
                assert tuple(coverage["missing_z"]) == missing_z


def test_non_atomic_quantities_have_at_least_one_target_dataset() -> None:
    by_role: dict[str, list[str]] = defaultdict(list)
    for quantity in ar.list_quantities():
        for set_id in ar.list_dataset_ids(quantity):
            role = ar.get_dataset_info(ar.DatasetRef(quantity, set_id)).usage_role
            assert role is not None
            by_role[role].append(quantity)

    for quantity in ar.list_quantities():
        if quantity != "atomic_radius":
            assert quantity in by_role["target"]
