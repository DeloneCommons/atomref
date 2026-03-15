"""X-H bond-length helpers built on the generic policy core."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math

from .elements import canonicalize_element_symbol, is_valid_element_symbol
from .errors import PolicyError
from .policy import (
    LookupResult,
    ValuePolicy,
    _get_value_from_policy_source,
    _lookup_value_from_policy_source,
)
from .registry import (
    DatasetInfo,
    DatasetRef,
    ElementScalarSet,
    get_builtin_set,
    get_dataset_info,
    list_dataset_ids,
    list_dataset_infos,
)
from .transfer import LinearTransfer, TransferModel

XHSet = ElementScalarSet

_QUANTITY = "xh_bond_length"


@dataclass(frozen=True, slots=True)
class XHPolicy:
    """Policy wrapper specialized for parent-element X-H bond lengths.

    The quantity key is fixed to ``"xh_bond_length"`` and uses the parent
    element ``X`` as the lookup key. ``H`` itself is not considered a valid
    parent element for this quantity.
    """

    base_set: str | XHSet
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[str, float] = field(default_factory=dict)
    fallback: float | None = None

    def as_value_policy(self) -> ValuePolicy[str]:
        """Convert the X-H policy into the generic scalar-value policy."""

        if isinstance(self.base_set, ElementScalarSet):
            if self.base_set.ref.quantity != _QUANTITY:
                raise PolicyError(
                    "base_set quantity "
                    f"{self.base_set.ref.quantity!r} is incompatible "
                    "with X-H lookup"
                )
            base = self.base_set
        else:
            base = DatasetRef(_QUANTITY, self.base_set)

        checked_overrides: dict[str, float] = {}
        for key, value in self.overrides.items():
            sym = _normalize_xh_symbol(key)
            if sym is None or not is_valid_element_symbol(sym):
                raise PolicyError(f"invalid X-H parent element symbol: {key!r}")
            if sym == "H":
                raise PolicyError("H is not a valid parent element for xh_bond_length")
            checked_overrides[key] = _coerce_non_negative_xh_value(
                value,
                what=f"X-H override value for {key!r}",
            )

        checked_fallback = (
            None
            if self.fallback is None
            else _coerce_non_negative_xh_value(self.fallback, what="X-H fallback")
        )

        return ValuePolicy(
            base=base,
            transfers=self.transfers,
            overrides=checked_overrides,
            fallback=checked_fallback,
            blocked=("H",),
        )


def _coerce_non_negative_xh_value(value: object, *, what: str) -> float:
    """Validate an X-H-like policy number."""

    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{what} must be a finite float") from exc
    if not math.isfinite(out):
        raise PolicyError(f"{what} must be a finite float")
    if out < 0:
        raise PolicyError(f"{what} must be non-negative")
    return out


def _normalize_xh_symbol(symbol: str | None) -> str | None:
    """Normalize symbols accepted by the X-H convenience layer."""

    cand = canonicalize_element_symbol(symbol)
    if cand in {"D", "T"}:
        cand = "H"
    return cand


def list_xh_sets(*, usage_role: str | None = None) -> tuple[str, ...]:
    """List packaged X-H set ids."""

    return list_dataset_ids(_QUANTITY, usage_role=usage_role)


def list_xh_set_infos(*, usage_role: str | None = None) -> tuple[DatasetInfo, ...]:
    """Return packaged metadata objects for X-H sets."""

    return list_dataset_infos(_QUANTITY, usage_role=usage_role)


def get_xh_set_info(set_id: str) -> DatasetInfo:
    """Return metadata for one packaged X-H set."""

    return get_dataset_info(DatasetRef(_QUANTITY, set_id))


def get_xh_set(set_id: str) -> XHSet:
    """Load one packaged X-H set as an :class:`ElementScalarSet`."""

    return get_builtin_set(DatasetRef(_QUANTITY, set_id))


def lookup_xh_bond_length(
    symbol: str | None,
    *,
    policy: XHPolicy | None = None,
) -> LookupResult:
    """Resolve a parent-element X-H bond length with provenance."""

    active = DEFAULT_XH_POLICY if policy is None else policy
    lookup = _lookup_value_from_policy_source(symbol, source=active)
    if lookup.value is None and _normalize_xh_symbol(symbol) == "H":
        return LookupResult(
            value=None,
            source="missing",
            target=lookup.target,
            notes=("H is not a valid parent element for xh_bond_length",),
        )
    return lookup


def get_xh_bond_length(
    symbol: str | None,
    *,
    policy: XHPolicy | None = None,
) -> float | None:
    """Return only the selected X-H bond-length value, without provenance."""

    active = DEFAULT_XH_POLICY if policy is None else policy
    return _get_value_from_policy_source(symbol, source=active)


DEFAULT_XH_POLICY = XHPolicy(
    base_set="csd_legacy_xh_cno",
    transfers=(
        LinearTransfer(
            predictors=(DatasetRef("covalent_radius", "cordero2008"),),
            min_points=3,
            exclude_placeholders=True,
        ),
    ),
)
"""Default X-H policy used by the convenience helpers."""
