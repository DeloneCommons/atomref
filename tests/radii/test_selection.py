from __future__ import annotations

import pytest

import atomref as ar
from atomref.errors import PolicyError


def test_get_covalent_radius_default_prefers_cordero() -> None:
    assert ar.get_covalent_radius('C') == pytest.approx(0.76)


def test_get_covalent_radius_maps_deuterium_to_hydrogen() -> None:
    assert ar.get_covalent_radius('D') == pytest.approx(0.31)


def test_get_vdw_radius_default_prefers_alvarez() -> None:
    assert ar.get_vdw_radius('C') == pytest.approx(1.77)


def test_completion_is_used_for_missing_base_values() -> None:
    m = ar.lookup_covalent_radius('Bk')
    assert m.value is not None
    assert m.source == 'transfer_substitution'

    m2 = ar.lookup_vdw_radius('Pm')
    assert m2.value is not None
    assert m2.source == 'transfer_linear'
    assert m2.value == pytest.approx(2.897226539514835)


def test_linear_transfer_rejects_placeholder_values() -> None:
    scheme = ar.RadiiPolicy(
        kind='van_der_waals',
        base_set='bondi1964',
        transfers=(
            ar.LinearTransfer(
                predictors=(ar.DatasetRef('van_der_waals_radius', 'csd_legacy_vdw'),)
            ),
        ),
    )
    m = ar.lookup_vdw_radius('Be', policy=scheme)
    assert m.value is None
    assert m.source == 'missing'
    assert any('placeholder' in s for s in m.notes)


def test_lookup_float_conversion() -> None:
    m = ar.lookup_covalent_radius('C')
    assert float(m) == pytest.approx(0.76)

    m_missing = ar.lookup_covalent_radius('Xx')
    with pytest.raises(TypeError):
        float(m_missing)


def test_override_precedes_base_value() -> None:
    policy = ar.RadiiPolicy(
        kind='covalent',
        base_set='cordero2008',
        overrides={'C': 9.99},
    )
    lookup = ar.lookup_covalent_radius('C', policy=policy)
    assert lookup.source == 'override'
    assert lookup.value == pytest.approx(9.99)


def test_fallback_is_used_only_after_transfers_fail() -> None:
    policy = ar.RadiiPolicy(
        kind='van_der_waals',
        base_set='bondi1964',
        transfers=(
            ar.LinearTransfer(
                predictors=(ar.DatasetRef('van_der_waals_radius', 'csd_legacy_vdw'),)
            ),
        ),
        fallback=2.5,
    )
    lookup = ar.lookup_vdw_radius('Be', policy=policy)
    assert lookup.source == 'fallback'
    assert lookup.value == pytest.approx(2.5)
    assert any('placeholder' in note for note in lookup.notes)


def test_linear_transfer_rejects_multiple_predictors_in_v0_1() -> None:
    policy = ar.RadiiPolicy(
        kind='van_der_waals',
        base_set='alvarez2013',
        transfers=(
            ar.LinearTransfer(
                predictors=(
                    ar.DatasetRef('atomic_radius', 'rahm2016'),
                    ar.DatasetRef('covalent_radius', 'cordero2008'),
                )
            ),
        ),
    )
    with pytest.raises(PolicyError):
        ar.lookup_vdw_radius('Pm', policy=policy)

