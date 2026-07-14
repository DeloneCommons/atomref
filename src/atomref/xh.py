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
    get_dataset_info,
    list_dataset_ids,
    list_dataset_infos,
    resolve_scalar_dataset_like,
)
from .transfer import LinearTransfer, TransferModel

XHSet = ElementScalarSet
"""Typing alias for an immutable parent-element X-H bond-length dataset."""

_QUANTITY = "xh_bond_length"


@dataclass(frozen=True, slots=True)
class XHPolicy:
    """Policy wrapper specialized for parent-element X-H bond lengths.

    Attributes:
        base_set: Packaged X-H set ID or custom
            [ElementScalarSet][atomref.registry.ElementScalarSet].
        transfers: Ordered substitution or linear-transfer rules. Defaults to
            no transfers.
        overrides: Explicit finite, nonnegative parent-element values checked
            before the base set. Defaults to an empty mapping.
        fallback: Final finite, nonnegative value, or `None`. Defaults to `None`.

    Examples:
        >>> policy = XHPolicy(base_set="csd_legacy_xh_cno")
        >>> get_xh_bond_length("C", policy=policy)
        1.089

    Notes:
        The quantity key is fixed to ``"xh_bond_length"`` and uses parent
        element X as its lookup key. H, D, and T are not valid parent elements.
        Packaged values are in angstrom. Custom sources and policy values must
        use compatible units because policies perform no unit conversion.
    """

    base_set: str | XHSet
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[str, float] = field(default_factory=dict)
    fallback: float | None = None

    def as_value_policy(self) -> ValuePolicy[str]:
        """Convert this wrapper into the generic scalar policy.

        Returns:
            An element-domain [ValuePolicy][atomref.policy.ValuePolicy] with
            hydrogen blocked as a parent.

        Raises:
            DatasetError: If a packaged set is unknown or non-scalar.
            PolicyError: If the base quantity, override, or fallback is invalid,
                or if H/D/T is used as an override parent.
        """

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
    """List packaged X-H set IDs.

    Args:
        usage_role: Optional case-insensitive metadata-role filter.

    Returns:
        Canonical set IDs in curated registry order.

    Raises:
        DatasetError: If registry metadata is malformed.
    """

    return list_dataset_ids(_QUANTITY, usage_role=usage_role)


def list_xh_set_infos(*, usage_role: str | None = None) -> tuple[DatasetInfo, ...]:
    """Return packaged metadata objects for X-H sets.

    Args:
        usage_role: Optional case-insensitive metadata-role filter.

    Returns:
        Immutable [DatasetInfo][atomref.registry.DatasetInfo] objects in curated
        registry order.

    Raises:
        DatasetError: If registry metadata is malformed.
    """

    return list_dataset_infos(_QUANTITY, usage_role=usage_role)


def get_xh_set_info(set_id: str) -> DatasetInfo:
    """Return metadata for one packaged X-H set.

    Args:
        set_id: Canonical packaged set ID or accepted alias.

    Returns:
        Curated metadata, including angstrom units and provenance.

    Raises:
        DatasetError: If the set is unknown or metadata is malformed.
    """

    return get_dataset_info(DatasetRef(_QUANTITY, set_id))


def get_xh_set(set_id: str) -> XHSet:
    """Load one packaged X-H set as an
    [ElementScalarSet][atomref.registry.ElementScalarSet].

    Args:
        set_id: Canonical packaged set ID or accepted alias.

    Returns:
        A cached immutable parent-element set in angstrom.

    Raises:
        DatasetError: If the set is unknown, malformed, or non-scalar.
    """

    return resolve_scalar_dataset_like(DatasetRef(_QUANTITY, set_id))


def lookup_xh_bond_length(
    symbol: str | None,
    *,
    policy: XHPolicy | None = None,
) -> LookupResult:
    """Resolve a parent-element X-H bond length with provenance.

    Args:
        symbol: Parent-element token, or `None`. H/D/T are explicitly blocked.
        policy: X-H policy; `None` selects
            [DEFAULT_XH_POLICY][atomref.DEFAULT_XH_POLICY].

    Returns:
        Lookup result whose value is in angstrom, or an explicit missing result.
        A blocked hydrogen parent includes an explanatory note.

    Raises:
        DatasetError: If a referenced dataset is unknown or non-scalar.
        PolicyError: If policy or transfer configuration is invalid.

    Examples:
        >>> result = lookup_xh_bond_length("C")
        >>> result.value, result.source
        (1.089, 'base')
    """

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
    """Return only the selected parent-element X-H bond length.

    Args:
        symbol: Parent-element token, or `None`. H/D/T are explicitly blocked.
        policy: X-H policy; `None` selects
            [DEFAULT_XH_POLICY][atomref.DEFAULT_XH_POLICY].

    Returns:
        Selected bond length in angstrom, or `None` when resolution is missing.

    Raises:
        DatasetError: If a referenced dataset is unknown or non-scalar.
        PolicyError: If policy or transfer configuration is invalid.
    """

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
