from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib import resources
import io
from types import MappingProxyType
import warnings
import zipfile

import pytest

import atomref as ar
from atomref.errors import DatasetError
import atomref.registry as registry
from atomref.registry import get_builtin_set

_RADIAL_ARCHIVE = 'synthetic_radial.zip'
_RADIAL_MEMBER = 'proatomic_density_neutral.csv'
_RADIAL_CSV = b'r_bohr,z001,z008\n0.0,1.0,8.0\n0.5,0.5,4.0\n'


def _make_zip(
    entries: tuple[tuple[str, bytes], ...],
    *,
    external_attr: int = 0o100644 << 16,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode='w',
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            for name, payload in entries:
                member = zipfile.ZipInfo(
                    filename=name,
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                member.compress_type = zipfile.ZIP_DEFLATED
                member.create_system = 3
                member.external_attr = external_attr
                member.internal_attr = 0
                member.extra = b''
                member.comment = b''
                archive.writestr(
                    member,
                    payload,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        archive.comment = b''
    return buffer.getvalue()


def _mark_zip_member_encrypted(archive_bytes: bytes) -> bytes:
    encrypted = bytearray(archive_bytes)
    for signature, flag_offset in ((b'PK\x03\x04', 6), (b'PK\x01\x02', 8)):
        start = encrypted.index(signature) + flag_offset
        flags = int.from_bytes(encrypted[start : start + 2], 'little') | 0x1
        encrypted[start : start + 2] = flags.to_bytes(2, 'little')
    return bytes(encrypted)


def _corrupt_deflated_member_data(archive_bytes: bytes) -> bytes:
    corrupted = bytearray(archive_bytes)
    with zipfile.ZipFile(io.BytesIO(archive_bytes), mode='r') as archive:
        member = archive.infolist()[0]
    header = member.header_offset
    name_length = int.from_bytes(corrupted[header + 26 : header + 28], 'little')
    extra_length = int.from_bytes(corrupted[header + 28 : header + 30], 'little')
    data_start = header + 30 + name_length + extra_length
    corrupted[data_start] = (corrupted[data_start] & 0xF8) | 0x07
    return bytes(corrupted)


@pytest.fixture
def install_synthetic_radial_registry(monkeypatch: pytest.MonkeyPatch):
    real_registry_loader = registry._load_registry_json

    def clear_caches() -> None:
        registry._load_builtin_set.cache_clear()
        registry._load_radial_csv_zip.cache_clear()
        registry._load_csv_columns.cache_clear()
        real_registry_loader.cache_clear()

    def install(archive_bytes: bytes, *, member: str = _RADIAL_MEMBER) -> None:
        raw_registry = {
            'quantities': {
                'synthetic_profile': {
                    'domain': 'element',
                    'units': 'arbitrary',
                    'description': 'Synthetic radial profiles for loader tests.',
                }
            },
            'datasets': {
                'synthetic_profile': {
                    'synthetic': {
                        'name': 'Synthetic radial profiles',
                        'aliases': ['synthetic alias'],
                        'storage': {
                            'kind': 'element_radial_csv_zip',
                            'filename': _RADIAL_ARCHIVE,
                            'member': member,
                            'radius_column': 'r_bohr',
                            'density_column_pattern': 'z{z:03d}',
                        },
                        'coverage': {
                            'n_values': 2,
                            'z_min': 1,
                            'z_max': 8,
                            'covered_z': [1, 8],
                        },
                    }
                }
            },
        }

        def read_package_data_bytes(filename: str) -> bytes:
            assert filename == _RADIAL_ARCHIVE
            return archive_bytes

        clear_caches()
        monkeypatch.setattr(registry, '_load_registry_json', lambda: raw_registry)
        monkeypatch.setattr(
            registry,
            '_read_package_data_bytes',
            read_package_data_bytes,
        )

    clear_caches()
    try:
        yield install
    finally:
        clear_caches()


def test_packaged_data_files_exist() -> None:
    pkg = 'atomref.data'
    for filename in (
        'periodic_table.csv',
        'covalent.csv',
        'van_der_waals.csv',
        'xh_bond_length.csv',
        'proatomic_density_neutral.zip',
        'registry.json',
    ):
        assert resources.files(pkg).joinpath(filename).is_file(), filename


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
    assert isinstance(ds, ar.ElementScalarSet)
    assert ds.get('C') == 0.76


def test_aliases_resolve_before_builtin_set_caching() -> None:
    canonical = get_builtin_set(ar.DatasetRef('covalent_radius', 'cordero2008'))
    alias = get_builtin_set(
        ar.DatasetRef('covalent_radius', 'Cordero-Alvarez covalent radii')
    )
    assert alias is canonical


def test_synthetic_radial_set_uses_generic_registry_and_loader(
    install_synthetic_radial_registry,
) -> None:
    archive_bytes = _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV),))
    with zipfile.ZipFile(io.BytesIO(archive_bytes), mode='r') as archive:
        assert archive.comment == b''
        assert len(archive.infolist()) == 1
        member = archive.infolist()[0]
        assert member.filename == _RADIAL_MEMBER
        assert member.date_time == (1980, 1, 1, 0, 0, 0)
        assert member.compress_type == zipfile.ZIP_DEFLATED
        assert member.create_system == 3
        assert member.external_attr == 0o100644 << 16
        assert member.internal_attr == 0
        assert member.extra == b''
        assert member.comment == b''
    install_synthetic_radial_registry(archive_bytes)

    assert ar.list_quantities() == ('synthetic_profile',)
    quantity_info = ar.get_quantity_info('synthetic_profile')
    assert quantity_info.domain == 'element'
    assert ar.list_dataset_ids('synthetic_profile') == ('synthetic',)
    assert tuple(
        item.ref.set_id for item in ar.list_dataset_infos('synthetic_profile')
    ) == ('synthetic',)
    info = ar.get_dataset_info(ar.DatasetRef('synthetic_profile', 'synthetic alias'))
    assert info.storage is not None
    assert info.storage['kind'] == 'element_radial_csv_zip'
    assert info.storage['member'] == _RADIAL_MEMBER

    via_alias = get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic alias'))
    dataset = get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))
    assert isinstance(dataset, ar.ElementRadialSet)
    assert via_alias is dataset
    assert dataset.radii == (0.0, 0.5)
    assert dataset.get('H') == (1.0, 0.5)
    assert dataset.get(8) == (8.0, 4.0)
    assert dataset.get('He') is None


def test_radial_zip_rejects_missing_declared_member(
    install_synthetic_radial_registry,
) -> None:
    install_synthetic_radial_registry(
        _make_zip((('different.csv', _RADIAL_CSV),))
    )
    with pytest.raises(DatasetError, match='does not contain the declared member'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_accepts_member_without_file_type_bits(
    install_synthetic_radial_registry,
) -> None:
    archive_bytes = _make_zip(
        ((_RADIAL_MEMBER, _RADIAL_CSV),),
        external_attr=0o600 << 16,
    )
    install_synthetic_radial_registry(archive_bytes)
    dataset = get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))
    assert isinstance(dataset, ar.ElementRadialSet)
    assert dataset.get('H') == (1.0, 0.5)


def test_radial_zip_rejects_unexpected_additional_member(
    install_synthetic_radial_registry,
) -> None:
    install_synthetic_radial_registry(
        _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV), ('extra.txt', b'extra')))
    )
    with pytest.raises(DatasetError, match='must contain exactly one member'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_rejects_duplicate_member_names(
    install_synthetic_radial_registry,
) -> None:
    install_synthetic_radial_registry(
        _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV), (_RADIAL_MEMBER, _RADIAL_CSV)))
    )
    with pytest.raises(DatasetError, match='must contain exactly one member'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_rejects_directory_entry(
    install_synthetic_radial_registry,
) -> None:
    directory = 'proatomic_density_neutral.csv/'
    install_synthetic_radial_registry(
        _make_zip(((directory, b''),)),
        member=directory,
    )
    with pytest.raises(DatasetError, match='contains a directory entry'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_rejects_malformed_archive(
    install_synthetic_radial_registry,
) -> None:
    install_synthetic_radial_registry(b'not a ZIP archive')
    with pytest.raises(DatasetError, match='invalid radial ZIP archive'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_wraps_corrupted_deflated_member(
    install_synthetic_radial_registry,
) -> None:
    archive_bytes = _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV),))
    install_synthetic_radial_registry(
        _corrupt_deflated_member_data(archive_bytes)
    )
    with pytest.raises(DatasetError, match='invalid radial ZIP archive'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_rejects_encrypted_member(
    install_synthetic_radial_registry,
) -> None:
    archive_bytes = _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV),))
    install_synthetic_radial_registry(_mark_zip_member_encrypted(archive_bytes))
    with pytest.raises(DatasetError, match='contains an encrypted member'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_zip_rejects_invalid_csv_columns(
    install_synthetic_radial_registry,
) -> None:
    invalid_csv = b'radius,z001,z008\n0.0,1.0,8.0\n'
    install_synthetic_radial_registry(
        _make_zip(((_RADIAL_MEMBER, invalid_csv),))
    )
    with pytest.raises(DatasetError, match='invalid radial CSV columns'):
        get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))


def test_radial_set_values_are_immutable(
    install_synthetic_radial_registry,
) -> None:
    install_synthetic_radial_registry(
        _make_zip(((_RADIAL_MEMBER, _RADIAL_CSV),))
    )
    dataset = get_builtin_set(ar.DatasetRef('synthetic_profile', 'synthetic'))
    assert isinstance(dataset, ar.ElementRadialSet)
    assert isinstance(dataset.radii, tuple)
    assert isinstance(dataset.get('H'), tuple)
    with pytest.raises(FrozenInstanceError):
        dataset.radii = (1.0,)


def test_unknown_storage_kind_raises_dataset_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ref = ar.DatasetRef('synthetic', 'unknown_storage')
    info = ar.DatasetInfo(
        ref=ref,
        domain='element',
        units=None,
        name='Unknown storage',
        storage=MappingProxyType({'kind': 'mystery'}),
    )
    monkeypatch.setattr(registry, 'get_dataset_info', lambda requested: info)
    registry._load_builtin_set.cache_clear()
    with pytest.raises(DatasetError, match='unknown storage kind'):
        get_builtin_set(ref)


def test_scalar_policy_rejects_radial_set_clearly() -> None:
    ref = ar.DatasetRef('synthetic_profile', 'synthetic')
    info = ar.DatasetInfo(
        ref=ref,
        domain='element',
        units='arbitrary',
        name='Synthetic radial profiles',
    )
    radial = ar.ElementRadialSet(
        ref=ref,
        info=info,
        radii=(0.0,),
        profiles_by_z=(None, (1.0,)),
    )
    with pytest.raises(DatasetError, match='radial payload; scalar dataset required'):
        ar.ValuePolicy(base=radial)


def test_list_quantities_and_quantity_info() -> None:
    quantities = ar.list_quantities()
    assert quantities == (
        'covalent_radius',
        'van_der_waals_radius',
        'atomic_radius',
        'xh_bond_length',
        'proatomic_density',
    )

    info = ar.get_quantity_info('atomic_radius')
    assert info.quantity == 'atomic_radius'
    assert info.domain == 'element'
    assert info.units == 'angstrom'
    assert 'support' in (info.description or '')

    proatomic = ar.get_quantity_info('proatomic_density')
    assert proatomic.domain == 'element'
    assert proatomic.units == 'electron/bohr^3'


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


def test_list_dataset_infos_can_filter_by_usage_role() -> None:
    infos = ar.list_dataset_infos('atomic_radius', usage_role='support')
    assert tuple(info.ref.set_id for info in infos) == ('rahm2016',)
    assert all(info.usage_role == 'support' for info in infos)


def test_list_radii_set_infos_can_filter_by_usage_role() -> None:
    infos = ar.list_radii_set_infos('van_der_waals', usage_role='target')
    assert 'alvarez2013' in {info.ref.set_id for info in infos}
    assert all(info.ref.quantity == 'van_der_waals_radius' for info in infos)


def test_public_builtin_set_helper_is_exported() -> None:
    ds = ar.get_builtin_set(ar.DatasetRef('covalent_radius', 'cordero2008'))
    assert ds.info.ref.quantity == 'covalent_radius'
    assert ds.get('C') == 0.76


def test_public_radii_set_helper_returns_packaged_radii_set() -> None:
    ds = ar.get_radii_set('van_der_waals', 'alvarez2013')
    assert ds.info.ref.quantity == 'van_der_waals_radius'
    assert ds.info.ref.set_id == 'alvarez2013'
    assert ds.get('O') == 1.5


def test_dataset_info_storage_is_frozen() -> None:
    info = ar.get_dataset_info(ar.DatasetRef('covalent_radius', 'cordero2008'))
    assert isinstance(info.storage, MappingProxyType)
    assert info.storage['column'] == 'cordero2008'
    with pytest.raises(TypeError):
        info.storage['column'] = 'broken'

    fresh = ar.get_dataset_info(ar.DatasetRef('covalent_radius', 'cordero2008'))
    assert fresh.storage is not None
    assert fresh.storage['column'] == 'cordero2008'


def test_dataset_alias_resolution_normalizes_dash_variants() -> None:
    info = ar.get_dataset_info(
        ar.DatasetRef('covalent_radius', 'Cordero-Alvarez covalent radii')
    )
    assert info.ref.set_id == 'cordero2008'


def test_custom_set_rejects_normalized_key_collisions() -> None:
    with pytest.raises(DatasetError):
        ar.ElementScalarSet.from_mapping(
            ref=ar.DatasetRef('covalent_radius', 'demo'),
            values={'H': 0.31, 'D': 0.5},
            name='Demo',
            units='angstrom',
        )


def test_custom_set_rejects_non_finite_values() -> None:
    with pytest.raises(DatasetError):
        ar.ElementScalarSet.from_mapping(
            ref=ar.DatasetRef('covalent_radius', 'demo'),
            values={'C': float('nan')},
            name='Demo',
            units='angstrom',
        )
