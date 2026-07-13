from __future__ import annotations

import atomref as ar


REQUIRED_PUBLIC_NAMES = {
    'BuiltinSet',
    'Element',
    'DatasetRef',
    'DatasetInfo',
    'ElementRadialSet',
    'ElementScalarSet',
    'QuantityInfo',
    'LookupResult',
    'RadiiPolicy',
    'DEFAULT_COVALENT_POLICY',
    'DEFAULT_VDW_POLICY',
    'BOHR_TO_ANGSTROM',
    'DEFAULT_PROATOMIC_DENSITY_SET',
    'PROATOMIC_TAIL_CUTOFF',
    'IAS_MINIMUM_RESOLUTION_BOHR',
    'IASPositionResult',
    'ProatomicDensityProfile',
    'ProatomicDensitySet',
    'LinearTransfer',
    'SubstitutionTransfer',
    'get_builtin_set',
    'get_radii_set',
    'get_covalent_radius',
    'lookup_covalent_radius',
    'get_vdw_radius',
    'lookup_vdw_radius',
    'XHPolicy',
    'DEFAULT_XH_POLICY',
    'get_xh_set',
    'get_xh_bond_length',
    'lookup_xh_bond_length',
    'list_xh_sets',
    'list_xh_set_infos',
    'list_quantities',
    'list_dataset_ids',
    'list_dataset_infos',
    'list_radii_sets',
    'list_radii_set_infos',
    'get_proatomic_density',
    'get_proatomic_density_profile',
    'get_proatomic_density_set',
    'get_proatomic_density_set_info',
    'estimate_proatomic_boundary',
    'estimate_promolecular_density_minimum',
    'estimate_ias_position',
    'list_proatomic_density_sets',
    'list_proatomic_density_set_infos',
}


def test___all___exports_existing_objects() -> None:
    for name in ar.__all__:
        assert hasattr(ar, name), name


def test_core_public_api_names_are_exported() -> None:
    assert REQUIRED_PUBLIC_NAMES.issubset(set(ar.__all__))
