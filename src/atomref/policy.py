"""Generic value-policy resolution for element-indexed scalar datasets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
import math
from typing import Generic, Literal, TypeVar

from .elements import canonicalize_element_symbol, get_element, is_valid_element_symbol
from .errors import PolicyError
from .registry import (
    DatasetLike,
    DatasetRef,
    ElementScalarSet,
    _is_placeholder_value,
    get_builtin_set,
    resolve_dataset_like,
)
from .transfer import LinearFit, LinearTransfer, SubstitutionTransfer, TransferModel


K = TypeVar('K')

LookupSource = Literal[
    'override',
    'base',
    'transfer_substitution',
    'transfer_linear',
    'fallback',
    'missing',
]


@dataclass(frozen=True, slots=True)
class LookupResult:
    value: float | None
    source: LookupSource
    target: DatasetRef
    resolved_from: tuple[DatasetRef, ...] = ()
    is_placeholder: bool = False
    fit: LinearFit | None = None
    notes: tuple[str, ...] = ()

    def __float__(self) -> float:
        if self.value is None:
            raise TypeError('reference value is missing')
        return float(self.value)


@dataclass(frozen=True, slots=True)
class ValuePolicy(Generic[K]):
    base: DatasetLike
    transfers: tuple[TransferModel, ...] = ()
    overrides: Mapping[K, float] = field(default_factory=dict)
    fallback: float | None = None


def _normalize_element_symbol(symbol: str | None) -> str | None:
    cand = canonicalize_element_symbol(symbol)
    if cand in {'D', 'T'}:
        cand = 'H'
    if cand is None:
        return None
    if not is_valid_element_symbol(cand):
        return None
    return cand


def _resolve_target_ref(policy: ValuePolicy[object]) -> DatasetRef:
    return resolve_dataset_like(policy.base).ref


def _fit_linear_transfer(base_set: ElementScalarSet, predictor_set: ElementScalarSet, *, min_points: int, exclude_placeholders: bool) -> LinearFit:
    xs: list[float] = []
    ys: list[float] = []

    n_z = min(len(base_set.values_by_z), len(predictor_set.values_by_z))
    for z in range(1, n_z):
        y = base_set.values_by_z[z]
        x = predictor_set.values_by_z[z]
        if y is None or x is None:
            continue
        y_f = float(y)
        x_f = float(x)
        if exclude_placeholders and (
            _is_placeholder_value(base_set.info, y_f)
            or _is_placeholder_value(predictor_set.info, x_f)
        ):
            continue
        xs.append(x_f)
        ys.append(y_f)

    n = len(xs)
    if n < min_points:
        raise PolicyError('not enough overlapping elements to fit linear transfer')

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0:
        raise PolicyError('cannot fit linear transfer: zero predictor variance')

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
def _fit_linear_transfer_cached(base_ref: DatasetRef, predictor_ref: DatasetRef, min_points: int, exclude_placeholders: bool) -> LinearFit:
    return _fit_linear_transfer(
        get_builtin_set(base_ref),
        get_builtin_set(predictor_ref),
        min_points=min_points,
        exclude_placeholders=exclude_placeholders,
    )


def _fit_transfer_model(base: DatasetLike, transfer: TransferModel) -> LinearFit | None:
    if not isinstance(transfer, LinearTransfer):
        return None
    if len(transfer.predictors) != 1:
        raise PolicyError('v0.1 LinearTransfer supports exactly one predictor dataset')

    predictor = transfer.predictors[0]
    if isinstance(base, DatasetRef) and isinstance(predictor, DatasetRef):
        return _fit_linear_transfer_cached(
            base, predictor, transfer.min_points, transfer.exclude_placeholders
        )
    return _fit_linear_transfer(
        resolve_dataset_like(base),
        resolve_dataset_like(predictor),
        min_points=transfer.min_points,
        exclude_placeholders=transfer.exclude_placeholders,
    )


def _apply_substitution_transfer(symbol: str, *, target: DatasetRef, transfer: SubstitutionTransfer) -> tuple[LookupResult | None, str | None]:
    source_set = resolve_dataset_like(transfer.source)
    value = source_set.get(symbol)
    if value is None:
        return None, f'no substitution value in {source_set.ref.set_id}'
    value_f = float(value)
    return (
        LookupResult(
            value=value_f,
            source='transfer_substitution',
            target=target,
            resolved_from=(source_set.ref,),
            is_placeholder=_is_placeholder_value(source_set.info, value_f),
            notes=('missing in base set; substituted from transfer source',),
        ),
        None,
    )


def _apply_linear_transfer(symbol: str, *, base: DatasetLike, target: DatasetRef, transfer: LinearTransfer) -> tuple[LookupResult | None, str | None]:
    if len(transfer.predictors) != 1:
        raise PolicyError('v0.1 LinearTransfer supports exactly one predictor dataset')

    predictor_set = resolve_dataset_like(transfer.predictors[0])
    predictor_value = predictor_set.get(symbol)
    if predictor_value is None:
        return None, f'no predictor value in {predictor_set.ref.set_id}'
    predictor_f = float(predictor_value)

    if transfer.exclude_placeholders and _is_placeholder_value(predictor_set.info, predictor_f):
        return None, f'predictor value in {predictor_set.ref.set_id} is a placeholder'

    fit = _fit_transfer_model(base, transfer)
    if fit is None:
        return None, 'no fit available for linear transfer'
    predicted = fit.coefficients[0] * predictor_f + fit.intercept
    return (
        LookupResult(
            value=float(predicted),
            source='transfer_linear',
            target=target,
            resolved_from=(predictor_set.ref,),
            is_placeholder=False,
            fit=fit,
            notes=('missing in base set; inferred via linear transfer',),
        ),
        None,
    )


def _resolve_value(symbol: str | None, *, policy: ValuePolicy[str]) -> LookupResult:
    target = _resolve_target_ref(policy)
    base_set = resolve_dataset_like(policy.base)
    if base_set.info.domain != 'element':
        raise PolicyError('v0.1 resolver supports only element-domain datasets')

    sym = _normalize_element_symbol(symbol)
    if sym is None:
        note = 'unknown element' if symbol is not None else 'missing element symbol'
        return LookupResult(value=None, source='missing', target=target, notes=(note,))

    if sym in policy.overrides:
        return LookupResult(
            value=float(policy.overrides[sym]),
            source='override',
            target=target,
            notes=('value supplied by policy override',),
        )

    base_value = base_set.get(sym)
    if base_value is not None:
        base_f = float(base_value)
        return LookupResult(
            value=base_f,
            source='base',
            target=target,
            resolved_from=(base_set.ref,),
            is_placeholder=_is_placeholder_value(base_set.info, base_f),
            notes=(),
        )

    transfer_notes: list[str] = ['missing in base set']
    for transfer in policy.transfers:
        if isinstance(transfer, SubstitutionTransfer):
            result, note = _apply_substitution_transfer(sym, target=target, transfer=transfer)
        elif isinstance(transfer, LinearTransfer):
            result, note = _apply_linear_transfer(sym, base=policy.base, target=target, transfer=transfer)
        else:  # pragma: no cover - closed union today
            raise PolicyError(f'unsupported transfer model: {type(transfer)!r}')

        if result is not None:
            return result
        if note:
            transfer_notes.append(note)

    if policy.fallback is not None:
        return LookupResult(
            value=float(policy.fallback),
            source='fallback',
            target=target,
            notes=tuple(transfer_notes + ['using fallback value']),
        )

    return LookupResult(
        value=None,
        source='missing',
        target=target,
        notes=tuple(transfer_notes),
    )
