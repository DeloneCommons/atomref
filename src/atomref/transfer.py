"""Transfer model configuration types."""

from __future__ import annotations

from dataclasses import dataclass

from .registry import DatasetLike


@dataclass(frozen=True, slots=True)
class LinearFit:
    coefficients: tuple[float, ...]
    intercept: float
    n_points: int
    r2: float
    rmse: float


@dataclass(frozen=True, slots=True)
class SubstitutionTransfer:
    source: DatasetLike


@dataclass(frozen=True, slots=True)
class LinearTransfer:
    predictors: tuple[DatasetLike, ...]
    min_points: int = 2
    exclude_placeholders: bool = True


TransferModel = SubstitutionTransfer | LinearTransfer
