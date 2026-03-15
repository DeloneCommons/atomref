"""Transfer-model configuration types for policy-based lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from .errors import PolicyError
from .registry import DatasetLike

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .policy import ValuePolicy


TransferValueSource = Literal[
    "override",
    "base",
    "transfer_substitution",
    "transfer_linear",
    "fallback",
]
"""Source labels that may be admitted into nested linear-transfer workflows."""

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


@runtime_checkable
class SupportsValuePolicy(Protocol):
    """Protocol for wrapper objects that can expose a generic value policy."""

    def as_value_policy(self) -> "ValuePolicy[str]":
        """Return the generic element-domain value policy."""


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
    """Use another dataset or policy directly when the base dataset is missing.

    The selected value is copied from the source rather than inferred.
    """

    source: DatasetLike | SupportsValuePolicy | ValuePolicy[str]


@dataclass(frozen=True, slots=True)
class LinearTransfer:
    """Infer missing target values from one or more predictor datasets or policies.

    In the current implementation the public API stores predictors as a tuple
    for forward compatibility, but the runtime intentionally accepts exactly one
    predictor source.

    For nested policy predictors, two safeguards apply:

    - ``fit_sources`` / ``fit_max_depth`` control which predictor values may be
      used when fitting the linear model itself;
    - ``prediction_sources`` / ``prediction_max_depth`` control which nested
      predictor values may be used for the final requested element.

    The defaults are intentionally conservative for fitting and permissive only
    enough to allow one additional completion step at prediction time.
    """

    predictors: tuple[DatasetLike | SupportsValuePolicy | ValuePolicy[str], ...]
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
        if source not in _ALLOWED_TRANSFER_VALUE_SOURCES:
            allowed = ", ".join(sorted(_ALLOWED_TRANSFER_VALUE_SOURCES))
            raise PolicyError(
                f"LinearTransfer {field_name} contains unsupported source "
                f"{source!r}; allowed values are: {allowed}"
            )
        if source not in seen:
            normalized.append(source)
            seen.add(source)
    return tuple(normalized)
