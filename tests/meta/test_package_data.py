from __future__ import annotations

from importlib import resources
import json


def test_packaged_data_files_are_available() -> None:
    data_root = resources.files('atomref.data')
    for name in (
        'periodic_table.csv',
        'covalent.csv',
        'proatomic_density_neutral.zip',
        'van_der_waals.csv',
        'registry.json',
        'xh_bond_length.csv',
    ):
        assert data_root.joinpath(name).is_file(), name


def test_packaged_registry_keeps_atomic_support_classification() -> None:
    data_root = resources.files('atomref.data')
    raw = json.loads(data_root.joinpath('registry.json').read_text(encoding='utf-8'))

    assert 'atomic_radius' in raw['datasets']
    assert 'xh_bond_length' in raw['datasets']
    rahm = raw['datasets']['atomic_radius']['rahm2016']
    assert rahm['usage_role'] == 'support'
    assert rahm['semantic_class'] == 'atomic_isodensity'
    assert rahm['phase_context'] == 'isolated_atom'


def test_packaged_registry_records_proatomic_attribution() -> None:
    data_root = resources.files('atomref.data')
    raw = json.loads(data_root.joinpath('registry.json').read_text(encoding='utf-8'))

    datasets = raw['datasets']['proatomic_density']
    matches = [
        entry
        for entry in datasets.values()
        if entry.get('storage', {}).get('filename')
        == 'proatomic_density_neutral.zip'
    ]
    assert len(matches) == 1

    entry_text = json.dumps(matches[0], sort_keys=True)
    for marker in (
        'CC BY 4.0',
        '10.5281/zenodo.21291021',
        '10.5281/zenodo.21291022',
        'pbe0_sfx2c_dyallv4z_h-lr_spherical_v2',
    ):
        assert marker in entry_text
