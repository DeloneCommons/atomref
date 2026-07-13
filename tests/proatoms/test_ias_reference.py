from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

import pytest

import atomref as ar


_REFERENCE_GRID_SPACING_BOHR = 0.001
_RESOLVED_VALLEY_SEPARATION_BOHR = 0.01
_COMPETING_RELATIVE_DEPTH = 1.0e-4


@dataclass(frozen=True, slots=True)
class _ReferenceCandidate:
    """One valley found by the independent dense reference."""

    position_bohr: float
    density: float


@dataclass(frozen=True, slots=True)
class _ReferenceSearch:
    """Independent cutoff-bounded reference result in native units."""

    overlap_left_bohr: float
    overlap_right_bohr: float
    max_grid_spacing_bohr: float
    cutoff_radius_a_bohr: float
    cutoff_radius_b_bohr: float
    raw_candidates: tuple[_ReferenceCandidate, ...]
    resolved_candidates: tuple[_ReferenceCandidate, ...]
    boundary_density: float
    status: str

    @property
    def selected(self) -> _ReferenceCandidate | None:
        """Return the lowest resolved valley, if present."""

        if not self.resolved_candidates:
            return None
        return self.resolved_candidates[0]

    @property
    def alternative(self) -> _ReferenceCandidate | None:
        """Return the second-lowest separated valley, if present."""

        if len(self.resolved_candidates) < 2:
            return None
        return self.resolved_candidates[1]


def _profile(symbol: str) -> ar.ProatomicDensityProfile:
    profile = ar.get_proatomic_density_profile(symbol)
    assert profile is not None
    return profile


def _independent_cutoff_radius(profile: ar.ProatomicDensityProfile) -> float:
    """Invert the public profile knots without a production cutoff helper."""

    cutoff = ar.PROATOMIC_TAIL_CUTOFF
    right = next(
        index
        for index, density in enumerate(profile.densities)
        if density <= cutoff
    )
    assert right > 0
    if profile.densities[right] == cutoff:
        return profile.radii[right]

    left = right - 1
    log_density_left = math.log(profile.densities[left])
    log_density_right = math.log(profile.densities[right])
    log_radius_left = math.log(profile.radii[left])
    log_radius_right = math.log(profile.radii[right])
    fraction = (math.log(cutoff) - log_density_left) / (
        log_density_right - log_density_left
    )
    return math.exp(
        log_radius_left + fraction * (log_radius_right - log_radius_left)
    )


def _objective(
    profile_a: ar.ProatomicDensityProfile,
    profile_b: ar.ProatomicDensityProfile,
    distance_bohr: float,
    position_bohr: float,
) -> float:
    """Evaluate the Stage 3 profiles directly in their native units."""

    return profile_a._evaluate_bohr(
        position_bohr
    ) + profile_b._evaluate_bohr(distance_bohr - position_bohr)


def _refine_by_fixed_subdivision(
    function: Callable[[float], float],
    left: float,
    center: float,
    right: float,
) -> _ReferenceCandidate:
    """Refine a bracket by repeated nine-point subdivision, not golden search."""

    center_value = function(center)
    best = _ReferenceCandidate(center, center_value)
    for _ in range(18):
        if math.nextafter(left, right) == right:
            break
        width = right - left
        points = tuple(left + width * index / 8 for index in range(9))
        values = tuple(function(point) for point in points)
        best_index = min(
            range(len(points)),
            key=lambda index: (values[index], points[index]),
        )
        local = _ReferenceCandidate(
            points[best_index],
            values[best_index],
        )
        if (local.density, local.position_bohr) < (
            best.density,
            best.position_bohr,
        ):
            best = local

        lower_index = max(0, best_index - 1)
        upper_index = min(8, best_index + 1)
        if lower_index == upper_index:
            break
        left, right = points[lower_index], points[upper_index]
    return best


def _scan_reference_objective(
    function: Callable[[float], float],
    overlap_left: float,
    overlap_right: float,
    max_spacing_bohr: float,
) -> tuple[float, tuple[_ReferenceCandidate, ...]]:
    """Find strict-interior valleys on one independent uniform reference grid."""

    if overlap_right <= overlap_left:
        return 0.0, ()
    width = overlap_right - overlap_left
    segment_count = max(2, math.ceil(width / max_spacing_bohr))
    max_grid_spacing = width / segment_count
    coordinates = [
        overlap_left + width * index / segment_count
        for index in range(segment_count + 1)
    ]
    # An odd segment count misses the exact interval midpoint. An even count
    # already contains it mathematically, so do not manufacture an adjacent-ULP
    # duplicate by evaluating the equivalent expression a second way.
    if segment_count % 2:
        coordinates.append((overlap_left + overlap_right) / 2.0)
        coordinates.sort()

    values = tuple(function(position) for position in coordinates)
    candidates: list[_ReferenceCandidate] = []
    for index in range(1, len(coordinates) - 1):
        if (
            values[index] <= values[index - 1]
            and values[index] <= values[index + 1]
        ):
            candidate = _refine_by_fixed_subdivision(
                function,
                coordinates[index - 1],
                coordinates[index],
                coordinates[index + 1],
            )
            if overlap_left < candidate.position_bohr < overlap_right:
                candidates.append(candidate)
    return max_grid_spacing, tuple(candidates)


def _coalesce_at_public_resolution(
    candidates: tuple[_ReferenceCandidate, ...],
    overlap_left: float,
    overlap_right: float,
) -> tuple[_ReferenceCandidate, ...]:
    """Group strict-interior candidates by position-connected components."""

    ordered = sorted(
        (
            candidate
            for candidate in candidates
            if overlap_left < candidate.position_bohr < overlap_right
        ),
        key=lambda candidate: candidate.position_bohr,
    )
    groups: list[list[_ReferenceCandidate]] = []
    for candidate in ordered:
        if (
            not groups
            or candidate.position_bohr - groups[-1][-1].position_bohr
            >= _RESOLVED_VALLEY_SEPARATION_BOHR
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
            key=lambda candidate: (
                candidate.density,
                candidate.position_bohr,
            ),
        )
    )


def _reference_status(
    candidates: tuple[_ReferenceCandidate, ...],
    boundary_density: float,
) -> str:
    """Classify the independently selected practical result."""

    if not candidates:
        return "no_resolved_interior_minimum"

    selected = candidates[0]
    roundoff = 128.0 * math.ulp(
        max(abs(boundary_density), abs(selected.density), 1.0)
    )
    if boundary_density < selected.density - roundoff:
        return "boundary_dominated"

    if len(candidates) > 1:
        relative_gap = max(
            0.0,
            (candidates[1].density - selected.density) / selected.density,
        )
        if relative_gap <= _COMPETING_RELATIVE_DEPTH:
            return "ambiguous_competing_minima"
    return "ok"


def _independent_reference_search(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
    *,
    max_spacing_bohr: float = _REFERENCE_GRID_SPACING_BOHR,
) -> _ReferenceSearch:
    """Search only ``I_c`` using an independent uniform-grid implementation."""

    profile_a = _profile(atom_a)
    profile_b = _profile(atom_b)
    cutoff_a = _independent_cutoff_radius(profile_a)
    cutoff_b = _independent_cutoff_radius(profile_b)
    overlap_left = max(0.0, distance_bohr - cutoff_b)
    overlap_right = min(distance_bohr, cutoff_a)

    def function(position: float) -> float:
        return _objective(
            profile_a,
            profile_b,
            distance_bohr,
            position,
        )

    boundary_density = min(function(0.0), function(distance_bohr))
    if overlap_right <= overlap_left:
        return _ReferenceSearch(
            overlap_left,
            overlap_right,
            0.0,
            cutoff_a,
            cutoff_b,
            (),
            (),
            boundary_density,
            "no_resolved_interior_minimum",
        )

    max_grid_spacing, raw_candidates = _scan_reference_objective(
        function,
        overlap_left,
        overlap_right,
        max_spacing_bohr,
    )
    resolved = _coalesce_at_public_resolution(
        raw_candidates,
        overlap_left,
        overlap_right,
    )
    return _ReferenceSearch(
        overlap_left,
        overlap_right,
        max_grid_spacing,
        cutoff_a,
        cutoff_b,
        raw_candidates,
        resolved,
        boundary_density,
        _reference_status(resolved, boundary_density),
    )


def _assert_matches_dense_reference(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
    expected_status: str,
) -> None:
    reference = _independent_reference_search(
        atom_a,
        atom_b,
        distance_bohr,
    )
    result = ar.estimate_promolecular_density_minimum(
        atom_a,
        atom_b,
        distance_bohr,
        distance_unit="bohr",
    )

    assert result is not None
    assert reference.max_grid_spacing_bohr <= _REFERENCE_GRID_SPACING_BOHR
    assert reference.status == expected_status
    assert result.status == expected_status
    assert result.method == "promolecular_density_minimum"
    assert result.cutoff_radius_a == pytest.approx(
        reference.cutoff_radius_a_bohr,
        rel=5.0e-13,
    )
    assert result.cutoff_radius_b == pytest.approx(
        reference.cutoff_radius_b_bohr,
        rel=5.0e-13,
    )

    selected = reference.selected
    assert selected is not None
    assert result.position_from_a is not None
    assert result.rho_sum is not None
    assert reference.overlap_left_bohr < result.position_from_a
    assert result.position_from_a < reference.overlap_right_bohr
    assert abs(result.position_from_a - selected.position_bohr) <= (
        ar.IAS_MINIMUM_RESOLUTION_BOHR
    )
    assert abs(result.rho_sum - selected.density) / selected.density <= 1.0e-4

    alternative = reference.alternative
    if expected_status == "ambiguous_competing_minima":
        assert alternative is not None
        assert result.alternative_position_from_a is not None
        assert result.alternative_rho_sum is not None
        assert abs(
            result.alternative_position_from_a - alternative.position_bohr
        ) <= ar.IAS_MINIMUM_RESOLUTION_BOHR
        assert abs(
            result.alternative_rho_sum - alternative.density
        ) / alternative.density <= 1.0e-4
        reference_gap = (
            alternative.density - selected.density
        ) / selected.density
        assert result.relative_depth_gap == pytest.approx(
            reference_gap,
            rel=2.0e-6,
            abs=1.0e-14,
        )


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "distance_bohr", "status"),
    [
        pytest.param("C", "O", 1.5, "ok", id="ordinary-c-o"),
        pytest.param("H", "U", 3.8, "ok", id="asymmetric-h-u"),
        pytest.param("At", "Bk", 4.0, "ok", id="heavy-at-bk"),
        pytest.param(
            "Fr",
            "Li",
            10.44712292574865,
            "ambiguous_competing_minima",
            id="competing-fr-li",
        ),
        pytest.param(
            "H",
            "Dy",
            1.5865200103109787,
            "boundary_dominated",
            id="boundary-dominated-h-dy",
        ),
    ],
)
def test_practical_minimum_matches_independent_dense_reference(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
    status: str,
) -> None:
    _assert_matches_dense_reference(
        atom_a,
        atom_b,
        distance_bohr,
        status,
    )


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "distance_bohr"),
    [
        pytest.param(
            "Ni",
            "Te",
            1.5897045597171517,
            id="archived-ni-te",
        ),
        pytest.param(
            "Al",
            "Pb",
            1.3645306063699802,
            id="archived-al-pb",
        ),
        pytest.param(
            "Pr",
            "Re",
            0.7592738817632778,
            id="archived-pr-re",
        ),
    ],
)
def test_archived_stage4a_resolved_cases_match_dense_reference(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
) -> None:
    _assert_matches_dense_reference(atom_a, atom_b, distance_bohr, "ok")


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "distance_bohr"),
    [
        pytest.param("H", "U", 1.58, id="archived-h-u"),
        pytest.param(
            "U",
            "H",
            0.05625504168898983,
            id="adjacent-ulp-midpoint-regression",
        ),
    ],
)
def test_difficult_short_pairs_have_no_independent_interior_valley(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
) -> None:
    reference = _independent_reference_search(
        atom_a,
        atom_b,
        distance_bohr,
    )
    result = ar.estimate_promolecular_density_minimum(
        atom_a,
        atom_b,
        distance_bohr,
        distance_unit="bohr",
    )

    assert not reference.raw_candidates
    assert result is not None
    assert result.status == "no_resolved_interior_minimum"
    assert result.method == "none"
    assert result.position_from_a is None
    assert result.rho_sum is None


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "distance_bohr", "near_nucleus"),
    [
        pytest.param(
            "C",
            "Lu",
            0.2217301367970158,
            True,
            id="archived-c-lu",
        ),
        pytest.param(
            "He",
            "Ru",
            0.6552909074349161,
            False,
            id="archived-he-ru",
        ),
    ],
)
def test_subresolution_dense_valleys_are_intentionally_unresolved(
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
    near_nucleus: bool,
) -> None:
    dense = _independent_reference_search(
        atom_a,
        atom_b,
        distance_bohr,
    )
    practical_grid = _independent_reference_search(
        atom_a,
        atom_b,
        distance_bohr,
        max_spacing_bohr=ar.IAS_MINIMUM_RESOLUTION_BOHR,
    )
    result = ar.estimate_promolecular_density_minimum(
        atom_a,
        atom_b,
        distance_bohr,
        distance_unit="bohr",
    )

    assert dense.selected is not None
    assert not practical_grid.raw_candidates
    if near_nucleus:
        assert dense.selected.position_bohr < ar.IAS_MINIMUM_RESOLUTION_BOHR
    assert result is not None
    assert result.status == "no_resolved_interior_minimum"
    assert result.method == "none"
    assert result.position_from_a is None


def test_homonuclear_shell_microstructure_cannot_move_public_midpoint() -> None:
    distance_bohr = 5.0
    reference = _independent_reference_search("Li", "Li", distance_bohr)
    result = ar.estimate_promolecular_density_minimum(
        "Li",
        "Li",
        distance_bohr,
        distance_unit="bohr",
    )

    assert len(reference.raw_candidates) >= 5
    assert reference.selected is not None
    assert abs(reference.selected.position_bohr - distance_bohr / 2.0) > (
        ar.IAS_MINIMUM_RESOLUTION_BOHR
    )
    assert result is not None
    assert result.method == "homonuclear_midpoint"
    assert result.position_from_a == distance_bohr / 2.0
    assert result.rho_sum is not None
    assert reference.selected.density < result.rho_sum


def test_heavy_pair_reference_and_public_result_reverse_together() -> None:
    distance_bohr = 4.0
    reference = _independent_reference_search("At", "Bk", distance_bohr)
    forward = ar.estimate_promolecular_density_minimum(
        "At",
        "Bk",
        distance_bohr,
        distance_unit="bohr",
    )
    reverse = ar.estimate_promolecular_density_minimum(
        "Bk",
        "At",
        distance_bohr,
        distance_unit="bohr",
    )

    assert reference.selected is not None
    assert forward is not None and reverse is not None
    assert forward.position_from_a is not None
    assert reverse.position_from_a is not None
    assert forward.rho_sum is not None and reverse.rho_sum is not None
    assert abs(
        forward.position_from_a - reference.selected.position_bohr
    ) <= ar.IAS_MINIMUM_RESOLUTION_BOHR
    assert reverse.position_from_a == pytest.approx(
        distance_bohr - forward.position_from_a,
        abs=2.0e-15,
    )
    assert reverse.rho_sum == pytest.approx(forward.rho_sum, rel=2.0e-15)
    assert reverse.status == forward.status
    assert reverse.method == forward.method


def test_packaged_y_np_reference_rejects_false_competitive_alternative() -> None:
    distance_bohr = 10.212596531891476
    reference = _independent_reference_search("Y", "Np", distance_bohr)
    result = ar.estimate_promolecular_density_minimum(
        "Y",
        "Np",
        distance_bohr,
        distance_unit="bohr",
    )

    assert result is not None
    assert reference.status == result.status == "ok"
    assert reference.selected is not None
    assert reference.alternative is None
    assert result.position_from_a == pytest.approx(
        reference.selected.position_bohr,
        abs=ar.IAS_MINIMUM_RESOLUTION_BOHR,
    )
    assert result.alternative_position_from_a is None
    assert result.alternative_rho_sum is None
    assert result.ambiguous is False


@pytest.mark.parametrize(
    ("atom_b", "distance_bohr", "midpoint_bohr"),
    [
        ("Mg", 10.427738551450130, 4.128012047240235),
        ("K", 11.554061800270143, 4.128012047240236),
    ],
)
def test_adjacent_float_midpoint_valley_matches_independent_reference(
    atom_b: str,
    distance_bohr: float,
    midpoint_bohr: float,
) -> None:
    reference = _independent_reference_search("H", atom_b, distance_bohr)
    result = ar.estimate_promolecular_density_minimum(
        "H",
        atom_b,
        distance_bohr,
        distance_unit="bohr",
    )

    assert result is not None
    assert reference.status == result.status == "ok"
    assert reference.selected is not None
    assert reference.selected.position_bohr == midpoint_bohr
    assert result.position_from_a == midpoint_bohr
    assert result.rho_sum == reference.selected.density


def test_reference_grouping_uses_position_connected_components() -> None:
    candidates = tuple(
        _ReferenceCandidate(position, density)
        for position, density in (
            (0.100, 1.0),
            (0.109, 1.0001),
            (0.118, 1.00005),
        )
    )

    resolved = _coalesce_at_public_resolution(candidates, 0.0, 1.0)

    assert resolved == (_ReferenceCandidate(0.100, 1.0),)


def test_reference_grouping_rejects_endpoints_but_retains_interior() -> None:
    left = 0.0
    right = 1.0
    first_interior = math.nextafter(left, right)
    last_interior = math.nextafter(right, left)
    candidates = (
        _ReferenceCandidate(left, 0.5),
        _ReferenceCandidate(first_interior, 1.0),
        _ReferenceCandidate(0.5, 2.0),
        _ReferenceCandidate(last_interior, 1.5),
        _ReferenceCandidate(right, 0.5),
    )

    resolved = _coalesce_at_public_resolution(candidates, left, right)

    assert all(left < candidate.position_bohr < right for candidate in resolved)
    assert first_interior in {
        candidate.position_bohr for candidate in resolved
    }
    assert last_interior in {
        candidate.position_bohr for candidate in resolved
    }


@pytest.mark.parametrize(
    ("center", "detected_spacing", "missed_spacing"),
    [
        (1.07 * 26.0 / 54.0, 0.02, 0.01),
        (1.07 * 53.0 / 107.0, 0.01, 0.02),
    ],
)
def test_reference_scanner_resolves_non_nested_grid_valleys_independently(
    center: float,
    detected_spacing: float,
    missed_spacing: float,
) -> None:
    half_width = 0.002

    def function(position: float) -> float:
        broad = 1.0 + (position - 0.2) ** 2
        offset = abs(position - center)
        if offset >= half_width:
            return broad
        shape = (1.0 - (offset / half_width) ** 2) ** 2
        depth = 1.0 + (center - 0.2) ** 2 - 1.00005
        return broad - depth * shape

    _, detected = _scan_reference_objective(
        function,
        0.0,
        1.07,
        detected_spacing,
    )
    _, missed = _scan_reference_objective(
        function,
        0.0,
        1.07,
        missed_spacing,
    )
    _, dense = _scan_reference_objective(function, 0.0, 1.07, 0.001)

    assert any(
        abs(candidate.position_bohr - center) < half_width
        for candidate in detected
    )
    assert not any(
        abs(candidate.position_bohr - center) < half_width
        for candidate in missed
    )
    assert any(
        abs(candidate.position_bohr - center) < half_width
        for candidate in dense
    )


@pytest.mark.parametrize(("atom_a", "atom_b"), [("H", "O"), ("O", "H")])
@pytest.mark.parametrize("steps_below", [1, 2])
def test_reference_rejects_near_contact_cutoff_endpoints(
    atom_a: str,
    atom_b: str,
    steps_below: int,
) -> None:
    cutoff_a = _independent_cutoff_radius(_profile("H"))
    cutoff_b = _independent_cutoff_radius(_profile("O"))
    distance = cutoff_a + cutoff_b
    for _ in range(steps_below):
        distance = math.nextafter(distance, 0.0)

    reference = _independent_reference_search(atom_a, atom_b, distance)

    for candidate in (
        *reference.raw_candidates,
        *reference.resolved_candidates,
    ):
        assert (
            reference.overlap_left_bohr
            < candidate.position_bohr
            < reference.overlap_right_bohr
        )
    if not reference.raw_candidates:
        assert reference.status == "no_resolved_interior_minimum"
        assert not reference.resolved_candidates


@pytest.mark.parametrize(("atom_a", "atom_b"), [("H", "O"), ("O", "H")])
def test_reference_rejects_extreme_unlike_nuclear_candidate(
    atom_a: str,
    atom_b: str,
) -> None:
    reference = _independent_reference_search(atom_a, atom_b, 2.0e-323)

    assert reference.status == "no_resolved_interior_minimum"
    assert not reference.raw_candidates
    assert not reference.resolved_candidates
