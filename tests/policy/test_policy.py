from __future__ import annotations

import pytest

import atomref as ar
from atomref.errors import PolicyError


def test_lookup_value_is_public_generic_entry_point() -> None:
    policy = ar.ValuePolicy(
        base=ar.DatasetRef('covalent_radius', 'cordero2008'),
        overrides={'d': 0.5},
    )
    lookup = ar.lookup_value('H', policy=policy)
    assert lookup.source == 'override'
    assert lookup.value == pytest.approx(0.5)


def test_get_value_returns_only_scalar() -> None:
    policy = ar.ValuePolicy(base=ar.DatasetRef('covalent_radius', 'cordero2008'))
    assert ar.get_value('C', policy=policy) == pytest.approx(0.76)


def test_value_policy_rejects_normalized_override_collisions() -> None:
    with pytest.raises(PolicyError):
        ar.ValuePolicy(
            base=ar.DatasetRef('covalent_radius', 'cordero2008'),
            overrides={'H': 0.31, 'D': 0.4},
        )


def test_value_policy_rejects_non_finite_fallback() -> None:
    with pytest.raises(PolicyError):
        ar.ValuePolicy(
            base=ar.DatasetRef('covalent_radius', 'cordero2008'),
            fallback=float('nan'),
        )


def test_substitution_transfer_accepts_policy_source() -> None:
    custom = ar.ElementScalarSet.from_mapping(
        ref=ar.DatasetRef('covalent_radius', 'demo_user_cov'),
        values={'C': 0.77},
        name='Demo covalent set',
        units='angstrom',
    )
    policy = ar.ValuePolicy(
        base=custom,
        transfers=(ar.SubstitutionTransfer(source=ar.DEFAULT_COVALENT_POLICY),),
    )
    lookup = ar.lookup_value('Bk', policy=policy)
    assert lookup.source == 'transfer_substitution'
    assert lookup.value == pytest.approx(1.54)
    assert lookup.resolved_from == (ar.DatasetRef('covalent_radius', 'csd_legacy_cov'),)
    assert any('policy source' in note for note in lookup.notes)


def test_linear_transfer_accepts_policy_predictor() -> None:
    predictor_policy = ar.ValuePolicy(base=ar.DatasetRef('atomic_radius', 'rahm2016'))
    policy = ar.RadiiPolicy(
        kind='van_der_waals',
        base_set='alvarez2013',
        transfers=(ar.LinearTransfer(predictors=(predictor_policy,),),),
    )
    lookup = ar.lookup_vdw_radius('Pm', policy=policy)
    assert lookup.source == 'transfer_linear'
    assert lookup.value == pytest.approx(ar.lookup_vdw_radius('Pm').value)
    assert lookup.fit is not None
    assert any('policy source' in note for note in lookup.notes)
