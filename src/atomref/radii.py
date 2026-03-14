"""Radii-specific public API built on the generic policy core."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Literal

from .elements import canonicalize_element_symbol, get_element, is_valid_element_symbol
from .errors import PolicyError
from .policy import LookupResult, ValuePolicy, _fit_transfer_model, _resolve_value
from .registry import DatasetInfo, DatasetRef, ElementScalarSet, get_dataset_info, list_dataset_ids
from .transfer import LinearFit, LinearTransfer, SubstitutionTransfer, TransferModel


RadiiKind = Literal['covalent', 'van_der_waals']
RadiiSet = ElementScalarSet


_KIND_TO_QUANTITY = {
    'covalent': 'covalent_radius',
    'van_der_waals': 'van_der_waals_radius',
}


@dataclass(frozen=True, slots=True)
class RadiiPolicy:
    kind: RadiiKind
    base_set: str | RadiiSet
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[str, float] = field(default_factory=dict)
    fallback: float | None = None

    def as_value_policy(self) -> ValuePolicy[str]:
        quantity = _quantity_for_kind(self.kind)
        if isinstance(self.base_set, ElementScalarSet):
            if self.base_set.ref.quantity != quantity:
                raise PolicyError(
                    f'base_set quantity {self.base_set.ref.quantity!r} is incompatible with radii kind {self.kind!r}'
                )
            base = self.base_set
        else:
            base = DatasetRef(quantity, self.base_set)

        normalized_overrides: dict[str, float] = {}
        for key, value in self.overrides.items():
            sym = _normalize_radii_symbol(key)
            if sym is None or not is_valid_element_symbol(sym):
                raise PolicyError(f'invalid override element symbol: {key!r}')
            normalized_overrides[sym] = float(value)

        return ValuePolicy(
            base=base,
            transfers=self.transfers,
            overrides=normalized_overrides,
            fallback=self.fallback,
        )


@dataclass(frozen=True, slots=True)
class RadiiElementAssessment:
    symbol: str
    lookup: LookupResult


@dataclass(frozen=True, slots=True)
class RadiiPolicyAssessment:
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


def _quantity_for_kind(kind: RadiiKind) -> str:
    try:
        return _KIND_TO_QUANTITY[kind]
    except KeyError as exc:
        raise PolicyError(f'unknown radii kind: {kind!r}') from exc


def _normalize_radii_symbol(symbol: str | None) -> str | None:
    cand = canonicalize_element_symbol(symbol)
    if cand in {'D', 'T'}:
        cand = 'H'
    return cand


def _normalize_assessment_elements(elements: Iterable[str]) -> tuple[str, ...]:
    symbols: set[str] = set()
    for token in elements:
        sym = _normalize_radii_symbol(token)
        if sym is None:
            raise ValueError('missing element symbol')
        if not is_valid_element_symbol(sym):
            raise ValueError(f'invalid element symbol: {sym!r}')
        symbols.add(sym)
    return tuple(sorted(symbols, key=lambda s: get_element(s).z if get_element(s) else 0))


def list_radii_sets(kind: RadiiKind) -> tuple[str, ...]:
    return list_dataset_ids(_quantity_for_kind(kind))


def get_radii_set_info(kind: RadiiKind, set_id: str) -> DatasetInfo:
    return get_dataset_info(DatasetRef(_quantity_for_kind(kind), set_id))


def _validate_policy_kind(policy: RadiiPolicy, *, expected: RadiiKind) -> None:
    if policy.kind != expected:
        raise PolicyError(f'expected a {expected!r} radii policy, got {policy.kind!r}')


def _lookup_radius(symbol: str | None, *, policy: RadiiPolicy) -> LookupResult:
    return _resolve_value(symbol, policy=policy.as_value_policy())


def lookup_covalent_radius(symbol: str | None, *, policy: RadiiPolicy | None = None) -> LookupResult:
    active = DEFAULT_COVALENT_POLICY if policy is None else policy
    _validate_policy_kind(active, expected='covalent')
    return _lookup_radius(symbol, policy=active)


def get_covalent_radius(symbol: str | None, *, policy: RadiiPolicy | None = None) -> float | None:
    return lookup_covalent_radius(symbol, policy=policy).value


def lookup_vdw_radius(symbol: str | None, *, policy: RadiiPolicy | None = None) -> LookupResult:
    active = DEFAULT_VDW_POLICY if policy is None else policy
    _validate_policy_kind(active, expected='van_der_waals')
    return _lookup_radius(symbol, policy=active)


def get_vdw_radius(symbol: str | None, *, policy: RadiiPolicy | None = None) -> float | None:
    return lookup_vdw_radius(symbol, policy=policy).value


def assess_radii_policy(elements: Iterable[str], *, policy: RadiiPolicy, detail: bool = False) -> RadiiPolicyAssessment:
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
        lookup = _resolve_value(symbol, policy=value_policy)
        if lookup.source == 'override':
            n_override += 1
        elif lookup.source == 'base':
            n_base += 1
        elif lookup.source == 'transfer_substitution':
            n_transfer_substitution += 1
        elif lookup.source == 'transfer_linear':
            n_transfer_linear += 1
        elif lookup.source == 'fallback':
            n_fallback += 1
        elif lookup.source == 'missing':
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
    kind='covalent',
    base_set='cordero2008',
    transfers=(SubstitutionTransfer(source=DatasetRef('covalent_radius', 'csd_legacy_cov')),),
)

DEFAULT_VDW_POLICY = RadiiPolicy(
    kind='van_der_waals',
    base_set='alvarez2013',
    transfers=(LinearTransfer(predictors=(DatasetRef('atomic_radius', 'rahm2016'),)),),
)
