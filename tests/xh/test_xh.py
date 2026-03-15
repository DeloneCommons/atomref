from __future__ import annotations

import pytest

import atomref as ar
from atomref.errors import PolicyError


def test_get_xh_bond_length_returns_curated_cno_values() -> None:
    assert ar.get_xh_bond_length('C') == pytest.approx(1.089)
    assert ar.get_xh_bond_length('N') == pytest.approx(1.015)
    assert ar.get_xh_bond_length('O') == pytest.approx(0.993)


def test_lookup_xh_bond_length_infers_other_elements_from_cordero() -> None:
    lookup = ar.lookup_xh_bond_length('S')
    assert lookup.source == 'transfer_linear'
    assert lookup.resolved_from == (ar.DatasetRef('covalent_radius', 'cordero2008'),)
    assert lookup.fit is not None
    assert lookup.fit.n_points == 3
    assert lookup.value == pytest.approx(1.3587333333333333)


def test_lookup_xh_bond_length_rejects_h_as_parent_element() -> None:
    lookup = ar.lookup_xh_bond_length('H')
    assert lookup.value is None
    assert lookup.source == 'missing'
    assert any('not a valid parent element' in note for note in lookup.notes)


def test_list_xh_sets_and_metadata() -> None:
    assert ar.list_xh_sets() == ('csd_legacy_xh_cno',)
    info = ar.get_xh_set_info('csd_legacy_xh_cno')
    assert info.ref.quantity == 'xh_bond_length'
    assert info.usage_role == 'target'
    assert info.coverage is not None
    assert info.coverage.n_values == 3


def test_xh_policy_rejects_h_override_key() -> None:
    policy = ar.XHPolicy(base_set='csd_legacy_xh_cno', overrides={'H': 1.0})
    with pytest.raises(PolicyError):
        policy.as_value_policy()


def test_xh_policy_rejects_negative_fallback() -> None:
    policy = ar.XHPolicy(base_set='csd_legacy_xh_cno', fallback=-1.0)
    with pytest.raises(PolicyError):
        policy.as_value_policy()


def test_xh_policy_accepts_wrapper_policy_predictor() -> None:
    policy = ar.XHPolicy(
        base_set='csd_legacy_xh_cno',
        transfers=(
            ar.LinearTransfer(
                predictors=(ar.DEFAULT_COVALENT_POLICY,),
                min_points=3,
                exclude_placeholders=True,
            ),
        ),
    )
    lookup = ar.lookup_xh_bond_length('Bk', policy=policy)
    assert lookup.source == 'transfer_linear'
    assert lookup.value == pytest.approx(1.8291333333333335)
    assert lookup.resolved_from == (ar.DatasetRef('covalent_radius', 'csd_legacy_cov'),)
    assert any('policy source' in note for note in lookup.notes)
