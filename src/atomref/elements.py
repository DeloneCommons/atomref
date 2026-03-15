"""Periodic-table access for stable element identity."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


_MISSING_TOKENS = {"", "?", "."}
_LEADING_ALPHA_RE = re.compile(r"([A-Za-z]{1,3})")


@dataclass(frozen=True, slots=True)
class Element:
    """Chemical element identity keyed by atomic number and symbol."""

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
    identified. Missing-value markers and non-element strings return ``None``.
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
    with table_path.open("r", encoding="utf-8", newline="") as handle:
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
    """Return ``True`` if ``symbol`` is a known packaged element symbol."""

    if symbol is None:
        return False
    return symbol in _load_elements_by_symbol()


def get_element(symbol: str | None) -> Element | None:
    """Look up packaged element identity from a symbol-like token."""

    sym = canonicalize_element_symbol(symbol)
    if sym is None:
        return None
    return _load_elements_by_symbol().get(sym)


def iter_elements() -> tuple[Element, ...]:
    """Return all packaged elements in increasing atomic-number order."""

    return _elements_in_z_order()
