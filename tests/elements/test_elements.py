from __future__ import annotations

import atomref as ar


def test_element_lookup_and_validation() -> None:
    assert ar.is_valid_element_symbol('C')
    assert ar.is_valid_element_symbol('cl') is False
    assert ar.get_element('cl') is not None
    assert ar.get_element('C').z == 6
    assert ar.get_element('Xx') is None


def test_iter_elements_is_sorted_and_complete() -> None:
    elems = ar.iter_elements()
    assert elems[0].symbol == 'H'
    assert elems[-1].symbol == 'Og'
    assert elems[0].z == 1
    assert elems[-1].z == 118
