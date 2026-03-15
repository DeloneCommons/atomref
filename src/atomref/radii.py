"""Radii-specific public API built on the generic policy core."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import math
from typing import Literal

from .elements import canonicalize_element_symbol, get_element, is_valid_element_symbol
from .errors import PolicyError
from .policy import (
    LookupResult,
    ValuePolicy,
    _fit_transfer_model,
    get_value,
    lookup_value,
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
from .transfer import LinearFit, LinearTransfer, SubstitutionTransfer, TransferModel

RadiiKind = Literal["covalent", "van_der_waals"]
RadiiSet = ElementScalarSet


_KIND_TO_QUANTITY = {
    "covalent": "covalent_radius",
    "van_der_waals": "van_der_waals_radius",
}


@dataclass(frozen=True, slots=True)
class RadiiPolicy:
    """Policy wrapper specialized for radii lookup.

    ``kind`` determines the target quantity, while the remaining fields mirror
    the generic :class:`atomref.policy.ValuePolicy` interface.
    """

    kind: RadiiKind
    base_set: str | RadiiSet
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[str, float] = field(default_factory=dict)
    fallback: float | None = None

    def as_value_policy(self) -> ValuePolicy[str]:
        """Convert the radii policy into the generic scalar-value policy."""

        quantity = _quantity_for_kind(self.kind)
        if isinstance(self.base_set, ElementScalarSet):
            if self.base_set.ref.quantity != quantity:
                msg = (
                    f"base_set quantity {self.base_set.ref.quantity!r} "
                    f"is incompatible with radii kind {self.kind!r}"
                )
                raise PolicyError(msg)
            base = self.base_set
        else:
            base = DatasetRef(quantity, self.base_set)

        checked_overrides = {
            key: _coerce_non_negative_radii_value(
                value,
                what=f"radii override value for {key!r}",
            )
            for key, value in self.overrides.items()
        }
        checked_fallback = (
            None
            if self.fallback is None
            else _coerce_non_negative_radii_value(
                self.fallback,
                what="radii fallback",
            )
        )

        return ValuePolicy(
            base=base,
            transfers=self.transfers,
            overrides=checked_overrides,
            fallback=checked_fallback,
        )


@dataclass(frozen=True, slots=True)
class RadiiElementAssessment:
    """Per-element row in a radii policy assessment report."""

    symbol: str
    lookup: LookupResult


@dataclass(frozen=True, slots=True)
class RadiiPolicyAssessment:
    """Summary of how a radii policy behaved over a set of elements."""

    kind: RadiiKind
    policy: RadiiPolicy
    elements: tuple[str, ...]

    n_elements: int
    n_override: int
    n_base: int
    n_transfer_substitution: int
    n_transfer_linear: int
    n_fallback: int
    n_missing: int
    n_placeholders: int

    missing_symbols: tuple[str, ...]
    placeholder_symbols: tuple[str, ...]

    fits: tuple[LinearFit, ...] = ()
    warnings: tuple[str, ...] = ()
    per_element: tuple[RadiiElementAssessment, ...] = ()


def _coerce_non_negative_radii_value(value: object, *, what: str) -> float:
    """Validate a radii-like policy number.

    The generic :class:`atomref.policy.ValuePolicy` accepts any finite scalar.
    Radii-specific convenience helpers are stricter and reject negative values.
    """

    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{what} must be a finite float") from exc
    if not math.isfinite(out):
        raise PolicyError(f"{what} must be a finite float")
    if out < 0:
        raise PolicyError(f"{what} must be non-negative")
    return out


def _quantity_for_kind(kind: RadiiKind) -> str:
    """Translate public radii kind names into registry quantity ids."""

    try:
        return _KIND_TO_QUANTITY[kind]
    except KeyError as exc:
        raise PolicyError(f"unknown radii kind: {kind!r}") from exc


def _normalize_radii_symbol(symbol: str | None) -> str | None:
    """Normalize symbols accepted by the radii convenience layer."""

    cand = canonicalize_element_symbol(symbol)
    if cand in {"D", "T"}:
        cand = "H"
    return cand


def _normalize_assessment_elements(elements: Iterable[str]) -> tuple[str, ...]:
    """Normalize, validate, deduplicate, and sort assessment element labels."""

    symbols: set[str] = set()
    for token in elements:
        sym = _normalize_radii_symbol(token)
        if sym is None:
            raise ValueError("missing element symbol")
        if not is_valid_element_symbol(sym):
            raise ValueError(f"invalid element symbol: {sym!r}")
        symbols.add(sym)
    return tuple(
        sorted(symbols, key=lambda s: get_element(s).z if get_element(s) else 0)
    )


def list_radii_sets(
    kind: RadiiKind,
    *,
    usage_role: str | None = None,
) -> tuple[str, ...]:
    """List packaged radii-set ids for one radii kind."""

    return list_dataset_ids(_quantity_for_kind(kind), usage_role=usage_role)


def list_radii_set_infos(
    kind: RadiiKind,
    *,
    usage_role: str | None = None,
) -> tuple[DatasetInfo, ...]:
    """Return packaged metadata objects for radii sets of one kind."""

    return list_dataset_infos(_quantity_for_kind(kind), usage_role=usage_role)


def get_radii_set_info(kind: RadiiKind, set_id: str) -> DatasetInfo:
    """Return metadata for one packaged radii set."""

    return get_dataset_info(DatasetRef(_quantity_for_kind(kind), set_id))


def get_radii_set(kind: RadiiKind, set_id: str) -> RadiiSet:
    """Load one packaged radii set as an :class:`ElementScalarSet`."""

    return get_builtin_set(DatasetRef(_quantity_for_kind(kind), set_id))


def _validate_policy_kind(policy: RadiiPolicy, *, expected: RadiiKind) -> None:
    """Raise when a policy is used with the wrong public radii helper."""

    if policy.kind != expected:
        raise PolicyError(f"expected a {expected!r} radii policy, got {policy.kind!r}")


def _lookup_radius(symbol: str | None, *, policy: RadiiPolicy) -> LookupResult:
    """Shared implementation for radii lookup helpers."""

    return lookup_value(symbol, policy=policy.as_value_policy())


def lookup_covalent_radius(
    symbol: str | None,
    *,
    policy: RadiiPolicy | None = None,
) -> LookupResult:
    """Resolve a covalent radius together with provenance information."""

    active = DEFAULT_COVALENT_POLICY if policy is None else policy
    _validate_policy_kind(active, expected="covalent")
    return _lookup_radius(symbol, policy=active)


def get_covalent_radius(
    symbol: str | None,
    *,
    policy: RadiiPolicy | None = None,
) -> float | None:
    """Return only the selected covalent-radius value, without provenance."""

    active = DEFAULT_COVALENT_POLICY if policy is None else policy
    _validate_policy_kind(active, expected="covalent")
    return get_value(symbol, policy=active.as_value_policy())


def lookup_vdw_radius(
    symbol: str | None,
    *,
    policy: RadiiPolicy | None = None,
) -> LookupResult:
    """Resolve a van der Waals radius together with provenance information."""

    active = DEFAULT_VDW_POLICY if policy is None else policy
    _validate_policy_kind(active, expected="van_der_waals")
    return _lookup_radius(symbol, policy=active)


def get_vdw_radius(
    symbol: str | None,
    *,
    policy: RadiiPolicy | None = None,
) -> float | None:
    """Return only the selected van der Waals-radius value, without provenance."""

    active = DEFAULT_VDW_POLICY if policy is None else policy
    _validate_policy_kind(active, expected="van_der_waals")
    return get_value(symbol, policy=active.as_value_policy())


def assess_radii_policy(
    elements: Iterable[str],
    *,
    policy: RadiiPolicy,
    detail: bool = False,
) -> RadiiPolicyAssessment:
    """Assess how a radii policy resolves values over a set of elements."""

    elems = _normalize_assessment_elements(elements)
    value_policy = policy.as_value_policy()

    n_override = 0
    n_base = 0
    n_transfer_substitution = 0
    n_transfer_linear = 0
    n_fallback = 0
    n_missing = 0
    n_placeholders = 0

    missing_symbols: list[str] = []
    placeholder_symbols: list[str] = []
    per_element: list[RadiiElementAssessment] = []

    for symbol in elems:
        lookup = lookup_value(symbol, policy=value_policy)
        if lookup.source == "override":
            n_override += 1
        elif lookup.source == "base":
            n_base += 1
        elif lookup.source == "transfer_substitution":
            n_transfer_substitution += 1
        elif lookup.source == "transfer_linear":
            n_transfer_linear += 1
        elif lookup.source == "fallback":
            n_fallback += 1
        elif lookup.source == "missing":
            n_missing += 1
            missing_symbols.append(symbol)

        if lookup.is_placeholder:
            n_placeholders += 1
            placeholder_symbols.append(symbol)

        if detail:
            per_element.append(RadiiElementAssessment(symbol=symbol, lookup=lookup))

    fits: list[LinearFit] = []
    warnings: list[str] = []
    for transfer in value_policy.transfers:
        if isinstance(transfer, LinearTransfer):
            try:
                fit = _fit_transfer_model(value_policy.base, transfer)
            except Exception as exc:  # noqa: BLE001
                warnings.append(str(exc))
            else:
                if fit is not None:
                    fits.append(fit)

    return RadiiPolicyAssessment(
        kind=policy.kind,
        policy=policy,
        elements=elems,
        n_elements=len(elems),
        n_override=n_override,
        n_base=n_base,
        n_transfer_substitution=n_transfer_substitution,
        n_transfer_linear=n_transfer_linear,
        n_fallback=n_fallback,
        n_missing=n_missing,
        n_placeholders=n_placeholders,
        missing_symbols=tuple(missing_symbols),
        placeholder_symbols=tuple(placeholder_symbols),
        fits=tuple(fits),
        warnings=tuple(warnings),
        per_element=tuple(per_element),
    )


DEFAULT_COVALENT_POLICY = RadiiPolicy(
    kind="covalent",
    base_set="cordero2008",
    transfers=(
        SubstitutionTransfer(source=DatasetRef("covalent_radius", "csd_legacy_cov")),
    ),
)
"""Default covalent-radii policy used by the convenience helpers."""

DEFAULT_VDW_POLICY = RadiiPolicy(
    kind="van_der_waals",
    base_set="alvarez2013",
    transfers=(LinearTransfer(predictors=(DatasetRef("atomic_radius", "rahm2016"),)),),
)
"""Default vdW-radii policy used by the convenience helpers."""
