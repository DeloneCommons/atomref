"""Neutral spherical proatomic-density profiles and scalar evaluation."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
import math
from typing import Literal

from .elements import Element, get_element, iter_elements
from .errors import DatasetError
from .registry import (
    DatasetInfo,
    DatasetRef,
    ElementRadialSet,
    _normalize_element_domain_symbol,
    get_builtin_set,
    get_dataset_info,
    list_dataset_ids,
    list_dataset_infos,
)


DEFAULT_PROATOMIC_DENSITY_SET = "pbe0_sfx2c_dyallv4z_h-lr_neutral_v2"
"""Identifier of the default packaged neutral proatomic-density set."""

BOHR_TO_ANGSTROM = 0.529177210903
"""Bohr radius in angstrom, used for public coordinate conversion."""

_QUANTITY = "proatomic_density"
_NATIVE_RADIUS_UNIT = "bohr"
_NATIVE_DENSITY_UNIT = "electron/bohr^3"
_ANGSTROM_DENSITY_UNIT = "electron/angstrom^3"
_INTERPOLATION_CONTRACT = "loglog_positive_bracketed_v1"

ProatomicDensitySet = ElementRadialSet
"""Loaded immutable element-indexed proatomic-density dataset."""


def _require_storage(info: DatasetInfo) -> Mapping[str, object]:
    """Return density storage metadata or raise a clear dataset error."""

    storage = info.storage
    if not isinstance(storage, Mapping):
        raise DatasetError(f"missing storage metadata for dataset: {info.ref!r}")
    if storage.get("native_coordinate_unit") != _NATIVE_RADIUS_UNIT:
        raise DatasetError(
            f"unsupported native coordinate unit for dataset: {info.ref!r}"
        )
    if storage.get("native_density_unit") != _NATIVE_DENSITY_UNIT:
        raise DatasetError(f"unsupported native density unit for dataset: {info.ref!r}")
    if storage.get("interpolation_contract") != _INTERPOLATION_CONTRACT:
        raise DatasetError(
            f"unsupported interpolation contract for dataset: {info.ref!r}"
        )
    return storage


def _coerce_public_max_radius(storage: Mapping[str, object], ref: DatasetRef) -> float:
    """Return the finite positive public radius limit declared by metadata."""

    try:
        public_max = float(storage["public_max_radius_bohr"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetError(f"invalid public radius limit for dataset: {ref!r}") from exc
    if not math.isfinite(public_max) or public_max <= 0.0:
        raise DatasetError(f"invalid public radius limit for dataset: {ref!r}")
    return public_max


@dataclass(frozen=True, slots=True)
class ProatomicDensityProfile:
    """Immutable view of one neutral spherical proatomic-density profile.

    Radii and stored densities use the dataset's native units, bohr and
    electron/bohr^3. Calling the profile evaluates one scalar coordinate using
    positive-region log-log interpolation. The public domain ends at the
    dataset-declared maximum (20 bohr for the packaged neutral H-Lr set). At the
    origin and below the first finite grid point, the first stored value is
    returned as a finite-grid convention rather than an exact nuclear value.
    """

    dataset: ElementRadialSet = field(repr=False)
    atomic_number: int
    symbol: str = field(init=False)
    _densities: tuple[float, ...] = field(init=False, repr=False)
    _log_radii: tuple[float, ...] = field(init=False, repr=False)
    _log_densities: tuple[float, ...] = field(init=False, repr=False)
    _public_max_radius_bohr: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate and precompute the positive log-log interpolation data."""

        if self.dataset.ref != self.dataset.info.ref:
            raise DatasetError(
                "radial dataset reference does not match its metadata reference: "
                f"{self.dataset.ref!r} != {self.dataset.info.ref!r}"
            )
        element = _get_element_by_atomic_number(self.atomic_number)
        if element is None:
            raise DatasetError(
                f"invalid atomic number for proatomic-density profile: "
                f"{self.atomic_number!r}"
            )
        object.__setattr__(self, "symbol", element.symbol)

        storage = _require_storage(self.dataset.info)
        radii = self.dataset.radii
        densities = self.dataset.get(self.atomic_number)
        if densities is None:
            raise DatasetError(
                f"profile Z={self.atomic_number} is absent from {self.dataset.ref!r}"
            )
        if len(radii) != len(densities) or not radii:
            raise DatasetError(
                f"radial grid/profile length mismatch for {self.dataset.ref!r}, "
                f"Z={self.atomic_number}"
            )
        if any(not math.isfinite(radius) or radius <= 0.0 for radius in radii):
            raise DatasetError(
                f"radial grid must be finite and positive for {self.dataset.ref!r}"
            )
        if any(right <= left for left, right in zip(radii, radii[1:])):
            raise DatasetError(
                f"radial grid must strictly increase for {self.dataset.ref!r}"
            )
        if any(not math.isfinite(value) or value <= 0.0 for value in densities):
            raise DatasetError(
                f"profile values must be finite and positive for "
                f"{self.dataset.ref!r}, Z={self.atomic_number}"
            )

        public_max = _coerce_public_max_radius(storage, self.dataset.ref)
        if public_max > radii[-1]:
            raise DatasetError(
                f"radial grid does not bracket the public limit for "
                f"{self.dataset.ref!r}"
            )

        object.__setattr__(self, "_densities", densities)
        object.__setattr__(self, "_log_radii", tuple(math.log(r) for r in radii))
        object.__setattr__(
            self,
            "_log_densities",
            tuple(math.log(value) for value in densities),
        )
        object.__setattr__(self, "_public_max_radius_bohr", public_max)

    @property
    def ref(self) -> DatasetRef:
        """Canonical registry reference for the source dataset."""

        return self.dataset.ref

    @property
    def info(self) -> DatasetInfo:
        """Curated metadata and provenance for the source dataset."""

        return self.dataset.info

    @property
    def radii(self) -> tuple[float, ...]:
        """Shared immutable source grid in bohr, including the endpoint bracket."""

        return self.dataset.radii

    @property
    def densities(self) -> tuple[float, ...]:
        """Immutable stored density values in electron/bohr^3."""

        return self._densities

    @property
    def interpolation_contract(self) -> str:
        """Stable identifier for this profile's interpolation behavior."""

        return _INTERPOLATION_CONTRACT

    @property
    def public_max_radius_bohr(self) -> float:
        """Largest supported public radius coordinate, in bohr."""

        return self._public_max_radius_bohr

    def evaluate(
        self,
        radius: float,
        *,
        radius_unit: Literal["angstrom", "bohr"] = "angstrom",
        density_unit: Literal[
            "electron/bohr^3", "electron/angstrom^3"
        ] = "electron/bohr^3",
    ) -> float:
        """Evaluate the density at one radius.

        ``radius_unit`` accepts ``"angstrom"`` or ``"bohr"`` independently
        of ``density_unit``, which accepts ``"electron/bohr^3"`` or
        ``"electron/angstrom^3"``. Invalid units, negative or non-finite
        radii, and coordinates above the dataset-declared public maximum raise
        :class:`ValueError`. The packaged neutral H-Lr set uses 20 bohr.
        """

        radius_bohr = _radius_to_bohr(
            radius,
            radius_unit=radius_unit,
            public_max_bohr=self._public_max_radius_bohr,
        )
        density = self._evaluate_bohr(radius_bohr)
        return _density_from_native(density, density_unit=density_unit)

    def __call__(
        self,
        radius: float,
        *,
        radius_unit: Literal["angstrom", "bohr"] = "angstrom",
        density_unit: Literal[
            "electron/bohr^3", "electron/angstrom^3"
        ] = "electron/bohr^3",
    ) -> float:
        """Evaluate the density; equivalent to :meth:`evaluate`."""

        return self.evaluate(
            radius,
            radius_unit=radius_unit,
            density_unit=density_unit,
        )

    def _evaluate_bohr(self, radius_bohr: float) -> float:
        """Evaluate one already validated native-coordinate radius."""

        radii = self.dataset.radii
        if radius_bohr <= radii[0]:
            return self._densities[0]

        right = bisect_left(radii, radius_bohr)
        if right < len(radii) and radii[right] == radius_bohr:
            return self._densities[right]
        if right == len(radii):
            raise DatasetError(
                f"radial grid does not bracket radius {radius_bohr!r} bohr for "
                f"{self.dataset.ref!r}"
            )

        left = right - 1
        fraction = (
            (math.log(radius_bohr) - self._log_radii[left])
            / (self._log_radii[right] - self._log_radii[left])
        )
        log_density = self._log_densities[left] + fraction * (
            self._log_densities[right] - self._log_densities[left]
        )
        density = math.exp(log_density)
        if not math.isfinite(density) or density <= 0.0:
            raise DatasetError(
                f"density interpolation failed for {self.dataset.ref!r}, "
                f"Z={self.atomic_number}"
            )
        return density


def _radius_to_bohr(
    radius: float,
    *,
    radius_unit: Literal["angstrom", "bohr"],
    public_max_bohr: float,
) -> float:
    """Validate one public radius and convert it to bohr."""

    if radius_unit not in {"angstrom", "bohr"}:
        raise ValueError(f"unknown radius unit: {radius_unit!r}")
    try:
        value = float(radius)
    except (TypeError, ValueError) as exc:
        raise ValueError("radius must be a finite non-negative scalar") from exc
    if not math.isfinite(value):
        raise ValueError("radius must be finite")
    if value < 0.0:
        raise ValueError("radius must be non-negative")

    public_max = (
        public_max_bohr
        if radius_unit == "bohr"
        else public_max_bohr * BOHR_TO_ANGSTROM
    )
    if value > public_max:
        raise ValueError(
            f"radius exceeds the public limit of {public_max_bohr:g} bohr"
        )
    if radius_unit == "bohr":
        return value
    radius_bohr = value / BOHR_TO_ANGSTROM
    return min(radius_bohr, public_max_bohr)


def _density_from_native(
    value: float,
    *,
    density_unit: Literal["electron/bohr^3", "electron/angstrom^3"],
) -> float:
    """Convert electron/bohr^3 to the selected output density unit."""

    if density_unit == _NATIVE_DENSITY_UNIT:
        return value
    if density_unit == _ANGSTROM_DENSITY_UNIT:
        return value / BOHR_TO_ANGSTROM**3
    raise ValueError(f"unknown density unit: {density_unit!r}")


def list_proatomic_density_sets() -> tuple[str, ...]:
    """List packaged proatomic-density dataset identifiers."""

    return list_dataset_ids(_QUANTITY)


def list_proatomic_density_set_infos() -> tuple[DatasetInfo, ...]:
    """Return metadata for all packaged proatomic-density datasets."""

    return list_dataset_infos(_QUANTITY)


def get_proatomic_density_set_info(
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> DatasetInfo:
    """Return metadata for one packaged proatomic-density dataset or alias."""

    return get_dataset_info(DatasetRef(_QUANTITY, set_id))


def get_proatomic_density_set(
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> ProatomicDensitySet:
    """Return one cached immutable packaged proatomic-density dataset."""

    loaded = get_builtin_set(DatasetRef(_QUANTITY, set_id))
    if not isinstance(loaded, ElementRadialSet):
        raise DatasetError(
            f"dataset {loaded.ref!r} has a scalar payload; radial dataset required"
        )
    return loaded


@lru_cache(maxsize=None)
def _get_element_by_atomic_number_cached(
    atomic_number: int,
) -> Element | None:
    """Return the periodic-table element for a validated integer Z."""

    return next(
        (candidate for candidate in iter_elements() if candidate.z == atomic_number),
        None,
    )


def _get_element_by_atomic_number(atomic_number: object) -> Element | None:
    """Resolve an integer atomic number while rejecting booleans safely."""

    if not isinstance(atomic_number, int) or isinstance(atomic_number, bool):
        return None
    return _get_element_by_atomic_number_cached(atomic_number)


def _resolve_density_element(element: str | int | None) -> Element | None:
    """Resolve a symbol, isotope alias, or integer atomic number."""

    if isinstance(element, int):
        return _get_element_by_atomic_number(element)
    if isinstance(element, str) or element is None:
        symbol = _normalize_element_domain_symbol(element)
        return get_element(symbol)
    return None


@lru_cache(maxsize=None)
def _get_profile_cached(ref: DatasetRef, atomic_number: int) -> ProatomicDensityProfile:
    """Create one shared immutable profile view from a canonical dataset ref."""

    dataset = get_builtin_set(ref)
    if not isinstance(dataset, ElementRadialSet):
        raise DatasetError(
            f"dataset {dataset.ref!r} has a scalar payload; radial dataset required"
        )
    element = _get_element_by_atomic_number(atomic_number)
    if element is None:
        raise DatasetError(f"unknown atomic number in radial dataset: {atomic_number}")
    return ProatomicDensityProfile(
        dataset=dataset,
        atomic_number=atomic_number,
    )


def get_proatomic_density_profile(
    element: str | int | None,
    *,
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> ProatomicDensityProfile | None:
    """Return a cached neutral profile, or ``None`` for unsupported elements.

    Element symbols are canonicalized using the package's normal element rules,
    and integer atomic numbers are accepted. Deuterium (``D``) and tritium
    (``T``) return hydrogen's electronic profile. Invalid values, including
    booleans, return ``None``. No substitution, correlation, or ionic selection
    is performed.
    """

    resolved = _resolve_density_element(element)
    if resolved is None:
        return None
    info = get_proatomic_density_set_info(set_id)
    dataset = get_proatomic_density_set(info.ref.set_id)
    if dataset.get(resolved.z) is None:
        return None
    return _get_profile_cached(dataset.ref, resolved.z)


def get_proatomic_density(
    element: str | int | None,
    radius: float,
    *,
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
    radius_unit: Literal["angstrom", "bohr"] = "angstrom",
    density_unit: Literal[
        "electron/bohr^3", "electron/angstrom^3"
    ] = "electron/bohr^3",
) -> float | None:
    """Evaluate one neutral proatomic density, or return ``None`` if absent.

    The default coordinate unit is angstrom and the default output unit is
    electron/bohr^3. The supported interval ends at the dataset-declared public
    maximum (20 bohr for the packaged neutral H-Lr set). Evaluation is scalar
    and dependency-free.
    """

    profile = get_proatomic_density_profile(element, set_id=set_id)
    if profile is None:
        return None
    return profile(
        radius,
        radius_unit=radius_unit,
        density_unit=density_unit,
    )
