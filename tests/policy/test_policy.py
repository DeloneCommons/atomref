from __future__ import annotations

from dataclasses import dataclass

import pytest

import atomref as ar
from atomref.errors import PolicyError


def _make_custom_set(
    quantity: str,
    set_id: str,
    values: dict[str, float | None],
) -> ar.ElementScalarSet:
    return ar.ElementScalarSet.from_mapping(
        ref=ar.DatasetRef(quantity, set_id),
        values=values,
        name=set_id,
        units='angstrom',
    )


def _make_partial_covalent_policy(*, include_o: bool) -> ar.RadiiPolicy:
    values = {
        'C': 0.76,
        'N': 0.71,
    }
    if include_o:
        values['O'] = 0.66
    custom = ar.ElementScalarSet.from_mapping(
        ref=ar.DatasetRef('covalent_radius', 'demo_partial_cov'),
        values=values,
        name='Demo partial covalent set',
        units='angstrom',
    )
    return ar.RadiiPolicy(
        kind='covalent',
        base_set=custom,
        transfers=(
            ar.LinearTransfer(
                predictors=(ar.DatasetRef('covalent_radius', 'cordero2008'),),
                min_points=2,
                exclude_placeholders=True,
            ),
        ),
    )


@dataclass
class _DemoPolicyWrapper:
    base: ar.ElementScalarSet
    source: object | None = None

    def as_value_policy(self) -> ar.ValuePolicy[str]:
        transfers = ()
        if self.source is not None:
            transfers = (ar.SubstitutionTransfer(source=self.source),)
        return ar.ValuePolicy(base=self.base, transfers=transfers)


def test_lookup_value_is_public_generic_entry_point() -> None:
    policy = ar.ValuePolicy(
        base=ar.DatasetRef('covalent_radius', 'cordero2008'),
        overrides={'d': 0.5},
    )
    lookup = ar.lookup_value('H', policy=policy)
    assert lookup.source == 'override'
    assert lookup.value == pytest.approx(0.5)
    assert lookup.transfer_depth == 0


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
    assert lookup.transfer_depth == 2
    assert lookup.resolved_from == (
        ar.DatasetRef('covalent_radius', 'csd_legacy_cov'),
    )
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
    assert lookup.transfer_depth == 1
    assert lookup.fit is not None
    assert any('policy source' in note for note in lookup.notes)


def test_linear_transfer_defaults_allow_direct_fit_and_one_nested_prediction() -> None:
    predictor_policy = _make_partial_covalent_policy(include_o=True)
    policy = ar.XHPolicy(
        base_set='csd_legacy_xh_cno',
        transfers=(
            ar.LinearTransfer(
                predictors=(predictor_policy,),
                min_points=3,
                exclude_placeholders=True,
            ),
        ),
    )
    lookup = ar.lookup_xh_bond_length('S', policy=policy)
    assert lookup.source == 'transfer_linear'
    assert lookup.transfer_depth == 2
    assert lookup.fit is not None
    assert lookup.fit.n_points == 3
    assert lookup.value == pytest.approx(ar.lookup_xh_bond_length('S').value)


def test_linear_transfer_fit_restrictions_block_inference_on_inference_by_default(
) -> None:
    predictor_policy = _make_partial_covalent_policy(include_o=False)
    policy = ar.XHPolicy(
        base_set='csd_legacy_xh_cno',
        transfers=(
            ar.LinearTransfer(
                predictors=(predictor_policy,),
                min_points=3,
                exclude_placeholders=True,
            ),
        ),
    )
    with pytest.raises(PolicyError, match='fit-source restrictions'):
        ar.lookup_xh_bond_length('S', policy=policy)


def test_linear_transfer_fit_restrictions_can_be_relaxed_explicitly() -> None:
    predictor_policy = _make_partial_covalent_policy(include_o=False)
    policy = ar.XHPolicy(
        base_set='csd_legacy_xh_cno',
        transfers=(
            ar.LinearTransfer(
                predictors=(predictor_policy,),
                min_points=3,
                exclude_placeholders=True,
                fit_sources=('base', 'override', 'transfer_linear'),
                fit_max_depth=1,
            ),
        ),
    )
    lookup = ar.lookup_xh_bond_length('S', policy=policy)
    assert lookup.source == 'transfer_linear'
    assert lookup.fit is not None
    assert lookup.fit.n_points == 3


def test_linear_transfer_prediction_depth_can_be_tightened() -> None:
    predictor_policy = _make_partial_covalent_policy(include_o=True)
    policy = ar.XHPolicy(
        base_set='csd_legacy_xh_cno',
        transfers=(
            ar.LinearTransfer(
                predictors=(predictor_policy,),
                min_points=3,
                exclude_placeholders=True,
                prediction_max_depth=0,
            ),
        ),
    )
    lookup = ar.lookup_xh_bond_length('S', policy=policy)
    assert lookup.value is None
    assert lookup.source == 'missing'
    assert any('prediction_max_depth' in note for note in lookup.notes)


def test_linear_transfer_rejects_invalid_nested_source_configuration() -> None:
    with pytest.raises(PolicyError, match='fit_max_depth'):
        ar.LinearTransfer(
            predictors=(ar.DatasetRef('covalent_radius', 'cordero2008'),),
            fit_max_depth=-1,
        )
    with pytest.raises(PolicyError, match='allowed values'):
        ar.LinearTransfer(
            predictors=(ar.DatasetRef('covalent_radius', 'cordero2008'),),
            prediction_sources=('missing',),  # type: ignore[arg-type]
        )


def test_lookup_value_detects_generic_policy_cycles() -> None:
    empty_1 = _make_custom_set('covalent_radius', 'cycle_empty_1', {})
    empty_2 = _make_custom_set('covalent_radius', 'cycle_empty_2', {})
    policy_1 = ar.ValuePolicy(base=empty_1)
    policy_2 = ar.ValuePolicy(
        base=empty_2,
        transfers=(ar.SubstitutionTransfer(source=policy_1),),
    )
    object.__setattr__(
        policy_1,
        'transfers',
        (ar.SubstitutionTransfer(source=policy_2),),
    )

    with pytest.raises(PolicyError, match='cyclic policy resolution detected'):
        ar.lookup_value('C', policy=policy_1)


def test_wrapper_policy_cycles_are_detected() -> None:
    empty = _make_custom_set('covalent_radius', 'demo_empty_cov', {})
    wrapper_a = _DemoPolicyWrapper(base=empty)
    wrapper_b = _DemoPolicyWrapper(base=empty, source=wrapper_a)
    wrapper_a.source = wrapper_b

    policy = ar.ValuePolicy(
        base=empty,
        transfers=(ar.SubstitutionTransfer(source=wrapper_a),),
    )
    with pytest.raises(PolicyError, match='cyclic policy resolution detected'):
        ar.lookup_value('C', policy=policy)
