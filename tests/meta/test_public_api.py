from __future__ import annotations

import atomref as ar


REQUIRED_PUBLIC_NAMES = {
    'Element',
    'DatasetRef',
    'DatasetInfo',
    'ElementScalarSet',
    'QuantityInfo',
    'LookupResult',
    'RadiiPolicy',
    'DEFAULT_COVALENT_POLICY',
    'DEFAULT_VDW_POLICY',
    'LinearTransfer',
    'SubstitutionTransfer',
    'get_covalent_radius',
    'lookup_covalent_radius',
    'get_vdw_radius',
    'lookup_vdw_radius',
    'list_quantities',
    'list_dataset_ids',
    'list_dataset_infos',
    'list_radii_sets',
    'list_radii_set_infos',
}


def test___all___exports_existing_objects() -> None:
    for name in ar.__all__:
        assert hasattr(ar, name), name


def test_core_public_api_names_are_exported() -> None:
    assert REQUIRED_PUBLIC_NAMES.issubset(set(ar.__all__))
