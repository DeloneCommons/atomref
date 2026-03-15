"""Generic value-policy resolution for element-indexed scalar datasets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
import math
from types import MappingProxyType
from typing import Generic, Literal, TypeVar

from .elements import (
    canonicalize_element_symbol,
    is_valid_element_symbol,
    iter_elements,
)
from .errors import PolicyError
from .registry import (
    DatasetLike,
    DatasetRef,
    ElementScalarSet,
    _is_placeholder_value,
    get_builtin_set,
    resolve_dataset_like,
)
from .transfer import (
    LinearFit,
    LinearTransfer,
    SubstitutionTransfer,
    SupportsValuePolicy,
    TransferModel,
)

K = TypeVar("K")

LookupSource = Literal[
    "override",
    "base",
    "transfer_substitution",
    "transfer_linear",
    "fallback",
    "missing",
]

_ACTIVE_POLICY_IDS: list[int] = []


@dataclass(frozen=True, slots=True)
class LookupResult:
    """Result of resolving one value through a policy.

    ``value`` carries the final scalar value when one could be produced, while
    ``source`` and the remaining metadata explain how that value was obtained.
    """

    value: float | None
    source: LookupSource
    target: DatasetRef
    resolved_from: tuple[DatasetRef, ...] = ()
    is_placeholder: bool = False
    fit: LinearFit | None = None
    notes: tuple[str, ...] = ()

    def __float__(self) -> float:
        """Coerce the resolved value to ``float`` or raise if it is missing."""

        if self.value is None:
            raise TypeError("reference value is missing")
        return float(self.value)


@dataclass(frozen=True, slots=True)
class ValuePolicy(Generic[K]):
    """Ordered rule set for resolving element-domain scalar values.

    The v0.1 runtime resolves only element-domain policies even though the
    metadata layer already records a more general ``domain`` concept. During
    construction, element-domain override keys are normalized to canonical
    element symbols and validated as finite floats.
    """

    base: DatasetLike
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[K, float] = field(default_factory=dict)
    fallback: float | None = None
    blocked: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and normalize policy configuration eagerly."""

        if self.fallback is not None:
            object.__setattr__(
                self,
                "fallback",
                _coerce_policy_float(self.fallback, what="policy fallback"),
            )

        base_set = resolve_dataset_like(self.base)
        if base_set.info.domain != "element":
            return

        normalized_blocked: list[str] = []
        seen_blocked: set[str] = set()
        for key in self.blocked:
            if not isinstance(key, str):
                raise PolicyError(
                    "element-domain blocked keys must be element-symbol strings"
                )
            sym = _normalize_element_symbol(key)
            if sym is None:
                raise PolicyError(f"invalid blocked element symbol: {key!r}")
            if sym not in seen_blocked:
                normalized_blocked.append(sym)
                seen_blocked.add(sym)
        object.__setattr__(self, "blocked", tuple(normalized_blocked))

        normalized_overrides: dict[str, float] = {}
        seen_original_keys: dict[str, str] = {}
        for key, value in self.overrides.items():
            if not isinstance(key, str):
                raise PolicyError(
                    "element-domain policy overrides must be keyed by element symbols"
                )
            sym = _normalize_element_symbol(key)
            if sym is None:
                raise PolicyError(f"invalid override element symbol: {key!r}")
            if sym in seen_blocked:
                raise PolicyError(f"override key {key!r} is blocked in this policy")
            previous = seen_original_keys.get(sym)
            if previous is not None and previous != key:
                raise PolicyError(
                    f"override keys {previous!r} and {key!r} both normalize to {sym!r}"
                )
            seen_original_keys[sym] = key
            normalized_overrides[sym] = _coerce_policy_float(
                value,
                what=f"override value for {key!r}",
            )

        object.__setattr__(
            self,
            "overrides",
            MappingProxyType(normalized_overrides),
        )


@dataclass(frozen=True, slots=True)
class _ResolvedElementSource:
    """Internal representation of an element-domain transfer source."""

    ref: DatasetRef
    values_by_z: tuple[float | None, ...]
    placeholder_by_z: tuple[bool, ...]
    via_policy: bool = False


@dataclass(frozen=True, slots=True)
class _TransferSourceValue:
    """Internal representation of one value obtained from a transfer source."""

    value: float
    ref: DatasetRef
    resolved_from: tuple[DatasetRef, ...]
    is_placeholder: bool
    via_policy: bool = False
    lookup_source: LookupSource | None = None
    notes: tuple[str, ...] = ()



def _coerce_policy_float(value: object, *, what: str) -> float:
    """Return a finite float for policy configuration values."""

    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{what} must be a finite float") from exc
    if not math.isfinite(out):
        raise PolicyError(f"{what} must be a finite float")
    return out



def _normalize_element_symbol(symbol: str | None) -> str | None:
    """Normalize user input to a packaged element symbol.

    The current resolver treats ``D`` and ``T`` as hydrogen aliases.
    """

    cand = canonicalize_element_symbol(symbol)
    if cand in {"D", "T"}:
        cand = "H"
    if cand is None:
        return None
    if not is_valid_element_symbol(cand):
        return None
    return cand



def _resolve_target_ref(policy: ValuePolicy[object]) -> DatasetRef:
    """Return the target dataset reference implied by a policy base."""

    return resolve_dataset_like(policy.base).ref



def _coerce_nested_policy(source: object) -> ValuePolicy[str] | None:
    """Return ``source`` as a generic value policy when possible."""

    if isinstance(source, ValuePolicy):
        return source
    if isinstance(source, SupportsValuePolicy):
        nested = source.as_value_policy()
        if not isinstance(nested, ValuePolicy):
            raise PolicyError("policy-like transfer sources must return ValuePolicy")
        return nested
    return None



def _materialize_transfer_source(
    source: DatasetLike | SupportsValuePolicy | ValuePolicy[str],
) -> _ResolvedElementSource:
    """Materialize any element-domain transfer source into dense by-Z arrays."""

    nested_policy = _coerce_nested_policy(source)
    if nested_policy is None:
        dataset = resolve_dataset_like(source)
        placeholders = tuple(
            False
            if value is None
            else _is_placeholder_value(dataset.info, float(value))
            for value in dataset.values_by_z
        )
        return _ResolvedElementSource(
            ref=dataset.ref,
            values_by_z=dataset.values_by_z,
            placeholder_by_z=placeholders,
            via_policy=False,
        )

    target = _resolve_target_ref(nested_policy)
    n_z = max(elem.z for elem in iter_elements())
    values: list[float | None] = [None] * (n_z + 1)
    placeholders: list[bool] = [False] * (n_z + 1)
    for elem in iter_elements():
        lookup = lookup_value(elem.symbol, policy=nested_policy)
        values[elem.z] = lookup.value
        placeholders[elem.z] = lookup.is_placeholder if lookup.value is not None else False
    return _ResolvedElementSource(
        ref=target,
        values_by_z=tuple(values),
        placeholder_by_z=tuple(placeholders),
        via_policy=True,
    )



def _lookup_transfer_source_value(
    symbol: str,
    source: DatasetLike | SupportsValuePolicy | ValuePolicy[str],
) -> tuple[_TransferSourceValue | None, str | None]:
    """Resolve one element value from a transfer source or nested policy."""

    nested_policy = _coerce_nested_policy(source)
    if nested_policy is None:
        source_set = resolve_dataset_like(source)
        value = source_set.get(symbol)
        if value is None:
            return None, f"no value in {source_set.ref.set_id}"
        value_f = float(value)
        return (
            _TransferSourceValue(
                value=value_f,
                ref=source_set.ref,
                resolved_from=(source_set.ref,),
                is_placeholder=_is_placeholder_value(source_set.info, value_f),
                via_policy=False,
                lookup_source="base",
                notes=(),
            ),
            None,
        )

    lookup = lookup_value(symbol, policy=nested_policy)
    if lookup.value is None:
        if lookup.notes:
            return (
                None,
                "policy source returned no value: " + "; ".join(lookup.notes),
            )
        return None, "policy source returned no value"

    return (
        _TransferSourceValue(
            value=float(lookup.value),
            ref=_resolve_target_ref(nested_policy),
            resolved_from=lookup.resolved_from,
            is_placeholder=lookup.is_placeholder,
            via_policy=True,
            lookup_source=lookup.source,
            notes=lookup.notes,
        ),
        None,
    )



def _fit_linear_transfer(
    base_set: ElementScalarSet,
    predictor_source: _ResolvedElementSource,
    *,
    min_points: int,
    exclude_placeholders: bool,
) -> LinearFit:
    """Fit a one-predictor linear transfer model between two sources."""

    xs: list[float] = []
    ys: list[float] = []

    n_z = min(len(base_set.values_by_z), len(predictor_source.values_by_z))
    for z in range(1, n_z):
        y = base_set.values_by_z[z]
        x = predictor_source.values_by_z[z]
        if y is None or x is None:
            continue
        y_f = float(y)
        x_f = float(x)
        if exclude_placeholders and (
            _is_placeholder_value(base_set.info, y_f)
            or predictor_source.placeholder_by_z[z]
        ):
            continue
        xs.append(x_f)
        ys.append(y_f)

    n = len(xs)
    if n < min_points:
        raise PolicyError("not enough overlapping elements to fit linear transfer")

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0:
        raise PolicyError("cannot fit linear transfer: zero predictor variance")

    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    y_hat = [slope * x + intercept for x in xs]
    sse = sum((y - yh) ** 2 for y, yh in zip(ys, y_hat))
    sst = sum((y - y_mean) ** 2 for y in ys)
    r2 = 1.0 - sse / sst if sst != 0 else 1.0
    rmse = math.sqrt(sse / n)

    return LinearFit(
        coefficients=(slope,),
        intercept=intercept,
        n_points=n,
        r2=r2,
        rmse=rmse,
    )


@lru_cache(maxsize=None)
def _fit_linear_transfer_cached(
    base_ref: DatasetRef,
    predictor_ref: DatasetRef,
    min_points: int,
    exclude_placeholders: bool,
) -> LinearFit:
    """Cache fits between two packaged datasets for repeated reuse."""

    return _fit_linear_transfer(
        get_builtin_set(base_ref),
        _materialize_transfer_source(predictor_ref),
        min_points=min_points,
        exclude_placeholders=exclude_placeholders,
    )



def _fit_transfer_model(base: DatasetLike, transfer: TransferModel) -> LinearFit | None:
    """Return the fit object for a transfer model when it needs one."""

    if not isinstance(transfer, LinearTransfer):
        return None
    if len(transfer.predictors) != 1:
        raise PolicyError("v0.1 LinearTransfer supports exactly one predictor source")

    predictor = transfer.predictors[0]
    if isinstance(base, DatasetRef) and isinstance(predictor, DatasetRef):
        return _fit_linear_transfer_cached(
            base,
            predictor,
            transfer.min_points,
            transfer.exclude_placeholders,
        )
    return _fit_linear_transfer(
        resolve_dataset_like(base),
        _materialize_transfer_source(predictor),
        min_points=transfer.min_points,
        exclude_placeholders=transfer.exclude_placeholders,
    )



def _apply_substitution_transfer(
    symbol: str,
    *,
    target: DatasetRef,
    transfer: SubstitutionTransfer,
) -> tuple[LookupResult | None, str | None]:
    """Try to resolve ``symbol`` by direct substitution from another source."""

    source_value, note = _lookup_transfer_source_value(symbol, transfer.source)
    if source_value is None:
        return None, note

    notes = [
        "missing in base set; substituted from policy source"
        if source_value.via_policy
        else "missing in base set; substituted from transfer source"
    ]
    if source_value.via_policy and source_value.lookup_source not in (None, "base"):
        notes.append(
            f"policy source resolved the value via {source_value.lookup_source}"
        )
    if source_value.is_placeholder:
        notes.append("transfer source value is marked as a placeholder")
    return (
        LookupResult(
            value=source_value.value,
            source="transfer_substitution",
            target=target,
            resolved_from=source_value.resolved_from,
            is_placeholder=source_value.is_placeholder,
            notes=tuple(notes),
        ),
        None,
    )



def _apply_linear_transfer(
    symbol: str,
    *,
    base: DatasetLike,
    target: DatasetRef,
    transfer: LinearTransfer,
) -> tuple[LookupResult | None, str | None]:
    """Try to resolve ``symbol`` through linear transfer from predictor data."""

    if len(transfer.predictors) != 1:
        raise PolicyError("v0.1 LinearTransfer supports exactly one predictor source")

    predictor_value, note = _lookup_transfer_source_value(symbol, transfer.predictors[0])
    if predictor_value is None:
        return None, note

    if transfer.exclude_placeholders and predictor_value.is_placeholder:
        if predictor_value.via_policy:
            return None, "predictor value from policy source is a placeholder"
        return None, f"predictor value in {predictor_value.ref.set_id} is a placeholder"

    fit = _fit_transfer_model(base, transfer)
    if fit is None:
        return None, "no fit available for linear transfer"
    predicted = fit.coefficients[0] * predictor_value.value + fit.intercept

    notes = ["missing in base set; inferred via linear transfer"]
    if predictor_value.via_policy:
        notes.append("predictor value supplied by policy source")
        notes.append("linear fit used policy-materialized predictor values")
        if predictor_value.lookup_source not in (None, "base"):
            notes.append(
                f"policy predictor resolved the value via {predictor_value.lookup_source}"
            )

    return (
        LookupResult(
            value=float(predicted),
            source="transfer_linear",
            target=target,
            resolved_from=predictor_value.resolved_from,
            is_placeholder=False,
            fit=fit,
            notes=tuple(notes),
        ),
        None,
    )



def _resolve_value(symbol: str | None, *, policy: ValuePolicy[str]) -> LookupResult:
    """Resolve a value through override, base, transfer, and fallback steps."""

    policy_id = id(policy)
    if policy_id in _ACTIVE_POLICY_IDS:
        raise PolicyError("cyclic policy resolution detected")

    _ACTIVE_POLICY_IDS.append(policy_id)
    try:
        target = _resolve_target_ref(policy)
        base_set = resolve_dataset_like(policy.base)
        if base_set.info.domain != "element":
            raise PolicyError("v0.1 resolver supports only element-domain datasets")

        sym = _normalize_element_symbol(symbol)
        if sym is None:
            note = "unknown element" if symbol is not None else "missing element symbol"
            return LookupResult(value=None, source="missing", target=target, notes=(note,))

        if sym in policy.blocked:
            return LookupResult(
                value=None,
                source="missing",
                target=target,
                notes=(f"{sym} is blocked by this policy",),
            )

        if sym in policy.overrides:
            return LookupResult(
                value=float(policy.overrides[sym]),
                source="override",
                target=target,
                notes=("value supplied by policy override",),
            )

        base_value = base_set.get(sym)
        if base_value is not None:
            base_f = float(base_value)
            is_placeholder = _is_placeholder_value(base_set.info, base_f)
            notes = (
                ("base dataset value is marked as a placeholder",)
                if is_placeholder
                else ()
            )
            return LookupResult(
                value=base_f,
                source="base",
                target=target,
                resolved_from=(base_set.ref,),
                is_placeholder=is_placeholder,
                notes=notes,
            )

        transfer_notes: list[str] = ["missing in base set"]
        for transfer in policy.transfers:
            if isinstance(transfer, SubstitutionTransfer):
                result, note = _apply_substitution_transfer(
                    sym,
                    target=target,
                    transfer=transfer,
                )
            elif isinstance(transfer, LinearTransfer):
                result, note = _apply_linear_transfer(
                    sym,
                    base=policy.base,
                    target=target,
                    transfer=transfer,
                )
            else:  # pragma: no cover - closed union today
                raise PolicyError(f"unsupported transfer model: {type(transfer)!r}")

            if result is not None:
                return result
            if note:
                transfer_notes.append(note)

        if policy.fallback is not None:
            return LookupResult(
                value=float(policy.fallback),
                source="fallback",
                target=target,
                notes=tuple(transfer_notes + ["using fallback value"]),
            )

        return LookupResult(
            value=None,
            source="missing",
            target=target,
            notes=tuple(transfer_notes),
        )
    finally:
        popped = _ACTIVE_POLICY_IDS.pop()
        assert popped == policy_id  # internal stack discipline



def lookup_value(symbol: str | None, *, policy: ValuePolicy[str]) -> LookupResult:
    """Public entry point for generic element-domain scalar lookup.

    This is the same resolver used internally by the radii convenience layer.
    In v0.1 the runtime supports only element-domain policies.
    """

    return _resolve_value(symbol, policy=policy)



def get_value(symbol: str | None, *, policy: ValuePolicy[str]) -> float | None:
    """Return only the resolved scalar value for an element-domain policy."""

    return lookup_value(symbol, policy=policy).value
