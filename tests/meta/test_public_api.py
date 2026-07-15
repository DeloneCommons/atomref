from __future__ import annotations

import inspect
from pathlib import Path

import atomref as ar


REPO_ROOT = Path(__file__).resolve().parents[2]


EXPECTED_PUBLIC_NAMES = {
    '__version__',
    'BuiltinSet',
    'Element',
    'DatasetRef',
    'DatasetInfo',
    'CoverageInfo',
    'ElementRadialSet',
    'ElementScalarSet',
    'QuantityInfo',
    'Reference',
    'LookupResult',
    'ValuePolicy',
    'RadiiPolicy',
    'RadiiElementAssessment',
    'RadiiPolicyAssessment',
    'DEFAULT_COVALENT_POLICY',
    'DEFAULT_VDW_POLICY',
    'BOHR_TO_ANGSTROM',
    'DEFAULT_PROATOMIC_DENSITY_SET',
    'PROATOMIC_TAIL_CUTOFF',
    'IAS_MINIMUM_RESOLUTION_BOHR',
    'IASPositionResult',
    'ProatomicDensityProfile',
    'ProatomicDensitySet',
    'LinearFit',
    'LinearTransfer',
    'SubstitutionTransfer',
    'canonicalize_element_symbol',
    'get_element',
    'iter_elements',
    'is_valid_element_symbol',
    'get_builtin_set',
    'get_dataset_info',
    'get_quantity_info',
    'get_radii_set',
    'get_radii_set_info',
    'get_covalent_radius',
    'lookup_covalent_radius',
    'get_vdw_radius',
    'lookup_vdw_radius',
    'XHPolicy',
    'DEFAULT_XH_POLICY',
    'get_xh_set',
    'get_xh_set_info',
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
    'lookup_value',
    'get_value',
    'assess_radii_policy',
}


def test___all___exports_existing_objects() -> None:
    for name in ar.__all__:
        assert hasattr(ar, name), name


def test_public_api_is_exact() -> None:
    assert len(ar.__all__) == len(set(ar.__all__))
    assert set(ar.__all__) == EXPECTED_PUBLIC_NAMES


def test_docs_merge_init_signatures_into_public_classes() -> None:
    config = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "merge_init_into_class: true" in config


def test_lookup_value_examples_are_a_top_level_docstring_section() -> None:
    docstring = inspect.getdoc(ar.lookup_value)
    assert docstring is not None
    lines = docstring.splitlines()

    raises_index = lines.index("Raises:")
    examples_index = lines.index("Examples:")
    notes_index = lines.index("Notes:")

    assert raises_index < examples_index < notes_index
