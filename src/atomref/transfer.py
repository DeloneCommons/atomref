"""Transfer-model configuration types for policy-based lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, TypeGuard, runtime_checkable

from .errors import PolicyError
from .registry import ScalarDatasetLike

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .policy import ValuePolicy


TransferValueSource = Literal[
    "override",
    "base",
    "transfer_substitution",
    "transfer_linear",
    "fallback",
]
"""Source labels admitted into nested linear-transfer workflows."""

_ALLOWED_TRANSFER_VALUE_SOURCES = frozenset(
    {
        "override",
        "base",
        "transfer_substitution",
        "transfer_linear",
        "fallback",
    }
)

_DEFAULT_LINEAR_FIT_SOURCES: tuple[TransferValueSource, ...] = (
    "base",
    "override",
)
_DEFAULT_LINEAR_PREDICTION_SOURCES: tuple[TransferValueSource, ...] = (
    "base",
    "override",
    "transfer_substitution",
    "transfer_linear",
)


def _is_transfer_value_source(source: str) -> TypeGuard[TransferValueSource]:
    """Return whether ``source`` is an admitted nested-result label."""

    return source in _ALLOWED_TRANSFER_VALUE_SOURCES


@runtime_checkable
class SupportsValuePolicy(Protocol):
    """Protocol for wrappers that expose a generic scalar value policy.

    Notes:
        [RadiiPolicy][atomref.RadiiPolicy] and [XHPolicy][atomref.XHPolicy]
        implement this structural protocol. Custom wrappers need not inherit
        from it; providing a compatible `as_value_policy()` method is enough.
    """

    def as_value_policy(self) -> "ValuePolicy[str]":
        """Return the generic element-domain value policy.

        Returns:
            A [ValuePolicy][atomref.ValuePolicy] over canonical element symbols.
        """


@dataclass(frozen=True, slots=True)
class LinearFit:
    """Summary statistics for a fitted linear transfer model.

    Parameters are stored in a compact, serializable form so they can be
    attached to [LookupResult][atomref.LookupResult] objects and reused in
    reporting code.

    Attributes:
        coefficients: Fitted slopes, one per predictor. The current runtime
            uses exactly one predictor. Units are target units divided by the
            corresponding predictor units.
        intercept: Fitted intercept in target-dataset units.
        n_points: Number of overlapping element values used in the fit.
        r2: Dimensionless coefficient of determination.
        rmse: Root-mean-square residual in target-dataset units.
    """

    coefficients: tuple[float, ...]
    intercept: float
    n_points: int
    r2: float
    rmse: float


@dataclass(frozen=True, slots=True)
class SubstitutionTransfer:
    """Use another dataset or policy directly when the base dataset is missing.

    The selected value is copied from the source rather than inferred.

    Attributes:
        source: Packaged scalar reference, custom
            [ElementScalarSet][atomref.registry.ElementScalarSet], generic
            [ValuePolicy][atomref.ValuePolicy], or compatible wrapper policy.

    Examples:
        >>> from atomref import DatasetRef, SubstitutionTransfer
        >>> transfer = SubstitutionTransfer(
        ...     source=DatasetRef("covalent_radius", "csd_legacy_cov")
        ... )

    Notes:
        Source and target values must use compatible units. The policy engine
        does not perform dimensional conversion.
    """

    source: ScalarDatasetLike | SupportsValuePolicy | ValuePolicy[str]


@dataclass(frozen=True, slots=True)
class LinearTransfer:
    """Infer missing target values from one or more predictor datasets or policies.

    In the current implementation the public API stores predictors as a tuple
    for forward compatibility, but the runtime intentionally accepts exactly one
    predictor source.

    Attributes:
        predictors: Predictor sources. The tuple must be nonempty, and the
            current resolver supports exactly one predictor at evaluation time.
        min_points: Minimum overlapping fit values. Must be at least 2 and
            defaults to 2.
        exclude_placeholders: Whether declared placeholder values are excluded
            from fitting. Defaults to `True`.
        fit_sources: Nested predictor result sources admitted to fitting.
            Defaults to direct ``"base"`` and ``"override"`` values.
        prediction_sources: Nested result sources admitted when predicting the
            requested element. Defaults to base, override, substitution, and
            linear-transfer values.
        fit_max_depth: Maximum nested transfer depth admitted to fitting.
            Defaults to 0 and must be nonnegative.
        prediction_max_depth: Maximum nested transfer depth admitted for the
            requested prediction. Defaults to 1 and must be nonnegative.

    Raises:
        PolicyError: If predictors are empty, `min_points` is below 2, a source
            control is empty or unknown, or either depth limit is negative.

    Examples:
        >>> from atomref import DatasetRef, LinearTransfer
        >>> transfer = LinearTransfer(
        ...     predictors=(DatasetRef("atomic_radius", "rahm2016"),)
        ... )

    Notes:
        Fit controls and prediction controls are independent. Predictor and
        target units must be internally consistent; no unit conversion is
        performed.
    """

    predictors: tuple[
        ScalarDatasetLike | SupportsValuePolicy | ValuePolicy[str], ...
    ]
    min_points: int = 2
    exclude_placeholders: bool = True
    fit_sources: tuple[TransferValueSource, ...] = _DEFAULT_LINEAR_FIT_SOURCES
    prediction_sources: tuple[TransferValueSource, ...] = (
        _DEFAULT_LINEAR_PREDICTION_SOURCES
    )
    fit_max_depth: int = 0
    prediction_max_depth: int = 1

    def __post_init__(self) -> None:
        """Validate obvious configuration errors eagerly."""

        if not self.predictors:
            raise PolicyError("LinearTransfer requires at least one predictor")
        if self.min_points < 2:
            raise PolicyError("LinearTransfer min_points must be at least 2")

        object.__setattr__(
            self,
            "fit_sources",
            _normalize_transfer_value_sources(
                self.fit_sources,
                field_name="fit_sources",
            ),
        )
        object.__setattr__(
            self,
            "prediction_sources",
            _normalize_transfer_value_sources(
                self.prediction_sources,
                field_name="prediction_sources",
            ),
        )

        if self.fit_max_depth < 0:
            raise PolicyError("LinearTransfer fit_max_depth must be non-negative")
        if self.prediction_max_depth < 0:
            raise PolicyError(
                "LinearTransfer prediction_max_depth must be non-negative"
            )


TransferModel = SubstitutionTransfer | LinearTransfer
"""Closed union of transfer models supported by the core resolver."""


def _normalize_transfer_value_sources(
    sources: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[TransferValueSource, ...]:
    """Validate and deduplicate source-label controls for linear transfers."""

    if not sources:
        raise PolicyError(f"LinearTransfer {field_name} may not be empty")

    normalized: list[TransferValueSource] = []
    seen: set[str] = set()
    for source in sources:
        if not _is_transfer_value_source(source):
            allowed = ", ".join(sorted(_ALLOWED_TRANSFER_VALUE_SOURCES))
            raise PolicyError(
                f"LinearTransfer {field_name} contains unsupported source "
                f"{source!r}; allowed values are: {allowed}"
            )
        if source not in seen:
            normalized.append(source)
            seen.add(source)
    return tuple(normalized)
