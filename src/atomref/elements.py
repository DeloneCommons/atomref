"""Periodic-table access for stable element identity."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


_MISSING_TOKENS = {"", "?", "."}
_LEADING_ALPHA_RE = re.compile(r"([A-Za-z]{1,3})")


@dataclass(frozen=True, slots=True)
class Element:
    """Chemical element identity keyed by atomic number and symbol.

    Attributes:
        z: Atomic number. Packaged elements span 1 (H) through 118 (Og).
        symbol: Conventional case-sensitive element symbol.
        name: English element name.

    Examples:
        >>> get_element("cl")
        Element(z=17, symbol='Cl', name='Chlorine')
    """

    z: int
    symbol: str
    name: str


def _normalize_element_token(token: str | None) -> str | None:
    """Strip quotes and obvious missing-value markers from a token."""

    if token is None:
        return None

    raw = token.strip()
    if raw in _MISSING_TOKENS:
        return None

    if (raw.startswith("'") and raw.endswith("'")) or (
        raw.startswith('"') and raw.endswith('"')
    ):
        raw = raw[1:-1].strip()
        if raw in _MISSING_TOKENS:
            return None

    if not raw:
        return None
    return raw


def canonicalize_element_symbol(token: str | None) -> str | None:
    """Canonicalize a free-form token to a conventional element symbol.

    The function accepts strings such as ``"cl"``, ``" Cl "`` or
    ``"Cl12"`` and returns ``"Cl"`` when a leading element-like token can be
    identified. It normalizes spelling but does not validate that the result is
    a known element.

    Args:
        token: Free-form token, or `None`. Empty strings and the missing-value
            markers ``"?"`` and ``"."`` are treated as missing.

    Returns:
        A conventionally capitalized leading element-like token, or `None` if
        no such token is present.

    Examples:
        >>> canonicalize_element_symbol(" Cl12 ")
        'Cl'
        >>> canonicalize_element_symbol("?") is None
        True

    Notes:
        Call
        [is_valid_element_symbol][atomref.elements.is_valid_element_symbol] or
        [get_element][atomref.elements.get_element] when membership in the
        packaged periodic table must also be checked.
    """

    raw = _normalize_element_token(token)
    if raw is None:
        return None

    match = _LEADING_ALPHA_RE.match(raw)
    if match is None:
        return None

    letters = match.group(1)
    return letters[0].upper() + letters[1:].lower()


@lru_cache(maxsize=1)
def _load_elements_by_symbol() -> dict[str, Element]:
    """Load the packaged periodic table into a symbol-keyed mapping."""

    table_path = resources.files("atomref.data").joinpath("periodic_table.csv")
    with io.TextIOWrapper(
        table_path.open("rb"), encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        out: dict[str, Element] = {}
        for row in reader:
            z = int(row["z"])
            symbol = row["symbol"]
            name = row["name"]
            out[symbol] = Element(z=z, symbol=symbol, name=name)
    return out


@lru_cache(maxsize=1)
def _elements_in_z_order() -> tuple[Element, ...]:
    """Return packaged elements sorted by increasing atomic number."""

    return tuple(sorted(_load_elements_by_symbol().values(), key=lambda e: e.z))


def is_valid_element_symbol(symbol: str | None) -> bool:
    """Check whether a canonical symbol is present in the periodic table.

    Args:
        symbol: Case-sensitive canonical symbol, or `None`.

    Returns:
        `True` only for an exact packaged symbol. This function does not trim or
        canonicalize its argument.

    Examples:
        >>> is_valid_element_symbol("Cl")
        True
        >>> is_valid_element_symbol("cl")
        False
    """

    if symbol is None:
        return False
    return symbol in _load_elements_by_symbol()


def get_element(symbol: str | None) -> Element | None:
    """Look up packaged element identity from a symbol-like token.

    Args:
        symbol: Free-form symbol token accepted by
            [canonicalize_element_symbol][atomref.elements.canonicalize_element_symbol],
            or `None`.

    Returns:
        The matching immutable [Element][atomref.elements.Element], or `None` if
        the token is missing or does not identify a packaged element.

    Examples:
        >>> get_element(" Cl12 ").z
        17
        >>> get_element("not-an-element") is None
        True
    """

    sym = canonicalize_element_symbol(symbol)
    if sym is None:
        return None
    return _load_elements_by_symbol().get(sym)


def iter_elements() -> tuple[Element, ...]:
    """Return all packaged elements in increasing atomic-number order.

    Returns:
        An immutable tuple containing H through Og, ordered by atomic number.

    Examples:
        >>> elements = iter_elements()
        >>> elements[0].symbol, elements[-1].symbol
        ('H', 'Og')
    """

    return _elements_in_z_order()
