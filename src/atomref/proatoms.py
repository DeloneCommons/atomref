"""Neutral spherical proatomic-density profiles and scalar evaluation."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
import math
from typing import Literal, SupportsFloat, SupportsIndex, cast

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

PROATOMIC_TAIL_CUTOFF = 1.0e-4
"""Fixed per-atom tail cutoff in electron/bohr^3 for pairwise estimates."""

IAS_MINIMUM_RESOLUTION_BOHR = 0.01
"""Declared spatial resolution of the practical minimum search, in bohr."""

_PAIRWISE_CONTRACT = "neutral_proatom_pairwise_cutoff_1e-4_resolution_0.01_v1"
_MINIMUM_INITIAL_SPACING_BOHR = 0.02
_MINIMUM_CONFIRM_SPACING_BOHR = 0.01
_MINIMUM_FALLBACK_SPACING_BOHR = 0.005
_COMPETITIVE_RELATIVE_DEPTH = 1.0e-4
_EQUALITY_BRACKET_TOLERANCE_BOHR = 1.0e-10
_CUTOFF_REPRODUCTION_REL_TOL = 5.0e-14
_FLOAT_COMPARISON_REL_TOL = 64.0 * 2.220446049250313e-16

_FloatLike = str | bytes | bytearray | memoryview | SupportsFloat | SupportsIndex

_IASRequestedMode = Literal["boundary", "minimum"]
_IASMethod = Literal[
    "homonuclear_midpoint",
    "equal_proatom_density",
    "cutoff_gap_midpoint",
    "promolecular_density_minimum",
    "none",
]
_IASStatus = Literal[
    "ok",
    "low_density_gap",
    "one_atom_dominates",
    "no_resolved_interior_minimum",
    "boundary_dominated",
    "ambiguous_competing_minima",
    "search_unstable",
]
_CutoffRegime = Literal["overlap", "contact", "gap"]
_NativeDominantSide = Literal["a", "b"]
_DominantAtomRole = Literal["atom_a", "atom_b"]


@dataclass(frozen=True, slots=True)
class IASPositionResult:
    """Immutable result of one pairwise neutral-proatom estimate.

    Attributes:
        atom_a: Canonical symbol of the first requested atom.
        atom_b: Canonical symbol of the second requested atom.
        distance: Requested positive pair distance, no greater than 20 bohr
            after conversion.
        distance_unit: Unit used by `distance`, coordinates, cutoff radii,
            contour separation, and search resolution: ``"angstrom"`` or
            ``"bohr"``.
        density_unit: Unit used by all density-valued fields:
            ``"electron/bohr^3"`` or ``"electron/angstrom^3"``.
        requested_mode: Requested ``"boundary"`` or ``"minimum"`` policy.
        method: Actual construction: symmetry midpoint, equal-proatom divider,
            cutoff-gap midpoint, promolecular minimum, or ``"none"``.
        status: Scientific and numerical outcome. Callers should inspect this
            together with `method` and `position_from_a`.
        position_from_a: Primary coordinate measured from atom A toward atom B
            in `distance_unit`, or `None` for a typed non-result.
        position_from_b: Complementary coordinate measured from atom B in
            `distance_unit`, or `None`.
        fraction_from_a: `position_from_a / distance`, normally in [0, 1], or
            `None` when no coordinate is returned.
        rho_a: Atom A component density at the primary coordinate, or `None`.
        rho_b: Atom B component density at the primary coordinate, or `None`.
        rho_sum: Sum of the two components at the primary coordinate, or `None`.
        cutoff_density: Fixed per-atom tail cutoff converted to `density_unit`.
        cutoff_radius_a: Atom A radius at the fixed cutoff in `distance_unit`.
        cutoff_radius_b: Atom B radius at the fixed cutoff in `distance_unit`.
        contour_separation: Signed `distance - cutoff_radius_a -
            cutoff_radius_b` in `distance_unit`; positive values indicate a gap.
        cutoff_regime: ``"overlap"``, ``"contact"``, or ``"gap"`` according to
            the signed contour separation.
        dominant_atom: Canonical symbol of the atom that dominates an unlike
            interval, or `None`.
        dominant_atom_role: Whether `dominant_atom` is ``"atom_a"`` or
            ``"atom_b"``, or `None`.
        alternative_position_from_a: Competitive alternative-minimum coordinate
            from atom A in `distance_unit`, or `None`.
        alternative_position_from_b: Complementary alternative coordinate from
            atom B in `distance_unit`, or `None`.
        alternative_rho_sum: Summed density at the alternative, or `None`.
        relative_depth_gap: Nonnegative dimensionless relative density gap
            between alternative and selected minima, or `None`.
        ambiguous: Whether a competitive resolved alternative meets the fixed
            relative-depth criterion.
        search_resolution: Finest minimum-search spacing in `distance_unit`, or
            `None` when minimum search is not applicable.
        search_converged: Whether required minimum-search passes agreed, or
            `None` outside applicable minimum searches.
        search_passes: Number of practical minimum-search passes, or `None` when
            not applicable.
        dataset_id: Canonical packaged proatomic-density dataset ID.
        interpolation_contract: Stable radial interpolation identifier.
        pairwise_contract: Stable cutoff and numerical-search identifier.
        coordinate_orientation: Explicit orientation label. The default and
            current value is ``"from_atom_a_toward_atom_b"``.

    Notes:
        A valid but scientifically non-applicable request uses ``method="none"``
        and leaves coordinate fields as `None`. Reversing the atoms maps each
        coordinate `x` to `R - x`, swaps A/B fields, and relabels dominance.

        ``"boundary_dominated"`` takes status precedence over
        ``"search_unstable"``, which takes precedence over
        ``"ambiguous_competing_minima"``. Separate boolean diagnostics preserve
        the underlying conditions. Neither mode is an exact molecular QTAIM
        surface or critical-point calculation.

        At an odd subnormal homonuclear distance, the mathematical midpoint may
        not be representable in binary64. The exposed coordinate then uses the
        ordinary `R / 2` result and preserves the complementary distance.
    """

    atom_a: str
    atom_b: str
    distance: float
    distance_unit: str
    density_unit: str
    requested_mode: _IASRequestedMode
    method: _IASMethod
    status: _IASStatus
    position_from_a: float | None
    position_from_b: float | None
    fraction_from_a: float | None
    rho_a: float | None
    rho_b: float | None
    rho_sum: float | None
    cutoff_density: float
    cutoff_radius_a: float
    cutoff_radius_b: float
    contour_separation: float
    cutoff_regime: _CutoffRegime
    dominant_atom: str | None
    dominant_atom_role: _DominantAtomRole | None
    alternative_position_from_a: float | None
    alternative_position_from_b: float | None
    alternative_rho_sum: float | None
    relative_depth_gap: float | None
    ambiguous: bool
    search_resolution: float | None
    search_converged: bool | None
    search_passes: int | None
    dataset_id: str
    interpolation_contract: str
    pairwise_contract: str
    coordinate_orientation: str = "from_atom_a_toward_atom_b"


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
        public_max = float(
            cast(_FloatLike, storage["public_max_radius_bohr"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetError(f"invalid public radius limit for dataset: {ref!r}") from exc
    if not math.isfinite(public_max) or public_max <= 0.0:
        raise DatasetError(f"invalid public radius limit for dataset: {ref!r}")
    return public_max


def _dataset_public_max_radius_bohr(dataset: ElementRadialSet) -> float:
    """Validate and return one dataset's declared public radius limit."""

    storage = _require_storage(dataset.info)
    public_max = _coerce_public_max_radius(storage, dataset.ref)
    if not dataset.radii or public_max > dataset.radii[-1]:
        raise DatasetError(
            f"radial grid does not bracket the public limit for {dataset.ref!r}"
        )
    return public_max


@dataclass(frozen=True, slots=True)
class ProatomicDensityProfile:
    """Immutable view of one neutral spherical proatomic-density profile.

    Attributes:
        dataset: Immutable radial dataset owning the shared grid and profiles.
        atomic_number: Selected integer atomic number. The packaged neutral set
            supports 1 (H) through 103 (Lr).
        symbol: Canonical element symbol initialized from `atomic_number`.
        ref: Canonical registry reference for `dataset`.
        info: Curated metadata and provenance for `dataset`.
        radii: Shared immutable source grid in bohr, including the endpoint
            bracket above the public domain.
        densities: Immutable sampled values in electron/bohr^3.
        interpolation_contract: Stable identifier for evaluation behavior.
        public_max_radius_bohr: Inclusive public radius limit in bohr; 20 for
            the packaged neutral H-Lr set.

    Raises:
        DatasetError: If the atomic number is invalid, the profile is absent,
            or radial data or metadata violate the interpolation contract.

    Examples:
        >>> profile = get_proatomic_density_profile("O")
        >>> profile is not None
        True
        >>> profile(1.5, radius_unit="bohr") > 0.0
        True

    Notes:
        Evaluation is scalar and uses positive-region log-log interpolation.
        At the origin and below the first finite grid point, the first stored
        value is returned as a finite-grid convention, not an exact nuclear
        density.
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

        public_max = _dataset_public_max_radius_bohr(self.dataset)

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
        """Return the canonical registry reference.

        Returns:
            Source [DatasetRef][atomref.registry.DatasetRef].
        """

        return self.dataset.ref

    @property
    def info(self) -> DatasetInfo:
        """Return curated source metadata and provenance.

        Returns:
            Source [DatasetInfo][atomref.registry.DatasetInfo].
        """

        return self.dataset.info

    @property
    def radii(self) -> tuple[float, ...]:
        """Return the shared immutable source grid.

        Returns:
            Positive radii in bohr, including the endpoint bracket above the
            20-bohr public domain.
        """

        return self.dataset.radii

    @property
    def densities(self) -> tuple[float, ...]:
        """Return immutable stored density values.

        Returns:
            Positive sampled values in electron/bohr^3, aligned with `radii`.
        """

        return self._densities

    @property
    def interpolation_contract(self) -> str:
        """Return the interpolation-contract identifier.

        Returns:
            ``"loglog_positive_bracketed_v1"``.
        """

        return _INTERPOLATION_CONTRACT

    @property
    def public_max_radius_bohr(self) -> float:
        """Return the inclusive public radius limit.

        Returns:
            Largest supported coordinate in bohr; 20 for the packaged neutral
            dataset.
        """

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

        Args:
            radius: Finite scalar coordinate in `radius_unit`. It must map to
                the inclusive interval 0 through 20 bohr for the packaged set.
            radius_unit: ``"angstrom"`` (default) or ``"bohr"``.
            density_unit: ``"electron/bohr^3"`` (default) or
                ``"electron/angstrom^3"``. This choice is independent of the
                coordinate unit.

        Returns:
            Finite positive interpolated density in `density_unit`.

        Raises:
            ValueError: If a unit is unknown or `radius` is negative,
                non-finite, nonscalar, or above the public limit.
            DatasetError: If the stored radial grid cannot bracket evaluation.

        Examples:
            >>> profile = get_proatomic_density_profile("O")
            >>> profile is not None
            True
            >>> profile.evaluate(0.75) > 0.0
            True
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
        """Evaluate the density; equivalent to
        [evaluate][atomref.proatoms.ProatomicDensityProfile.evaluate].

        Args:
            radius: Finite coordinate from 0 through the public 20-bohr limit.
            radius_unit: ``"angstrom"`` (default) or ``"bohr"``.
            density_unit: ``"electron/bohr^3"`` (default) or
                ``"electron/angstrom^3"``.

        Returns:
            Finite positive interpolated density in `density_unit`.

        Raises:
            ValueError: If a unit or radius is outside the public contract.
            DatasetError: If the stored radial data cannot support evaluation.
        """

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
    if isinstance(radius, bool):
        raise ValueError("radius must be a finite non-negative scalar")
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
    density_unit: str,
) -> float:
    """Convert electron/bohr^3 to the selected output density unit."""

    if density_unit == _NATIVE_DENSITY_UNIT:
        return value
    if density_unit == _ANGSTROM_DENSITY_UNIT:
        return value / BOHR_TO_ANGSTROM**3
    raise ValueError(f"unknown density unit: {density_unit!r}")


def list_proatomic_density_sets() -> tuple[str, ...]:
    """List packaged proatomic-density dataset identifiers.

    Returns:
        Canonical set IDs in curated registry order.

    Raises:
        DatasetError: If registry metadata is unavailable or malformed.
    """

    return list_dataset_ids(_QUANTITY)


def list_proatomic_density_set_infos() -> tuple[DatasetInfo, ...]:
    """Return metadata for all packaged proatomic-density datasets.

    Returns:
        Immutable [DatasetInfo][atomref.registry.DatasetInfo] objects in curated
        registry order.

    Raises:
        DatasetError: If registry metadata is unavailable or malformed.
    """

    return list_dataset_infos(_QUANTITY)


def get_proatomic_density_set_info(
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> DatasetInfo:
    """Return metadata for one packaged proatomic-density dataset.

    Args:
        set_id: Canonical set ID or accepted alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        Curated method, units, provenance, coverage, and storage metadata.

    Raises:
        DatasetError: If the set is unknown or metadata is malformed.
    """

    return get_dataset_info(DatasetRef(_QUANTITY, set_id))


def get_proatomic_density_set(
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> ProatomicDensitySet:
    """Return one cached immutable packaged proatomic-density dataset.

    Args:
        set_id: Canonical set ID or accepted alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        Element-indexed neutral profiles sharing one radial grid.

    Raises:
        DatasetError: If the set is unknown, malformed, or has a scalar rather
            than radial payload.
    """

    loaded = get_builtin_set(DatasetRef(_QUANTITY, set_id))
    if not isinstance(loaded, ElementRadialSet):
        raise DatasetError(
            f"dataset {loaded.ref!r} has a scalar payload; radial dataset required"
        )
    return loaded


def _resolve_proatomic_density_set(
    set_id: str,
) -> tuple[ProatomicDensitySet, float]:
    """Resolve and load one selected proatomic-density dataset."""

    info = get_proatomic_density_set_info(set_id)
    dataset = get_proatomic_density_set(info.ref.set_id)
    return dataset, _dataset_public_max_radius_bohr(dataset)


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

    Args:
        element: Element symbol, integer atomic number, or `None`. D/T map to
            hydrogen's electronic profile; booleans are rejected.
        set_id: Canonical set ID or accepted alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        A cached
        [ProatomicDensityProfile][atomref.proatoms.ProatomicDensityProfile], or
        `None` for an invalid, unsupported, or uncovered element. The packaged
        set covers H through Lr.

    Raises:
        DatasetError: If the selected dataset is unknown, malformed, or
            non-radial.

    Examples:
        >>> get_proatomic_density_profile(8).symbol
        'O'
        >>> get_proatomic_density_profile("Og") is None
        True

    Notes:
        No neighboring-element substitution, correlation, ionic selection, or
        scalar [ValuePolicy][atomref.ValuePolicy] is applied.
    """

    dataset, _ = _resolve_proatomic_density_set(set_id)
    resolved = _resolve_density_element(element)
    if resolved is None:
        return None
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

    Args:
        element: Element symbol, integer atomic number, or `None`. D/T map to H.
        radius: Finite nonnegative scalar coordinate in `radius_unit`, no greater
            than 20 bohr after conversion.
        set_id: Canonical set ID or alias. Defaults to the packaged neutral set.
        radius_unit: ``"angstrom"`` (default) or ``"bohr"``.
        density_unit: ``"electron/bohr^3"`` (default) or
            ``"electron/angstrom^3"``.

    Returns:
        Finite positive scalar density in `density_unit`, or `None` for an
        invalid, unsupported, or uncovered element.

    Raises:
        ValueError: If a unit is unknown or the radius is negative, non-finite,
            nonscalar, or above 20 bohr after conversion.
        DatasetError: If the selected dataset is unknown, malformed, or
            non-radial.

    Examples:
        >>> rho = get_proatomic_density("O", 0.75)
        >>> rho is not None and rho > 0.0
        True

    Notes:
        Radius and density units are independent. Evaluation is scalar and
        dependency-free, with no extrapolation beyond 20 bohr.
    """

    dataset, public_max_radius_bohr = _resolve_proatomic_density_set(set_id)
    radius_bohr = _radius_to_bohr(
        radius,
        radius_unit=radius_unit,
        public_max_bohr=public_max_radius_bohr,
    )
    _density_from_native(1.0, density_unit=density_unit)

    resolved = _resolve_density_element(element)
    if resolved is None or dataset.get(resolved.z) is None:
        return None
    profile = _get_profile_cached(dataset.ref, resolved.z)
    return _density_from_native(
        profile._evaluate_bohr(radius_bohr),
        density_unit=density_unit,
    )


@dataclass(frozen=True, slots=True)
class _PreparedPairwiseProfile:
    """Cached native numerical representation used by pairwise estimates."""

    profile: ProatomicDensityProfile
    loglog_slopes: tuple[float, ...]
    cutoff_radius_bohr: float


@dataclass(frozen=True, slots=True)
class _MinimumCandidate:
    """One locally refined minimum candidate in native units."""

    position_bohr: float
    density: float


@dataclass(frozen=True, slots=True)
class _MinimumPass:
    """Raw refined candidates from one deterministic grid pass."""

    max_spacing_bohr: float
    candidates: tuple[_MinimumCandidate, ...]

    @property
    def selected(self) -> _MinimumCandidate | None:
        """Return the lowest refined candidate, if any."""

        return min(
            self.candidates,
            key=lambda candidate: (
                candidate.density,
                candidate.position_bohr,
            ),
            default=None,
        )


@dataclass(frozen=True, slots=True)
class _NativeIASResult:
    """Pairwise result before requested orientation and unit conversion."""

    requested_mode: _IASRequestedMode
    method: _IASMethod
    status: _IASStatus
    position_bohr: float | None
    rho_a: float | None
    rho_b: float | None
    rho_sum: float | None
    cutoff_radius_a_bohr: float
    cutoff_radius_b_bohr: float
    contour_separation_bohr: float
    cutoff_regime: _CutoffRegime
    dominant_side: _NativeDominantSide | None = None
    alternative_position_bohr: float | None = None
    alternative_rho_sum: float | None = None
    relative_depth_gap: float | None = None
    ambiguous: bool = False
    search_resolution_bohr: float | None = None
    search_converged: bool | None = None
    search_passes: int | None = None


def _prepare_pairwise_profile(
    profile: ProatomicDensityProfile,
) -> _PreparedPairwiseProfile:
    """Validate and prepare one profile for the fixed pairwise cutoff.

    The inverse cutoff coordinate is obtained analytically from the one
    bracketing log-log segment. ``_CUTOFF_REPRODUCTION_REL_TOL`` is a
    conservative binary64 envelope; the packaged H-Lr maximum observed error
    is substantially smaller.
    """

    densities = profile.densities
    if any(right >= left for left, right in zip(densities, densities[1:])):
        raise DatasetError(
            "pairwise proatomic profiles must be strictly decreasing for "
            f"{profile.ref!r}, Z={profile.atomic_number}"
        )
    if densities[0] <= PROATOMIC_TAIL_CUTOFF:
        raise DatasetError(
            "first proatomic density must exceed the pairwise tail cutoff for "
            f"{profile.ref!r}, Z={profile.atomic_number}"
        )

    try:
        right = next(
            index
            for index, density in enumerate(densities)
            if density <= PROATOMIC_TAIL_CUTOFF
        )
    except StopIteration as exc:
        raise DatasetError(
            "proatomic density does not fall below the pairwise tail cutoff for "
            f"{profile.ref!r}, Z={profile.atomic_number}"
        ) from exc
    if not any(
        radius < profile.public_max_radius_bohr
        and density < PROATOMIC_TAIL_CUTOFF
        for radius, density in zip(profile.radii, densities)
    ):
        raise DatasetError(
            "proatomic density must fall below the pairwise tail cutoff before "
            f"the public limit for {profile.ref!r}, Z={profile.atomic_number}"
        )

    slopes = tuple(
        (right_log_density - left_log_density)
        / (right_log_radius - left_log_radius)
        for left_log_radius, right_log_radius, left_log_density, right_log_density
        in zip(
            profile._log_radii,
            profile._log_radii[1:],
            profile._log_densities,
            profile._log_densities[1:],
        )
    )

    if densities[right] == PROATOMIC_TAIL_CUTOFF:
        cutoff_radius = profile.radii[right]
    else:
        left = right - 1
        cutoff_log_radius = profile._log_radii[left] + (
            math.log(PROATOMIC_TAIL_CUTOFF) - profile._log_densities[left]
        ) / slopes[left]
        cutoff_radius = math.exp(cutoff_log_radius)

    if not math.isfinite(cutoff_radius) or not (
        0.0 < cutoff_radius < profile.public_max_radius_bohr
    ):
        raise DatasetError(
            "pairwise tail cutoff is not reached before the public radius limit "
            f"for {profile.ref!r}, Z={profile.atomic_number}"
        )

    reproduced_log_density = profile._log_densities[right - 1] + slopes[
        right - 1
    ] * (math.log(cutoff_radius) - profile._log_radii[right - 1])
    reproduced = math.exp(reproduced_log_density)
    if not math.isclose(
        reproduced,
        PROATOMIC_TAIL_CUTOFF,
        rel_tol=_CUTOFF_REPRODUCTION_REL_TOL,
        abs_tol=0.0,
    ):
        raise DatasetError(
            "analytical pairwise tail-cutoff inversion failed for "
            f"{profile.ref!r}, Z={profile.atomic_number}"
        )

    return _PreparedPairwiseProfile(
        profile=profile,
        loglog_slopes=slopes,
        cutoff_radius_bohr=cutoff_radius,
    )


@lru_cache(maxsize=None)
def _get_prepared_pairwise_profile_cached(
    ref: DatasetRef,
    atomic_number: int,
) -> _PreparedPairwiseProfile:
    """Return one cached pairwise representation by canonical dataset key."""

    return _prepare_pairwise_profile(_get_profile_cached(ref, atomic_number))


def _prepared_pairwise_profile(
    profile: ProatomicDensityProfile,
) -> _PreparedPairwiseProfile:
    """Return the cached pairwise representation for a packaged profile."""

    return _get_prepared_pairwise_profile_cached(
        profile.ref,
        profile.atomic_number,
    )


def _continuous_log_density_bohr(
    prepared: _PreparedPairwiseProfile,
    radius_bohr: float,
) -> float:
    """Evaluate the continuous accepted log-log representation in log space."""

    profile = prepared.profile
    radii = profile.radii
    if radius_bohr <= radii[0]:
        return profile._log_densities[0]

    left = min(bisect_right(radii, radius_bohr) - 1, len(radii) - 2)
    return profile._log_densities[left] + prepared.loglog_slopes[left] * (
        math.log(radius_bohr) - profile._log_radii[left]
    )


def _evaluate_prepared_density_bohr(
    prepared: _PreparedPairwiseProfile,
    radius_bohr: float,
) -> float:
    """Evaluate the exact Stage 3 convention using cached segment slopes."""

    profile = prepared.profile
    radii = profile.radii
    if radius_bohr <= radii[0]:
        return profile.densities[0]
    right = bisect_left(radii, radius_bohr)
    if right < len(radii) and radii[right] == radius_bohr:
        return profile.densities[right]
    left = right - 1
    return math.exp(
        profile._log_densities[left]
        + prepared.loglog_slopes[left]
        * (math.log(radius_bohr) - profile._log_radii[left])
    )


def _component_values(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
    position_bohr: float,
) -> tuple[float, float, float]:
    """Evaluate pair components and their sum in native units."""

    rho_a = _evaluate_prepared_density_bohr(profile_a, position_bohr)
    rho_b = _evaluate_prepared_density_bohr(
        profile_b,
        distance_bohr - position_bohr,
    )
    return rho_a, rho_b, rho_a + rho_b


def _objective(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
    position_bohr: float,
) -> float:
    """Return the native promolecular line-density sum."""

    return (
        _evaluate_prepared_density_bohr(profile_a, position_bohr)
        + _evaluate_prepared_density_bohr(
            profile_b,
            distance_bohr - position_bohr,
        )
    )


def _cutoff_regime(
    distance_bohr: float,
    cutoff_radius_a_bohr: float,
    cutoff_radius_b_bohr: float,
) -> tuple[float, _CutoffRegime]:
    """Return signed contour separation and its exact-sign regime."""

    radius_sum = cutoff_radius_a_bohr + cutoff_radius_b_bohr
    separation = distance_bohr - radius_sum
    if separation == 0.0:
        return separation, "contact"
    if separation > 0.0:
        return separation, "gap"
    return separation, "overlap"


def _equal_contribution_position(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
) -> tuple[float | None, _NativeDominantSide | None]:
    """Solve the continuous log-density equality by bracketed bisection."""

    def difference(position: float) -> float:
        return _continuous_log_density_bohr(
            profile_a,
            position,
        ) - _continuous_log_density_bohr(
            profile_b,
            distance_bohr - position,
        )

    left = 0.0
    right = distance_bohr
    left_value = difference(left)
    right_value = difference(right)

    if left_value <= 0.0:
        return None, "b"
    if right_value >= 0.0:
        return None, "a"

    while right - left > _EQUALITY_BRACKET_TOLERANCE_BOHR:
        midpoint = (left + right) / 2.0
        if midpoint == left or midpoint == right:
            break
        value = difference(midpoint)
        if value == 0.0:
            return midpoint, None
        if value > 0.0:
            left = midpoint
        else:
            right = midpoint
        if math.nextafter(left, right) == right:
            break

    return (left + right) / 2.0, None


def _native_boundary_estimate(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
) -> _NativeIASResult:
    """Compute boundary mode in canonical orientation and native units."""

    cutoff_a = profile_a.cutoff_radius_bohr
    cutoff_b = profile_b.cutoff_radius_bohr
    separation, regime = _cutoff_regime(distance_bohr, cutoff_a, cutoff_b)

    if profile_a.profile.atomic_number == profile_b.profile.atomic_number:
        position = distance_bohr / 2.0
        rho_a, rho_b, rho_sum = _component_values(
            profile_a,
            profile_b,
            distance_bohr,
            position,
        )
        return _NativeIASResult(
            requested_mode="boundary",
            method="homonuclear_midpoint",
            status="low_density_gap" if regime == "gap" else "ok",
            position_bohr=position,
            rho_a=rho_a,
            rho_b=rho_b,
            rho_sum=rho_sum,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
        )

    if regime == "gap":
        position = (distance_bohr + cutoff_a - cutoff_b) / 2.0
        rho_a, rho_b, rho_sum = _component_values(
            profile_a,
            profile_b,
            distance_bohr,
            position,
        )
        return _NativeIASResult(
            requested_mode="boundary",
            method="cutoff_gap_midpoint",
            status="low_density_gap",
            position_bohr=position,
            rho_a=rho_a,
            rho_b=rho_b,
            rho_sum=rho_sum,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
        )

    equal_position, dominant_side = _equal_contribution_position(
        profile_a,
        profile_b,
        distance_bohr,
    )
    if equal_position is None:
        return _NativeIASResult(
            requested_mode="boundary",
            method="none",
            status="one_atom_dominates",
            position_bohr=None,
            rho_a=None,
            rho_b=None,
            rho_sum=None,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
            dominant_side=dominant_side,
        )

    rho_a, rho_b, rho_sum = _component_values(
        profile_a,
        profile_b,
        distance_bohr,
        equal_position,
    )
    return _NativeIASResult(
        requested_mode="boundary",
        method="equal_proatom_density",
        status="ok",
        position_bohr=equal_position,
        rho_a=rho_a,
        rho_b=rho_b,
        rho_sum=rho_sum,
        cutoff_radius_a_bohr=cutoff_a,
        cutoff_radius_b_bohr=cutoff_b,
        contour_separation_bohr=separation,
        cutoff_regime=regime,
    )


def _bounded_minimum(
    function: Callable[[float], float],
    left: float,
    center: float,
    right: float,
    center_value: float,
) -> _MinimumCandidate:
    """Refine one sample-resolved valley with local golden-section search."""

    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right - ratio * (right - left)
    x2 = left + ratio * (right - left)
    f1 = function(x1)
    f2 = function(x2)

    for _ in range(36):
        if math.nextafter(left, right) == right:
            break
        if f1 <= f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left)
            f1 = function(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left)
            f2 = function(x2)

    position, density = min(
        ((center, center_value), (x1, f1), (x2, f2)),
        key=lambda item: (item[1], item[0]),
    )
    return _MinimumCandidate(position, density)


def _coalesce_minimum_candidates(
    candidates: tuple[_MinimumCandidate, ...],
) -> tuple[_MinimumCandidate, ...]:
    """Coalesce position-connected candidates at the public resolution."""

    ordered = sorted(candidates, key=lambda candidate: candidate.position_bohr)
    groups: list[list[_MinimumCandidate]] = []
    for candidate in ordered:
        if (
            not groups
            or candidate.position_bohr - groups[-1][-1].position_bohr
            >= IAS_MINIMUM_RESOLUTION_BOHR
        ):
            groups.append([candidate])
        else:
            groups[-1].append(candidate)
    representatives = [
        min(
            group,
            key=lambda candidate: (
                candidate.density,
                candidate.position_bohr,
            ),
        )
        for group in groups
    ]
    return tuple(
        sorted(
            representatives,
            key=lambda candidate: (candidate.density, candidate.position_bohr),
        )
    )


def _minimum_grid_pass(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
    overlap_left: float,
    overlap_right: float,
    max_spacing_bohr: float,
    equal_position_bohr: float | None,
) -> _MinimumPass:
    """Run one deterministic practical-resolution valley search pass."""

    width = overlap_right - overlap_left
    segments = max(2, math.ceil(width / max_spacing_bohr))
    coordinates = [
        overlap_left + width * index / segments
        for index in range(segments + 1)
    ]
    coordinates[0] = overlap_left
    coordinates[-1] = overlap_right
    if segments % 2:
        midpoint = (overlap_left + overlap_right) / 2.0
        if midpoint not in coordinates:
            coordinates.append(midpoint)
    if (
        equal_position_bohr is not None
        and overlap_left < equal_position_bohr < overlap_right
        and equal_position_bohr not in coordinates
    ):
        coordinates.append(equal_position_bohr)
    coordinates = sorted(set(coordinates))

    def objective(position: float) -> float:
        return _objective(
            profile_a,
            profile_b,
            distance_bohr,
            position,
        )
    values = [objective(position) for position in coordinates]
    candidates: list[_MinimumCandidate] = []
    for index in range(1, len(coordinates) - 1):
        if (
            values[index] <= values[index - 1]
            and values[index] <= values[index + 1]
        ):
            candidate = _bounded_minimum(
                objective,
                coordinates[index - 1],
                coordinates[index],
                coordinates[index + 1],
                values[index],
            )
            if overlap_left < candidate.position_bohr < overlap_right:
                candidates.append(candidate)

    return _MinimumPass(
        max_spacing_bohr=max_spacing_bohr,
        candidates=tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    candidate.density,
                    candidate.position_bohr,
                ),
            )
        ),
    )


def _selections_compatible(
    first: _MinimumCandidate | None,
    second: _MinimumCandidate | None,
) -> bool:
    """Return whether two pass selections agree at the public resolution."""

    if first is None or second is None:
        return first is second
    position_agrees = (
        abs(first.position_bohr - second.position_bohr)
        <= IAS_MINIMUM_RESOLUTION_BOHR
    )
    density_agrees = abs(first.density - second.density) <= (
        _COMPETITIVE_RELATIVE_DEPTH * min(first.density, second.density)
    )
    return position_agrees and density_agrees


def _combine_confirmed_minimum_candidates(
    *passes: _MinimumPass,
    candidate_filter: Callable[[_MinimumCandidate], bool] | None = None,
) -> tuple[_MinimumCandidate, ...]:
    """Combine candidates from every executed pass before coalescing."""

    return _coalesce_minimum_candidates(
        tuple(
            candidate
            for minimum_pass in passes
            for candidate in minimum_pass.candidates
            if candidate_filter is None or candidate_filter(candidate)
        )
    )


def _minimum_candidate_is_publicly_strict(
    candidate: _MinimumCandidate,
    distance_bohr: float,
    cutoff_a_bohr: float,
    cutoff_b_bohr: float,
    extra_presentations: tuple[tuple[float, float], ...] = (),
) -> bool:
    """Return whether a minimum stays interior in every public presentation.

    A binary64 subtraction used for pair reversal, or the multiplication used
    for angstrom output, can round a native strict-interior coordinate onto an
    exposed cutoff endpoint.  Reject such a candidate in native space for both
    supported units and orientations so this representability decision cannot
    depend on how the caller labels the pair or names the distance unit.
    """

    presentations = (
        (distance_bohr, 1.0),
        (distance_bohr * BOHR_TO_ANGSTROM, BOHR_TO_ANGSTROM),
        *extra_presentations,
    )
    for distance, scale in presentations:
        cutoff_a = cutoff_a_bohr * scale
        cutoff_b = cutoff_b_bohr * scale
        position_a = candidate.position_bohr * scale
        position_b = distance - position_a

        overlap_left_a = max(0.0, distance - cutoff_b)
        overlap_right_a = min(distance, cutoff_a)
        overlap_left_b = max(0.0, distance - cutoff_a)
        overlap_right_b = min(distance, cutoff_b)
        if not (
            overlap_left_a < position_a < overlap_right_a
            and overlap_left_b < position_b < overlap_right_b
        ):
            return False
    return True


def _less_beyond_roundoff(first: float, second: float) -> bool:
    """Return whether ``first`` is meaningfully below ``second`` in binary64."""

    envelope = _FLOAT_COMPARISON_REL_TOL * max(abs(first), abs(second))
    return first < second - envelope


def _native_minimum_estimate(
    profile_a: _PreparedPairwiseProfile,
    profile_b: _PreparedPairwiseProfile,
    distance_bohr: float,
    *,
    public_presentations: tuple[tuple[float, float], ...] = (),
) -> _NativeIASResult:
    """Compute practical minimum mode in canonical orientation and native units."""

    cutoff_a = profile_a.cutoff_radius_bohr
    cutoff_b = profile_b.cutoff_radius_bohr
    separation, regime = _cutoff_regime(distance_bohr, cutoff_a, cutoff_b)

    if profile_a.profile.atomic_number == profile_b.profile.atomic_number:
        position = distance_bohr / 2.0
        rho_a, rho_b, rho_sum = _component_values(
            profile_a,
            profile_b,
            distance_bohr,
            position,
        )
        return _NativeIASResult(
            requested_mode="minimum",
            method="homonuclear_midpoint",
            status="low_density_gap" if regime == "gap" else "ok",
            position_bohr=position,
            rho_a=rho_a,
            rho_b=rho_b,
            rho_sum=rho_sum,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
            search_resolution_bohr=IAS_MINIMUM_RESOLUTION_BOHR,
            search_converged=True,
            search_passes=0,
        )

    if regime in ("contact", "gap"):
        return _NativeIASResult(
            requested_mode="minimum",
            method="none",
            status="low_density_gap",
            position_bohr=None,
            rho_a=None,
            rho_b=None,
            rho_sum=None,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
            search_resolution_bohr=IAS_MINIMUM_RESOLUTION_BOHR,
            search_converged=None,
            search_passes=0,
        )

    overlap_left = max(0.0, distance_bohr - cutoff_b)
    overlap_right = min(distance_bohr, cutoff_a)

    equal_position, _ = _equal_contribution_position(
        profile_a,
        profile_b,
        distance_bohr,
    )
    coarse = _minimum_grid_pass(
        profile_a,
        profile_b,
        distance_bohr,
        overlap_left,
        overlap_right,
        _MINIMUM_INITIAL_SPACING_BOHR,
        equal_position,
    )
    fine = _minimum_grid_pass(
        profile_a,
        profile_b,
        distance_bohr,
        overlap_left,
        overlap_right,
        _MINIMUM_CONFIRM_SPACING_BOHR,
        equal_position,
    )

    executed_passes = [coarse, fine]
    final_spacing_bohr = fine.max_spacing_bohr
    search_passes = 2
    search_converged = True
    if not _selections_compatible(coarse.selected, fine.selected):
        fallback = _minimum_grid_pass(
            profile_a,
            profile_b,
            distance_bohr,
            overlap_left,
            overlap_right,
            _MINIMUM_FALLBACK_SPACING_BOHR,
            equal_position,
        )
        executed_passes.append(fallback)
        final_spacing_bohr = fallback.max_spacing_bohr
        search_passes = 3
        search_converged = _selections_compatible(
            fine.selected,
            fallback.selected,
        )

    final_pass = _MinimumPass(
        max_spacing_bohr=final_spacing_bohr,
        candidates=_combine_confirmed_minimum_candidates(
            *executed_passes,
            candidate_filter=lambda candidate: (
                overlap_left < candidate.position_bohr < overlap_right
                and _minimum_candidate_is_publicly_strict(
                    candidate,
                    distance_bohr,
                    cutoff_a,
                    cutoff_b,
                    public_presentations,
                )
            ),
        ),
    )

    selected = final_pass.selected
    if selected is None:
        return _NativeIASResult(
            requested_mode="minimum",
            method="none",
            status="no_resolved_interior_minimum",
            position_bohr=None,
            rho_a=None,
            rho_b=None,
            rho_sum=None,
            cutoff_radius_a_bohr=cutoff_a,
            cutoff_radius_b_bohr=cutoff_b,
            contour_separation_bohr=separation,
            cutoff_regime=regime,
            search_resolution_bohr=final_pass.max_spacing_bohr,
            search_converged=search_converged,
            search_passes=search_passes,
        )

    alternative = (
        final_pass.candidates[1] if len(final_pass.candidates) > 1 else None
    )
    relative_depth_gap = None
    ambiguous = False
    if alternative is not None:
        relative_depth_gap = max(
            0.0,
            (alternative.density - selected.density) / selected.density,
        )
        ambiguous = relative_depth_gap <= _COMPETITIVE_RELATIVE_DEPTH

    status: _IASStatus = "ambiguous_competing_minima" if ambiguous else "ok"
    if not search_converged:
        status = "search_unstable"

    boundary_density = min(
        _objective(profile_a, profile_b, distance_bohr, 0.0),
        _objective(profile_a, profile_b, distance_bohr, distance_bohr),
    )
    if _less_beyond_roundoff(boundary_density, selected.density):
        status = "boundary_dominated"

    rho_a, rho_b, rho_sum = _component_values(
        profile_a,
        profile_b,
        distance_bohr,
        selected.position_bohr,
    )
    return _NativeIASResult(
        requested_mode="minimum",
        method="promolecular_density_minimum",
        status=status,
        position_bohr=selected.position_bohr,
        rho_a=rho_a,
        rho_b=rho_b,
        rho_sum=rho_sum,
        cutoff_radius_a_bohr=cutoff_a,
        cutoff_radius_b_bohr=cutoff_b,
        contour_separation_bohr=separation,
        cutoff_regime=regime,
        alternative_position_bohr=(
            None if alternative is None else alternative.position_bohr
        ),
        alternative_rho_sum=(
            None if alternative is None else alternative.density
        ),
        relative_depth_gap=relative_depth_gap,
        ambiguous=ambiguous,
        search_resolution_bohr=final_pass.max_spacing_bohr,
        search_converged=search_converged,
        search_passes=search_passes,
    )


def _validate_pair_distance(
    distance: float,
    *,
    distance_unit: str,
) -> tuple[float, float]:
    """Validate a public pair distance and return requested/native values."""

    if distance_unit not in ("angstrom", "bohr"):
        raise ValueError(f"unknown distance unit: {distance_unit!r}")
    if isinstance(distance, bool):
        raise ValueError("distance must be a finite positive scalar")
    try:
        requested_distance = float(distance)
    except (TypeError, ValueError) as exc:
        raise ValueError("distance must be a finite positive scalar") from exc
    if not math.isfinite(requested_distance):
        raise ValueError("distance must be finite")
    if requested_distance <= 0.0:
        raise ValueError("distance must be strictly positive")

    public_max = (
        20.0 if distance_unit == "bohr" else 20.0 * BOHR_TO_ANGSTROM
    )
    if requested_distance > public_max:
        raise ValueError("distance exceeds the public limit of 20 bohr")
    if distance_unit == "bohr":
        return requested_distance, requested_distance
    return requested_distance, min(requested_distance / BOHR_TO_ANGSTROM, 20.0)


def _density_output_factor(density_unit: str) -> float:
    """Validate an output density unit and return its native scale factor."""

    return _density_from_native(1.0, density_unit=density_unit)


def _assemble_pairwise_result(
    native: _NativeIASResult,
    *,
    requested_profile_a: ProatomicDensityProfile,
    requested_profile_b: ProatomicDensityProfile,
    canonical_profile_a: _PreparedPairwiseProfile,
    canonical_profile_b: _PreparedPairwiseProfile,
    canonical_was_reversed: bool,
    requested_distance: float,
    distance_bohr: float,
    distance_unit: str,
    density_unit: str,
) -> IASPositionResult:
    """Apply requested orientation and units to one complete native result."""

    distance_factor = 1.0 if distance_unit == "bohr" else BOHR_TO_ANGSTROM
    density_factor = _density_output_factor(density_unit)

    def oriented_coordinate_pair(
        canonical_position: float | None,
    ) -> tuple[float | None, float | None, float | None]:
        if canonical_position is None:
            return None, None, None
        canonical_from_a = (
            requested_distance / 2.0
            if native.method == "homonuclear_midpoint"
            else canonical_position * distance_factor
        )
        canonical_from_b = requested_distance - canonical_from_a
        canonical_fraction = canonical_from_a / requested_distance
        if canonical_was_reversed:
            return (
                canonical_from_b,
                canonical_from_a,
                canonical_from_b / requested_distance,
            )
        return canonical_from_a, canonical_from_b, canonical_fraction

    position_a, position_b, fraction_a = oriented_coordinate_pair(
        native.position_bohr
    )
    alternative_a, alternative_b, _ = oriented_coordinate_pair(
        native.alternative_position_bohr
    )

    if canonical_was_reversed:
        rho_a_native, rho_b_native = native.rho_b, native.rho_a
        cutoff_a_native = native.cutoff_radius_b_bohr
        cutoff_b_native = native.cutoff_radius_a_bohr
    else:
        rho_a_native, rho_b_native = native.rho_a, native.rho_b
        cutoff_a_native = native.cutoff_radius_a_bohr
        cutoff_b_native = native.cutoff_radius_b_bohr

    dominant_atom = None
    dominant_atom_role: _DominantAtomRole | None = None
    if native.dominant_side is not None:
        canonical_dominant = (
            canonical_profile_a
            if native.dominant_side == "a"
            else canonical_profile_b
        )
        dominant_atom = canonical_dominant.profile.symbol
        dominant_is_requested_a = (
            native.dominant_side == "a" and not canonical_was_reversed
        ) or (native.dominant_side == "b" and canonical_was_reversed)
        dominant_atom_role = "atom_a" if dominant_is_requested_a else "atom_b"

    return IASPositionResult(
        atom_a=requested_profile_a.symbol,
        atom_b=requested_profile_b.symbol,
        distance=requested_distance,
        distance_unit=distance_unit,
        density_unit=density_unit,
        requested_mode=native.requested_mode,
        method=native.method,
        status=native.status,
        position_from_a=position_a,
        position_from_b=position_b,
        fraction_from_a=fraction_a,
        rho_a=None if rho_a_native is None else rho_a_native * density_factor,
        rho_b=None if rho_b_native is None else rho_b_native * density_factor,
        rho_sum=(
            None if native.rho_sum is None else native.rho_sum * density_factor
        ),
        cutoff_density=PROATOMIC_TAIL_CUTOFF * density_factor,
        cutoff_radius_a=cutoff_a_native * distance_factor,
        cutoff_radius_b=cutoff_b_native * distance_factor,
        contour_separation=native.contour_separation_bohr * distance_factor,
        cutoff_regime=native.cutoff_regime,
        dominant_atom=dominant_atom,
        dominant_atom_role=dominant_atom_role,
        alternative_position_from_a=alternative_a,
        alternative_position_from_b=alternative_b,
        alternative_rho_sum=(
            None
            if native.alternative_rho_sum is None
            else native.alternative_rho_sum * density_factor
        ),
        relative_depth_gap=native.relative_depth_gap,
        ambiguous=native.ambiguous,
        search_resolution=(
            None
            if native.search_resolution_bohr is None
            else native.search_resolution_bohr * distance_factor
        ),
        search_converged=native.search_converged,
        search_passes=native.search_passes,
        dataset_id=requested_profile_a.ref.set_id,
        interpolation_contract=requested_profile_a.interpolation_contract,
        pairwise_contract=_PAIRWISE_CONTRACT,
    )


def _estimate_pairwise(
    atom_a: str | int | None,
    atom_b: str | int | None,
    distance: float,
    *,
    mode: Literal["boundary", "minimum"],
    distance_unit: str,
    density_unit: str,
    set_id: str,
) -> IASPositionResult | None:
    """Validate, canonicalize, compute, and assemble one pairwise estimate."""

    requested_distance, distance_bohr = _validate_pair_distance(
        distance,
        distance_unit=distance_unit,
    )
    _density_output_factor(density_unit)

    dataset, _ = _resolve_proatomic_density_set(set_id)

    resolved_a = _resolve_density_element(atom_a)
    resolved_b = _resolve_density_element(atom_b)
    if resolved_a is None or resolved_b is None:
        return None

    if dataset.get(resolved_a.z) is None or dataset.get(resolved_b.z) is None:
        return None
    requested_profile_a = _get_profile_cached(dataset.ref, resolved_a.z)
    requested_profile_b = _get_profile_cached(dataset.ref, resolved_b.z)

    prepared_a = _prepared_pairwise_profile(requested_profile_a)
    prepared_b = _prepared_pairwise_profile(requested_profile_b)
    canonical_was_reversed = (
        prepared_a.profile.atomic_number > prepared_b.profile.atomic_number
    )
    if canonical_was_reversed:
        canonical_a, canonical_b = prepared_b, prepared_a
    else:
        canonical_a, canonical_b = prepared_a, prepared_b

    contact_distance_bohr = (
        canonical_a.cutoff_radius_bohr + canonical_b.cutoff_radius_bohr
    )
    contact_distances_requested: tuple[float, ...]
    if distance_unit == "bohr":
        contact_distances_requested = (contact_distance_bohr,)
    else:
        contact_distances_requested = (
            contact_distance_bohr * BOHR_TO_ANGSTROM,
            canonical_a.cutoff_radius_bohr * BOHR_TO_ANGSTROM
            + canonical_b.cutoff_radius_bohr * BOHR_TO_ANGSTROM,
        )
    if requested_distance in contact_distances_requested:
        # Preserve an exact physical cutoff contact across the named input
        # units without broadening the binding native ``d_c > 0`` branch.
        distance_bohr = contact_distance_bohr

    if mode == "boundary":
        native = _native_boundary_estimate(
            canonical_a,
            canonical_b,
            distance_bohr,
        )
    else:
        distance_factor = (
            1.0 if distance_unit == "bohr" else BOHR_TO_ANGSTROM
        )
        native = _native_minimum_estimate(
            canonical_a,
            canonical_b,
            distance_bohr,
            public_presentations=((requested_distance, distance_factor),),
        )

    return _assemble_pairwise_result(
        native,
        requested_profile_a=requested_profile_a,
        requested_profile_b=requested_profile_b,
        canonical_profile_a=canonical_a,
        canonical_profile_b=canonical_b,
        canonical_was_reversed=canonical_was_reversed,
        requested_distance=requested_distance,
        distance_bohr=distance_bohr,
        distance_unit=distance_unit,
        density_unit=density_unit,
    )


def estimate_proatomic_boundary(
    atom_a: str | int | None,
    atom_b: str | int | None,
    distance: float,
    *,
    distance_unit: Literal["angstrom", "bohr"] = "angstrom",
    density_unit: Literal[
        "electron/bohr^3", "electron/angstrom^3"
    ] = "electron/bohr^3",
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> IASPositionResult | None:
    """Estimate a stable pairwise neutral-proatom boundary.

    Args:
        atom_a: First element symbol or atomic number. D/T map to H.
        atom_b: Second element symbol or atomic number. D/T map to H.
        distance: Finite positive pair distance in `distance_unit`, no greater
            than 20 bohr after conversion.
        distance_unit: ``"angstrom"`` (default) or ``"bohr"``. Returned
            coordinates and cutoff radii use the same unit.
        density_unit: ``"electron/bohr^3"`` (default) or
            ``"electron/angstrom^3"`` for reported density fields.
        set_id: Canonical proatomic-density set ID or alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        An [IASPositionResult][atomref.proatoms.IASPositionResult] oriented from
        atom A toward atom B, or `None` when either profile is invalid or
        unavailable. A valid one-atom-dominance case returns a typed result with
        no coordinate.

    Raises:
        ValueError: If distance or a unit is outside the public contract.
        DatasetError: If the selected dataset is unknown, malformed, or
            non-radial.

    Examples:
        >>> result = estimate_proatomic_boundary("C", "O", 1.5)
        >>> result is not None
        True
        >>> result.requested_mode
        'boundary'

    Notes:
        Homonuclear pairs use the exact midpoint. Overlapping unlike profiles
        use equal neutral-proatom density; separated fixed-cutoff contours use
        the midpoint of their gap. This stable divider is not a molecular QTAIM
        zero-flux surface.
    """

    return _estimate_pairwise(
        atom_a,
        atom_b,
        distance,
        mode="boundary",
        distance_unit=distance_unit,
        density_unit=density_unit,
        set_id=set_id,
    )


def estimate_promolecular_density_minimum(
    atom_a: str | int | None,
    atom_b: str | int | None,
    distance: float,
    *,
    distance_unit: Literal["angstrom", "bohr"] = "angstrom",
    density_unit: Literal[
        "electron/bohr^3", "electron/angstrom^3"
    ] = "electron/bohr^3",
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> IASPositionResult | None:
    """Estimate one practically resolved promolecular line-density minimum.

    Args:
        atom_a: First element symbol or atomic number. D/T map to H.
        atom_b: Second element symbol or atomic number. D/T map to H.
        distance: Finite positive pair distance in `distance_unit`, no greater
            than 20 bohr after conversion.
        distance_unit: ``"angstrom"`` (default) or ``"bohr"``. Returned
            coordinates and search resolution use the same unit.
        density_unit: ``"electron/bohr^3"`` (default) or
            ``"electron/angstrom^3"`` for reported density fields.
        set_id: Canonical proatomic-density set ID or alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        An [IASPositionResult][atomref.proatoms.IASPositionResult] oriented from
        atom A toward atom B, or `None` when either profile is invalid or
        unavailable. A valid pair with no resolved strict-interior minimum
        returns a typed result with no coordinate.

    Raises:
        ValueError: If distance or a unit is outside the public contract.
        DatasetError: If the selected dataset is unknown, malformed, or
            non-radial.

    Examples:
        >>> result = estimate_promolecular_density_minimum("C", "O", 1.5)
        >>> result is not None
        True
        >>> result.requested_mode
        'minimum'

    Notes:
        Search is confined to the interval where both neutral components meet
        [PROATOMIC_TAIL_CUTOFF][atomref.proatoms.PROATOMIC_TAIL_CUTOFF]. It has
        declared resolution
        [IAS_MINIMUM_RESOLUTION_BOHR][atomref.proatoms.IAS_MINIMUM_RESOLUTION_BOHR],
        exposes only strict-interior unlike-atom candidates, and never falls
        back to boundary mode. It is a practical
        neutral-promolecular proxy, not an exact molecular-density critical
        point.
    """

    return _estimate_pairwise(
        atom_a,
        atom_b,
        distance,
        mode="minimum",
        distance_unit=distance_unit,
        density_unit=density_unit,
        set_id=set_id,
    )


def estimate_ias_position(
    atom_a: str | int | None,
    atom_b: str | int | None,
    distance: float,
    *,
    mode: Literal["boundary", "minimum"] = "boundary",
    distance_unit: Literal["angstrom", "bohr"] = "angstrom",
    density_unit: Literal[
        "electron/bohr^3", "electron/angstrom^3"
    ] = "electron/bohr^3",
    set_id: str = DEFAULT_PROATOMIC_DENSITY_SET,
) -> IASPositionResult | None:
    """Dispatch explicitly to one pairwise neutral-proatom mode.

    Args:
        atom_a: First element symbol or atomic number. D/T map to H.
        atom_b: Second element symbol or atomic number. D/T map to H.
        distance: Finite positive pair distance in `distance_unit`, no greater
            than 20 bohr after conversion.
        mode: ``"boundary"`` (default) or ``"minimum"``.
        distance_unit: ``"angstrom"`` (default) or ``"bohr"``.
        density_unit: ``"electron/bohr^3"`` (default) or
            ``"electron/angstrom^3"``.
        set_id: Canonical proatomic-density set ID or alias. Defaults to
            [DEFAULT_PROATOMIC_DENSITY_SET][atomref.proatoms.DEFAULT_PROATOMIC_DENSITY_SET].

    Returns:
        The same [IASPositionResult][atomref.proatoms.IASPositionResult] or
        missing-profile `None` produced by the corresponding direct estimator.

    Raises:
        ValueError: If `mode`, distance, or a unit is outside the public
            contract.
        DatasetError: If the selected dataset is unknown, malformed, or
            non-radial.

    Examples:
        >>> direct = estimate_proatomic_boundary("C", "O", 1.5)
        >>> selected = estimate_ias_position("C", "O", 1.5)
        >>> selected == direct
        True

    Notes:
        The minimum mode never silently falls back to boundary mode. The two
        modes are related scientific approximations, not interchangeable names
        for one calculation.
    """

    if mode not in ("boundary", "minimum"):
        raise ValueError(f"unknown IAS position mode: {mode!r}")
    return _estimate_pairwise(
        atom_a,
        atom_b,
        distance,
        mode=mode,
        distance_unit=distance_unit,
        density_unit=density_unit,
        set_id=set_id,
    )
