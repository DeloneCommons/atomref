from __future__ import annotations

import atomref as ar


def test_assess_vdw_default_linear_counts() -> None:
    rep = ar.assess_radii_policy(['Pm', 'O'], policy=ar.DEFAULT_VDW_POLICY)
    assert rep.kind == 'van_der_waals'
    assert rep.n_elements == 2
    assert rep.n_base == 1
    assert rep.n_transfer_linear == 1
    assert rep.n_missing == 0
    assert rep.fits
    assert rep.fits[0].n_points == 90


def test_assess_vdw_detail_reports_sources() -> None:
    rep = ar.assess_radii_policy(['Pm', 'O'], policy=ar.DEFAULT_VDW_POLICY, detail=True)
    by_sym = {d.symbol: d for d in rep.per_element}
    assert by_sym['O'].lookup.source == 'base'
    assert by_sym['Pm'].lookup.source == 'transfer_linear'


def test_assess_covalent_sub_placeholder_count() -> None:
    rep = ar.assess_radii_policy(['Es'], policy=ar.DEFAULT_COVALENT_POLICY)
    assert rep.kind == 'covalent'
    assert rep.n_elements == 1
    assert rep.n_transfer_substitution == 1
    assert rep.n_placeholders == 1
    assert rep.placeholder_symbols == ('Es',)
    assert rep.n_missing == 0


def test_assess_covalent_missing_in_both_sets() -> None:
    rep = ar.assess_radii_policy(['Rg'], policy=ar.DEFAULT_COVALENT_POLICY)
    assert rep.n_missing == 1
    assert rep.missing_symbols == ('Rg',)
