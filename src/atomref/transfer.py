"""Transfer-model configuration types for policy-based lookup."""

from __future__ import annotations

from dataclasses import dataclass

from .registry import DatasetLike


@dataclass(frozen=True, slots=True)
class LinearFit:
    """Summary statistics for a fitted linear transfer model.

    Parameters are stored in a compact, serializable form so they can be
    attached to :class:`atomref.policy.LookupResult` objects and reused in
    reporting code.
    """

    coefficients: tuple[float, ...]
    intercept: float
    n_points: int
    r2: float
    rmse: float


@dataclass(frozen=True, slots=True)
class SubstitutionTransfer:
    """Use another dataset directly when the base dataset is missing a value."""

    source: DatasetLike


@dataclass(frozen=True, slots=True)
class LinearTransfer:
    """Infer missing target values from one or more predictor datasets.

    In v0.1 the public API stores predictors as a tuple for forward
    compatibility, but the runtime implementation intentionally accepts exactly
    one predictor dataset.
    """

    predictors: tuple[DatasetLike, ...]
    min_points: int = 2
    exclude_placeholders: bool = True


TransferModel = SubstitutionTransfer | LinearTransfer
"""Closed union of transfer models supported by the core resolver."""
