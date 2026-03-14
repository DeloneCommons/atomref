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
