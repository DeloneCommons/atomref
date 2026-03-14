from __future__ import annotations

from importlib import resources

import atomref as ar
from atomref.registry import get_builtin_set


def test_packaged_data_files_exist() -> None:
    pkg = 'atomref.data'
    assert resources.files(pkg).joinpath('periodic_table.csv').is_file()
    assert resources.files(pkg).joinpath('covalent.csv').is_file()
    assert resources.files(pkg).joinpath('van_der_waals.csv').is_file()
    assert resources.files(pkg).joinpath('registry.json').is_file()


def test_registry_lists_vdw_sets_but_not_atomic_support_sets() -> None:
    vdw_sets = ar.list_radii_sets('van_der_waals')
    assert 'alvarez2013' in vdw_sets
    assert 'rahm2016' not in vdw_sets


def test_rahm_is_registered_as_atomic_radius() -> None:
    info = ar.get_dataset_info(ar.DatasetRef('atomic_radius', 'rahm2016'))
    assert info.ref.quantity == 'atomic_radius'
    assert info.semantic_class == 'atomic_isodensity'
    assert info.phase_context == 'isolated_atom'


def test_builtin_set_loading_works() -> None:
    ds = get_builtin_set(ar.DatasetRef('covalent_radius', 'cordero2008'))
    assert ds.get('C') == 0.76


def test_list_quantities_and_quantity_info() -> None:
    quantities = ar.list_quantities()
    assert quantities == ('covalent_radius', 'van_der_waals_radius', 'atomic_radius')

    info = ar.get_quantity_info('atomic_radius')
    assert info.quantity == 'atomic_radius'
    assert info.domain == 'element'
    assert info.units == 'angstrom'
    assert 'support' in (info.description or '')


def test_rahm_note_no_longer_claims_it_is_classified_as_vdw() -> None:
    info = ar.get_dataset_info(ar.DatasetRef('atomic_radius', 'rahm2016'))
    joined = ' '.join(info.notes).lower()
    assert 'classified as vdw' not in joined
    assert 'atomic support data' in joined


def test_usage_role_is_exposed_on_dataset_info() -> None:
    info = ar.get_dataset_info(ar.DatasetRef('atomic_radius', 'rahm2016'))
    assert info.usage_role == 'support'


def test_list_dataset_ids_can_filter_by_usage_role() -> None:
    assert ar.list_dataset_ids('atomic_radius', usage_role='support') == ('rahm2016',)
    assert ar.list_dataset_ids('van_der_waals_radius', usage_role='target') == (
        'bondi1964',
        'rowland_taylor1996',
        'alvarez2013',
        'chernyshov2020',
    )


def test_list_radii_sets_can_filter_by_usage_role() -> None:
    assert ar.list_radii_sets('covalent', usage_role='support') == ('csd_legacy_cov',)
    assert 'alvarez2013' in ar.list_radii_sets('van_der_waals', usage_role='target')
