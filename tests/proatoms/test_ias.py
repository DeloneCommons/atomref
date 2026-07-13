from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
import math
from types import MappingProxyType

import pytest

import atomref as ar
from atomref.errors import DatasetError
import atomref.proatoms as proatoms


_DATASET_ID = "pbe0_sfx2c_dyallv4z_h-lr_neutral_v2"
_INTERPOLATION_CONTRACT = "loglog_positive_bracketed_v1"
_PAIRWISE_CONTRACT = "neutral_proatom_pairwise_cutoff_1e-4_resolution_0.01_v1"

_AMBIGUOUS_CASE = ("Mn", "Gd", 9.699418444855935)
_BOUNDARY_DOMINATED_CASE = ("Zn", "He", 0.742706534980151)
_NO_RESOLVED_CASE = ("C", "Lu", 0.2217301367970158)
_UNSTABLE_CASE = ("Be", "Cm", 5.209173731112204)


def _result(value: ar.IASPositionResult | None) -> ar.IASPositionResult:
    assert value is not None
    return value


def _profile(symbol: str) -> ar.ProatomicDensityProfile:
    profile = ar.get_proatomic_density_profile(symbol)
    assert profile is not None
    return profile


def _independent_cutoff_radius(profile: ar.ProatomicDensityProfile) -> float:
    cutoff = ar.PROATOMIC_TAIL_CUTOFF
    right = next(
        index
        for index, density in enumerate(profile.densities)
        if density <= cutoff
    )
    if profile.densities[right] == cutoff:
        return profile.radii[right]
    left = right - 1
    log_radius_left = math.log(profile.radii[left])
    log_radius_right = math.log(profile.radii[right])
    log_density_left = math.log(profile.densities[left])
    log_density_right = math.log(profile.densities[right])
    fraction = (math.log(cutoff) - log_density_left) / (
        log_density_right - log_density_left
    )
    return math.exp(
        log_radius_left + fraction * (log_radius_right - log_radius_left)
    )


def _pair_density_sum(
    profile_a: ar.ProatomicDensityProfile,
    profile_b: ar.ProatomicDensityProfile,
    distance_bohr: float,
    position_bohr: float,
) -> float:
    return profile_a(position_bohr, radius_unit="bohr") + profile_b(
        distance_bohr - position_bohr,
        radius_unit="bohr",
    )


def _synthetic_profile(
    densities: tuple[float, ...],
    *,
    radii: tuple[float, ...] = (0.1, 1.0, 4.0, 10.0, 20.0, 21.0),
    set_id: str,
) -> ar.ProatomicDensityProfile:
    ref = ar.DatasetRef("proatomic_density", set_id)
    info = ar.DatasetInfo(
        ref=ref,
        domain="element",
        units="electron/bohr^3",
        name="Synthetic pairwise profile",
        storage=MappingProxyType(
            {
                "native_coordinate_unit": "bohr",
                "native_density_unit": "electron/bohr^3",
                "public_max_radius_bohr": 20.0,
                "interpolation_contract": _INTERPOLATION_CONTRACT,
            }
        ),
    )
    dataset = ar.ElementRadialSet(
        ref=ref,
        info=info,
        radii=radii,
        profiles_by_z=(None, densities),
    )
    return ar.ProatomicDensityProfile(dataset=dataset, atomic_number=1)


def _assert_reversal(
    forward: ar.IASPositionResult,
    reverse: ar.IASPositionResult,
    distance_bohr: float,
) -> None:
    assert reverse.method == forward.method
    assert reverse.status == forward.status
    assert reverse.cutoff_regime == forward.cutoff_regime
    assert reverse.search_converged == forward.search_converged
    assert reverse.search_passes == forward.search_passes
    assert reverse.search_resolution == forward.search_resolution
    assert reverse.relative_depth_gap == forward.relative_depth_gap
    assert reverse.ambiguous == forward.ambiguous
    assert reverse.cutoff_radius_a == forward.cutoff_radius_b
    assert reverse.cutoff_radius_b == forward.cutoff_radius_a
    assert reverse.contour_separation == forward.contour_separation

    if forward.position_from_a is None:
        assert reverse.position_from_a is None
        assert reverse.position_from_b is None
        assert reverse.fraction_from_a is None
    else:
        assert reverse.position_from_a == pytest.approx(
            distance_bohr - forward.position_from_a,
            abs=2.0e-12,
        )
        assert reverse.position_from_b == pytest.approx(
            forward.position_from_a,
            abs=2.0e-12,
        )
        assert reverse.fraction_from_a == pytest.approx(
            1.0 - forward.fraction_from_a,
            abs=2.0e-15,
        )
        assert reverse.rho_a == pytest.approx(forward.rho_b, rel=2.0e-14)
        assert reverse.rho_b == pytest.approx(forward.rho_a, rel=2.0e-14)
        assert reverse.rho_sum == pytest.approx(forward.rho_sum, rel=2.0e-14)

    if forward.alternative_position_from_a is None:
        assert reverse.alternative_position_from_a is None
        assert reverse.alternative_position_from_b is None
        assert reverse.alternative_rho_sum is None
    else:
        assert reverse.alternative_position_from_a == pytest.approx(
            distance_bohr - forward.alternative_position_from_a,
            abs=2.0e-12,
        )
        assert reverse.alternative_position_from_b == pytest.approx(
            forward.alternative_position_from_a,
            abs=2.0e-12,
        )
        assert reverse.alternative_rho_sum == pytest.approx(
            forward.alternative_rho_sum,
            rel=2.0e-14,
        )


def _assert_minimum_coordinates_strictly_inside_overlap(
    result: ar.IASPositionResult,
) -> None:
    """Check that exposed unlike-atom minima are not overlap endpoints."""

    if result.requested_mode != "minimum" or result.atom_a == result.atom_b:
        return
    overlap_left = max(0.0, result.distance - result.cutoff_radius_b)
    overlap_right = min(result.distance, result.cutoff_radius_a)
    for position in (
        result.position_from_a,
        result.alternative_position_from_a,
    ):
        if position is not None:
            assert overlap_left < position < overlap_right
            assert 0.0 < position < result.distance


def test_public_functions_and_dispatcher_default_are_consistent() -> None:
    signature = inspect.signature(ar.estimate_ias_position)
    assert signature.parameters["mode"].default == "boundary"

    direct_boundary = ar.estimate_proatomic_boundary(
        "C", "O", 3.0, distance_unit="bohr"
    )
    direct_minimum = ar.estimate_promolecular_density_minimum(
        "C", "O", 3.0, distance_unit="bohr"
    )
    assert ar.estimate_ias_position(
        "C", "O", 3.0, distance_unit="bohr"
    ) == direct_boundary
    assert ar.estimate_ias_position(
        "C", "O", 3.0, mode="boundary", distance_unit="bohr"
    ) == direct_boundary
    assert ar.estimate_ias_position(
        "C", "O", 3.0, mode="minimum", distance_unit="bohr"
    ) == direct_minimum
    assert _result(direct_boundary).requested_mode == "boundary"
    assert _result(direct_minimum).requested_mode == "minimum"


def test_result_is_frozen_slotted_and_carries_complete_provenance() -> None:
    result = _result(
        ar.estimate_proatomic_boundary("C", "O", 3.0, distance_unit="bohr")
    )
    assert isinstance(result, ar.IASPositionResult)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.status = "low_density_gap"

    assert result.atom_a == "C"
    assert result.atom_b == "O"
    assert result.distance == 3.0
    assert result.distance_unit == "bohr"
    assert result.density_unit == "electron/bohr^3"
    assert result.coordinate_orientation == "from_atom_a_toward_atom_b"
    assert result.dataset_id == _DATASET_ID
    assert result.interpolation_contract == _INTERPOLATION_CONTRACT
    assert result.pairwise_contract == _PAIRWISE_CONTRACT
    assert result.cutoff_density == ar.PROATOMIC_TAIL_CUTOFF
    assert result.position_from_a is not None
    assert result.position_from_b is not None
    assert result.fraction_from_a is not None
    assert result.rho_a is not None
    assert result.rho_b is not None
    assert result.rho_sum is not None
    assert result.position_from_a + result.position_from_b == pytest.approx(3.0)
    assert result.fraction_from_a == pytest.approx(result.position_from_a / 3.0)
    assert result.rho_sum == pytest.approx(result.rho_a + result.rho_b)
    assert result.rho_a == pytest.approx(
        _profile("C")(result.position_from_a, radius_unit="bohr")
    )
    assert result.rho_b == pytest.approx(
        _profile("O")(result.position_from_b, radius_unit="bohr")
    )


def test_every_packaged_profile_has_one_analytical_cutoff_radius() -> None:
    seen = 0
    for element in ar.iter_elements():
        if element.z > 103:
            break
        profile = _profile(element.symbol)
        assert all(
            right < left
            for left, right in zip(profile.densities, profile.densities[1:])
        ), element.symbol
        assert profile.densities[0] > ar.PROATOMIC_TAIL_CUTOFF
        crossing_indices = [
            index
            for index in range(1, len(profile.densities))
            if (
                profile.densities[index - 1] > ar.PROATOMIC_TAIL_CUTOFF
                and profile.densities[index] <= ar.PROATOMIC_TAIL_CUTOFF
            )
        ]
        assert len(crossing_indices) == 1, element.symbol

        prepared = proatoms._prepared_pairwise_profile(profile)
        expected = _independent_cutoff_radius(profile)
        assert math.isfinite(prepared.cutoff_radius_bohr), element.symbol
        assert 0.0 < prepared.cutoff_radius_bohr < 20.0, element.symbol
        assert prepared.cutoff_radius_bohr == pytest.approx(
            expected,
            rel=2.0e-14,
        ), element.symbol
        reproduced = profile(
            prepared.cutoff_radius_bohr,
            radius_unit="bohr",
        )
        assert reproduced == pytest.approx(
            ar.PROATOMIC_TAIL_CUTOFF,
            rel=5.0e-14,
        ), element.symbol
        seen += 1
    assert seen == 103


def test_pairwise_profile_preparation_is_lazy_cached_and_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile("O")
    proatoms._get_prepared_pairwise_profile_cached.cache_clear()
    real_prepare = proatoms._prepare_pairwise_profile
    calls = 0

    def counting_prepare(
        candidate: ar.ProatomicDensityProfile,
    ) -> proatoms._PreparedPairwiseProfile:
        nonlocal calls
        calls += 1
        return real_prepare(candidate)

    monkeypatch.setattr(proatoms, "_prepare_pairwise_profile", counting_prepare)
    profile(1.0, radius_unit="bohr")
    ar.get_proatomic_density_set_info()
    assert calls == 0

    first = proatoms._prepared_pairwise_profile(profile)
    second = proatoms._prepared_pairwise_profile(profile)
    assert first is second
    assert calls == 1
    cache_info = proatoms._get_prepared_pairwise_profile_cached.cache_info()
    assert cache_info.misses == 1
    assert cache_info.hits == 1


def test_cutoff_preparation_accepts_an_exact_cutoff_knot() -> None:
    profile = _synthetic_profile(
        (1.0, 0.1, 0.01, 0.0001, 0.00001, 0.000001),
        radii=(0.1, 1.0, 4.0, 10.0, 15.0, 20.0),
        set_id="synthetic_exact_cutoff",
    )
    prepared = proatoms._prepare_pairwise_profile(profile)
    assert prepared.cutoff_radius_bohr == profile.radii[3]


@pytest.mark.parametrize(
    ("densities", "set_id", "message"),
    [
        (
            (1.0, 0.1, 0.1, 0.001, 0.0001, 0.00001),
            "synthetic_not_strict",
            "strictly decreasing",
        ),
        (
            (0.0001, 0.00009, 0.00008, 0.00007, 0.00006, 0.00005),
            "synthetic_first_below",
            "first proatomic density",
        ),
        (
            (1.0, 0.1, 0.01, 0.001, 0.0002, 0.00011),
            "synthetic_never_below",
            "does not fall below",
        ),
        (
            (1.0, 0.1, 0.01, 0.001, 0.0002, 0.00001),
            "synthetic_after_public_limit",
            "before the public limit",
        ),
    ],
)
def test_cutoff_preparation_rejects_invalid_profile_contracts(
    densities: tuple[float, ...],
    set_id: str,
    message: str,
) -> None:
    profile = _synthetic_profile(densities, set_id=set_id)
    with pytest.raises(DatasetError, match=message):
        proatoms._prepare_pairwise_profile(profile)


@pytest.mark.parametrize("symbol", ["H", "Li"])
@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_homonuclear_pairs_return_exact_midpoint(
    symbol: str,
    mode: str,
) -> None:
    distance = 5.0
    result = _result(
        ar.estimate_ias_position(
            symbol,
            symbol,
            distance,
            mode=mode,
            distance_unit="bohr",
        )
    )
    assert result.method == "homonuclear_midpoint"
    assert result.position_from_a == distance / 2.0
    assert result.position_from_b == distance / 2.0
    assert result.fraction_from_a == 0.5
    assert result.rho_a == result.rho_b


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_homonuclear_cutoff_gap_keeps_midpoint(mode: str) -> None:
    distance = 10.0
    result = _result(
        ar.estimate_ias_position(
            "H",
            "H",
            distance,
            mode=mode,
            distance_unit="bohr",
        )
    )
    assert result.status == "low_density_gap"
    assert result.cutoff_regime == "gap"
    assert result.method == "homonuclear_midpoint"
    assert result.position_from_a == 5.0


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "distance"),
    [
        ("H", "O", 2.0),
        ("H", "Lr", 2.0),
        ("Fe", "La", 5.0),
        ("La", "U", 6.0),
    ],
)
def test_overlapping_unlike_boundary_balances_components(
    atom_a: str,
    atom_b: str,
    distance: float,
) -> None:
    result = _result(
        ar.estimate_proatomic_boundary(
            atom_a,
            atom_b,
            distance,
            distance_unit="bohr",
        )
    )
    assert result.method == "equal_proatom_density"
    assert result.status == "ok"
    assert result.cutoff_regime == "overlap"
    assert result.position_from_a is not None
    assert 0.0 < result.position_from_a < distance
    assert result.rho_a == pytest.approx(result.rho_b, rel=2.0e-9)


def test_boundary_cutoff_gap_uses_geometric_contour_midpoint() -> None:
    distance = 10.0
    result = _result(
        ar.estimate_proatomic_boundary("H", "O", distance, distance_unit="bohr")
    )
    expected = (
        distance + result.cutoff_radius_a - result.cutoff_radius_b
    ) / 2.0
    assert result.method == "cutoff_gap_midpoint"
    assert result.status == "low_density_gap"
    assert result.cutoff_regime == "gap"
    assert result.contour_separation > 0.0
    assert result.position_from_a == expected


def test_boundary_branches_are_continuous_at_cutoff_contact() -> None:
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile("H")
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile("O")
    ).cutoff_radius_bohr
    contact_distance = cutoff_a + cutoff_b
    overlap = _result(
        ar.estimate_proatomic_boundary(
            "H",
            "O",
            contact_distance - 1.0e-7,
            distance_unit="bohr",
        )
    )
    contact = _result(
        ar.estimate_proatomic_boundary(
            "H", "O", contact_distance, distance_unit="bohr"
        )
    )
    gap = _result(
        ar.estimate_proatomic_boundary(
            "H",
            "O",
            contact_distance + 1.0e-7,
            distance_unit="bohr",
        )
    )
    assert overlap.method == "equal_proatom_density"
    assert overlap.cutoff_regime == "overlap"
    assert contact.method == "equal_proatom_density"
    assert contact.cutoff_regime == "contact"
    assert gap.method == "cutoff_gap_midpoint"
    assert gap.cutoff_regime == "gap"
    assert contact.position_from_a == pytest.approx(cutoff_a, abs=1.0e-9)
    assert overlap.position_from_a == pytest.approx(cutoff_a, abs=2.0e-7)
    assert gap.position_from_a == pytest.approx(cutoff_a, abs=2.0e-7)


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_exact_cutoff_contact_is_distance_unit_invariant(mode: str) -> None:
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile("F")
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile("Ne")
    ).cutoff_radius_bohr
    distance_bohr = cutoff_a + cutoff_b
    distance_angstrom = distance_bohr * ar.BOHR_TO_ANGSTROM

    native = _result(
        ar.estimate_ias_position(
            "F", "Ne", distance_bohr, mode=mode, distance_unit="bohr"
        )
    )
    converted = _result(
        ar.estimate_ias_position(
            "F", "Ne", distance_angstrom, mode=mode, distance_unit="angstrom"
        )
    )
    metadata_distance_angstrom = (
        native.cutoff_radius_a * ar.BOHR_TO_ANGSTROM
        + native.cutoff_radius_b * ar.BOHR_TO_ANGSTROM
    )
    reconstructed = _result(
        ar.estimate_ias_position(
            "F",
            "Ne",
            metadata_distance_angstrom,
            mode=mode,
            distance_unit="angstrom",
        )
    )

    assert (
        native.cutoff_regime
        == converted.cutoff_regime
        == reconstructed.cutoff_regime
        == "contact"
    )
    assert native.method == converted.method == reconstructed.method
    assert native.status == converted.status == reconstructed.status
    assert converted.contour_separation == 0.0
    if native.position_from_a is None:
        assert converted.position_from_a is None
    else:
        assert converted.position_from_a == pytest.approx(
            native.position_from_a * ar.BOHR_TO_ANGSTROM,
            rel=2.0e-15,
        )


@pytest.mark.parametrize(("atom_a", "atom_b"), [("H", "O"), ("O", "H")])
@pytest.mark.parametrize("distance_unit", ["bohr", "angstrom"])
def test_minimum_rejects_near_contact_cutoff_endpoint(
    atom_a: str,
    atom_b: str,
    distance_unit: str,
) -> None:
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile("H")
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile("O")
    ).cutoff_radius_bohr
    contact = cutoff_a + cutoff_b
    distance_bohr = math.nextafter(math.nextafter(contact, 0.0), 0.0)
    distance = (
        distance_bohr
        if distance_unit == "bohr"
        else distance_bohr * ar.BOHR_TO_ANGSTROM
    )

    result = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a,
            atom_b,
            distance,
            distance_unit=distance_unit,
        )
    )

    assert result.cutoff_regime == "overlap"
    assert result.method == "none"
    assert result.status == "no_resolved_interior_minimum"
    assert result.position_from_a is None
    assert result.position_from_b is None
    assert result.alternative_position_from_a is None
    assert result.alternative_position_from_b is None


def test_minimum_contact_neighbors_and_representable_interiors() -> None:
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile("H")
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile("He")
    ).cutoff_radius_bohr
    contact = cutoff_a + cutoff_b
    distances = [contact]
    distance = contact
    for _ in range(5):
        distance = math.nextafter(distance, 0.0)
        distances.append(distance)

    interior_counts: list[int] = []
    for distance in (distances[0], *distances[2:]):
        overlap_left = max(0.0, distance - cutoff_b)
        overlap_right = min(distance, cutoff_a)
        position = math.nextafter(overlap_left, overlap_right)
        count = 0
        while position < overlap_right:
            count += 1
            position = math.nextafter(position, overlap_right)
        interior_counts.append(count)

        result = _result(
            ar.estimate_promolecular_density_minimum(
                "H", "He", distance, distance_unit="bohr"
            )
        )
        _assert_minimum_coordinates_strictly_inside_overlap(result)

    assert interior_counts == [0, 1, 2, 3, 4]
    formerly_clamped = _result(
        ar.estimate_promolecular_density_minimum(
            "H", "He", distances[4], distance_unit="bohr"
        )
    )
    assert formerly_clamped.method == "none"
    assert formerly_clamped.status == "no_resolved_interior_minimum"

    exact = _result(
        ar.estimate_promolecular_density_minimum(
            "H", "He", contact, distance_unit="bohr"
        )
    )
    above = _result(
        ar.estimate_promolecular_density_minimum(
            "H",
            "He",
            math.nextafter(contact, math.inf),
            distance_unit="bohr",
        )
    )
    assert exact.method == above.method == "none"
    assert exact.status == above.status == "low_density_gap"
    assert exact.cutoff_regime == "contact"
    assert above.cutoff_regime == "gap"


@pytest.mark.parametrize(
    ("atom_a", "atom_b", "steps_below_contact"),
    [("H", "Se", 2), ("Kr", "He", 4)],
)
@pytest.mark.parametrize("distance_unit", ["bohr", "angstrom"])
def test_near_contact_minimum_survives_no_public_endpoint_rounding(
    atom_a: str,
    atom_b: str,
    steps_below_contact: int,
    distance_unit: str,
) -> None:
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile(atom_a)
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile(atom_b)
    ).cutoff_radius_bohr
    distance_bohr = cutoff_a + cutoff_b
    for _ in range(steps_below_contact):
        distance_bohr = math.nextafter(distance_bohr, 0.0)
    distance = (
        distance_bohr
        if distance_unit == "bohr"
        else distance_bohr * ar.BOHR_TO_ANGSTROM
    )

    for requested_a, requested_b in ((atom_a, atom_b), (atom_b, atom_a)):
        result = _result(
            ar.estimate_promolecular_density_minimum(
                requested_a,
                requested_b,
                distance,
                distance_unit=distance_unit,
            )
        )
        assert result.method == "none"
        assert result.status == "no_resolved_interior_minimum"
        assert result.position_from_a is None
        assert result.position_from_b is None
        assert result.alternative_position_from_a is None
        assert result.alternative_position_from_b is None


def test_raw_angstrom_near_contact_cannot_expose_a_cutoff_endpoint() -> None:
    atom_a = "H"
    atom_b = "Fe"
    cutoff_a = proatoms._prepared_pairwise_profile(
        _profile(atom_a)
    ).cutoff_radius_bohr
    cutoff_b = proatoms._prepared_pairwise_profile(
        _profile(atom_b)
    ).cutoff_radius_bohr
    distance = (cutoff_a + cutoff_b) * ar.BOHR_TO_ANGSTROM
    distance = math.nextafter(math.nextafter(distance, 0.0), 0.0)

    for requested_a, requested_b in ((atom_a, atom_b), (atom_b, atom_a)):
        result = _result(
            ar.estimate_promolecular_density_minimum(
                requested_a,
                requested_b,
                distance,
                distance_unit="angstrom",
            )
        )
        assert result.method == "none"
        assert result.status == "no_resolved_interior_minimum"
        assert result.position_from_a is None
        assert result.position_from_b is None
        assert result.alternative_position_from_a is None
        assert result.alternative_position_from_b is None


def test_boundary_reports_one_atom_domination_orientation_safely() -> None:
    forward = _result(
        ar.estimate_proatomic_boundary("H", "Lr", 0.1, distance_unit="bohr")
    )
    reverse = _result(
        ar.estimate_proatomic_boundary("Lr", "H", 0.1, distance_unit="bohr")
    )
    assert forward.method == reverse.method == "none"
    assert forward.status == reverse.status == "one_atom_dominates"
    assert forward.position_from_a is reverse.position_from_a is None
    assert forward.dominant_atom == reverse.dominant_atom == "Lr"
    assert forward.dominant_atom_role == "atom_b"
    assert reverse.dominant_atom_role == "atom_a"
    _assert_reversal(forward, reverse, 0.1)


def test_ordinary_minimum_is_resolved_inside_significant_overlap() -> None:
    distance = 7.0
    result = _result(
        ar.estimate_promolecular_density_minimum(
            "H", "O", distance, distance_unit="bohr"
        )
    )
    left = max(0.0, distance - result.cutoff_radius_b)
    right = min(distance, result.cutoff_radius_a)
    assert result.method == "promolecular_density_minimum"
    assert result.status == "ok"
    assert result.position_from_a is not None
    assert left < result.position_from_a < right
    assert result.position_from_a not in {left, right, 0.0, distance}
    assert result.search_resolution == ar.IAS_MINIMUM_RESOLUTION_BOHR
    assert result.search_converged is True
    assert result.search_passes == 2


def test_production_coalescing_uses_position_connected_components() -> None:
    candidates = tuple(
        proatoms._MinimumCandidate(position, density)
        for position, density in (
            (0.100, 1.0),
            (0.109, 1.0001),
            (0.118, 1.00005),
        )
    )

    resolved = proatoms._coalesce_minimum_candidates(candidates)

    assert resolved == (proatoms._MinimumCandidate(0.100, 1.0),)


def test_packaged_y_np_bridge_candidates_form_one_resolved_valley() -> None:
    distance = 10.212596531891476
    profile_a = proatoms._prepared_pairwise_profile(_profile("Y"))
    profile_b = proatoms._prepared_pairwise_profile(_profile("Np"))
    overlap_left = max(
        0.0,
        distance - profile_b.cutoff_radius_bohr,
    )
    overlap_right = min(distance, profile_a.cutoff_radius_bohr)
    equal_position, _ = proatoms._equal_contribution_position(
        profile_a,
        profile_b,
        distance,
    )
    fallback = proatoms._minimum_grid_pass(
        profile_a,
        profile_b,
        distance,
        overlap_left,
        overlap_right,
        0.005,
        equal_position,
    )
    result = _result(
        ar.estimate_promolecular_density_minimum(
            "Y",
            "Np",
            distance,
            distance_unit="bohr",
        )
    )
    reverse = _result(
        ar.estimate_promolecular_density_minimum(
            "Np",
            "Y",
            distance,
            distance_unit="bohr",
        )
    )

    assert tuple(
        candidate.position_bohr for candidate in fallback.candidates
    ) == pytest.approx((5.037953988322846, 5.030526030430109))
    assert result.method == "promolecular_density_minimum"
    assert result.status == "ok"
    assert result.position_from_a == pytest.approx(
        5.0379539928790065,
        abs=1.0e-10,
    )
    assert result.alternative_position_from_a is None
    assert result.alternative_position_from_b is None
    assert result.alternative_rho_sum is None
    assert result.relative_depth_gap is None
    assert result.ambiguous is False
    assert result.search_passes == 3
    assert result.search_converged is True
    assert reverse.status == "ok"
    assert reverse.alternative_position_from_a is None
    _assert_reversal(result, reverse, distance)


@pytest.mark.parametrize(
    ("atom_b", "distance_bohr", "midpoint_bohr", "density"),
    [
        (
            "Mg",
            10.427738551450130,
            4.128012047240235,
            0.00020000000000000052,
        ),
        (
            "K",
            11.554061800270143,
            4.128012047240236,
            0.00020000000000000036,
        ),
    ],
)
@pytest.mark.parametrize("distance_unit", ["bohr", "angstrom"])
def test_adjacent_grid_coordinates_preserve_near_contact_midpoint_valley(
    atom_b: str,
    distance_bohr: float,
    midpoint_bohr: float,
    density: float,
    distance_unit: str,
) -> None:
    distance_factor = (
        1.0 if distance_unit == "bohr" else ar.BOHR_TO_ANGSTROM
    )
    distance = distance_bohr * distance_factor
    forward = _result(
        ar.estimate_promolecular_density_minimum(
            "H",
            atom_b,
            distance,
            distance_unit=distance_unit,
        )
    )
    reverse = _result(
        ar.estimate_promolecular_density_minimum(
            atom_b,
            "H",
            distance,
            distance_unit=distance_unit,
        )
    )

    for result in (forward, reverse):
        assert result.method == "promolecular_density_minimum"
        assert result.status == "ok"
        assert result.rho_sum == pytest.approx(density, rel=2.0e-15)
        assert result.alternative_position_from_a is None
        _assert_minimum_coordinates_strictly_inside_overlap(result)
    assert forward.position_from_a == midpoint_bohr * distance_factor
    assert reverse.position_from_a == distance - forward.position_from_a
    _assert_reversal(forward, reverse, distance)

    converted = _result(
        ar.estimate_promolecular_density_minimum(
            "H",
            atom_b,
            distance,
            distance_unit=distance_unit,
            density_unit="electron/angstrom^3",
        )
    )
    assert converted.method == forward.method
    assert converted.status == forward.status
    assert converted.position_from_a == forward.position_from_a
    assert converted.rho_sum == pytest.approx(
        density / ar.BOHR_TO_ANGSTROM**3,
        rel=2.0e-15,
    )


def test_required_grid_passes_retain_coarse_only_competitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlap_left = 0.0
    overlap_right = 1.07
    narrow_center = overlap_right * 26.0 / 54.0
    half_width = 0.002

    def synthetic_objective(
        _profile_a: object,
        _profile_b: object,
        _distance_bohr: float,
        position_bohr: float,
    ) -> float:
        broad = 1.0 + (position_bohr - 0.2) ** 2
        offset = abs(position_bohr - narrow_center)
        if offset >= half_width:
            return broad
        shape = (1.0 - (offset / half_width) ** 2) ** 2
        depth = 1.0 + (narrow_center - 0.2) ** 2 - 1.00005
        return broad - depth * shape

    monkeypatch.setattr(proatoms, "_objective", synthetic_objective)
    coarse = proatoms._minimum_grid_pass(
        None,
        None,
        overlap_right,
        overlap_left,
        overlap_right,
        0.02,
        None,
    )
    fine = proatoms._minimum_grid_pass(
        None,
        None,
        overlap_right,
        overlap_left,
        overlap_right,
        0.01,
        None,
    )

    assert len(coarse.candidates) == 2
    assert len(fine.candidates) == 1
    assert proatoms._selections_compatible(coarse.selected, fine.selected)
    combined = proatoms._combine_confirmed_minimum_candidates(coarse, fine)
    assert len(combined) == 2
    assert combined[1].position_bohr == narrow_center

    fallback = proatoms._MinimumPass(0.005, fine.candidates)
    combined_with_fallback = proatoms._combine_confirmed_minimum_candidates(
        coarse,
        fine,
        fallback,
    )
    assert len(combined_with_fallback) == 2

    pass_by_spacing = {
        0.02: coarse,
        0.01: fine,
    }

    def controlled_pass(
        _profile_a: object,
        _profile_b: object,
        _distance_bohr: float,
        _overlap_left: float,
        _overlap_right: float,
        max_spacing_bohr: float,
        _equal_position_bohr: float | None,
    ) -> proatoms._MinimumPass:
        return pass_by_spacing[max_spacing_bohr]

    monkeypatch.setattr(proatoms, "_minimum_grid_pass", controlled_pass)
    profile_a = proatoms._prepared_pairwise_profile(_profile("H"))
    profile_b = proatoms._prepared_pairwise_profile(_profile("O"))
    native = proatoms._native_minimum_estimate(
        profile_a,
        profile_b,
        overlap_right,
    )
    assert native.status == "ambiguous_competing_minima"
    assert native.ambiguous is True
    assert native.alternative_position_bohr == narrow_center
    assert native.relative_depth_gap == pytest.approx(5.0e-5)


def test_fallback_reconciles_candidates_from_every_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coarse_only = proatoms._MinimumCandidate(0.5151851851851852, 1.00005)
    fine_primary = proatoms._MinimumCandidate(0.8, 1.0)
    coarse = proatoms._MinimumPass(0.02, (coarse_only,))
    fine = proatoms._MinimumPass(0.01, (fine_primary,))
    fallback = proatoms._MinimumPass(0.005, (fine_primary,))
    pass_by_spacing = {
        0.02: coarse,
        0.01: fine,
        0.005: fallback,
    }

    def controlled_pass(
        _profile_a: object,
        _profile_b: object,
        _distance_bohr: float,
        _overlap_left: float,
        _overlap_right: float,
        max_spacing_bohr: float,
        _equal_position_bohr: float | None,
    ) -> proatoms._MinimumPass:
        return pass_by_spacing[max_spacing_bohr]

    def synthetic_objective(
        _profile_a: object,
        _profile_b: object,
        _distance_bohr: float,
        position_bohr: float,
    ) -> float:
        return 1.0 + (position_bohr - 0.8) ** 2

    def synthetic_components(
        _profile_a: object,
        _profile_b: object,
        _distance_bohr: float,
        position_bohr: float,
    ) -> tuple[float, float, float]:
        density = synthetic_objective(None, None, 1.07, position_bohr)
        return density / 2.0, density / 2.0, density

    monkeypatch.setattr(proatoms, "_minimum_grid_pass", controlled_pass)
    monkeypatch.setattr(proatoms, "_objective", synthetic_objective)
    monkeypatch.setattr(proatoms, "_component_values", synthetic_components)
    monkeypatch.setattr(
        proatoms,
        "_equal_contribution_position",
        lambda *_args: (None, None),
    )

    profile_a = proatoms._prepared_pairwise_profile(_profile("H"))
    profile_b = proatoms._prepared_pairwise_profile(_profile("O"))
    native = proatoms._native_minimum_estimate(profile_a, profile_b, 1.07)

    assert native.status == "ambiguous_competing_minima"
    assert native.position_bohr == fine_primary.position_bohr
    assert native.alternative_position_bohr == coarse_only.position_bohr
    assert native.relative_depth_gap == pytest.approx(5.0e-5)
    assert native.search_passes == 3
    assert native.search_converged is True


def test_minimum_empty_overlap_returns_typed_gap_without_coordinate() -> None:
    result = _result(
        ar.estimate_promolecular_density_minimum(
            "H", "O", 10.0, distance_unit="bohr"
        )
    )
    assert result.requested_mode == "minimum"
    assert result.method == "none"
    assert result.status == "low_density_gap"
    assert result.cutoff_regime == "gap"
    assert result.position_from_a is None
    assert result.rho_sum is None
    assert result.search_passes == 0


def test_no_resolved_minimum_does_not_fall_back_to_boundary_mode() -> None:
    atom_a, atom_b, distance = _NO_RESOLVED_CASE
    minimum = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    boundary = _result(
        ar.estimate_proatomic_boundary(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    assert minimum.requested_mode == "minimum"
    assert minimum.method == "none"
    assert minimum.status == "no_resolved_interior_minimum"
    assert minimum.position_from_a is None
    assert minimum.rho_sum is None
    assert boundary.requested_mode == "boundary"
    assert boundary.status != minimum.status


def test_boundary_dominated_minimum_retains_interior_diagnostic() -> None:
    atom_a, atom_b, distance = _BOUNDARY_DOMINATED_CASE
    result = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    assert result.requested_mode == "minimum"
    assert result.method == "promolecular_density_minimum"
    assert result.status == "boundary_dominated"
    assert result.position_from_a is not None
    assert 0.0 < result.position_from_a < distance
    assert result.rho_sum is not None
    assert result.search_passes == 3
    _assert_minimum_coordinates_strictly_inside_overlap(result)

    profile_a = _profile(atom_a)
    profile_b = _profile(atom_b)
    boundary_density = min(
        _pair_density_sum(profile_a, profile_b, distance, 0.0),
        _pair_density_sum(profile_a, profile_b, distance, distance),
    )
    assert boundary_density < result.rho_sum


def test_competing_minima_are_limited_to_one_alternative() -> None:
    atom_a, atom_b, distance = _AMBIGUOUS_CASE
    result = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    assert result.method == "promolecular_density_minimum"
    assert result.status == "ambiguous_competing_minima"
    assert result.ambiguous is True
    assert result.alternative_position_from_a is not None
    assert result.alternative_position_from_b is not None
    assert result.alternative_rho_sum is not None
    assert result.relative_depth_gap is not None
    assert result.relative_depth_gap <= 1.0e-4
    assert abs(
        result.alternative_position_from_a - result.position_from_a
    ) >= ar.IAS_MINIMUM_RESOLUTION_BOHR
    assert result.alternative_position_from_a + (
        result.alternative_position_from_b
    ) == pytest.approx(distance)
    assert result.search_passes == 3
    assert result.search_resolution == 0.005
    assert result.search_converged is True
    _assert_minimum_coordinates_strictly_inside_overlap(result)


def test_unstable_search_returns_finest_supported_candidate() -> None:
    atom_a, atom_b, distance = _UNSTABLE_CASE
    result = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    assert result.method == "promolecular_density_minimum"
    assert result.status == "search_unstable"
    assert result.position_from_a is not None
    assert result.search_passes == 3
    assert result.search_resolution == 0.005
    assert result.search_converged is False
    _assert_minimum_coordinates_strictly_inside_overlap(result)


@pytest.mark.parametrize("case", [_AMBIGUOUS_CASE, _UNSTABLE_CASE])
def test_minimum_primary_and_alternative_coordinates_reverse(
    case: tuple[str, str, float],
) -> None:
    atom_a, atom_b, distance = case
    forward = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a, atom_b, distance, distance_unit="bohr"
        )
    )
    reverse = _result(
        ar.estimate_promolecular_density_minimum(
            atom_b, atom_a, distance, distance_unit="bohr"
        )
    )
    assert forward.alternative_position_from_a is not None
    _assert_minimum_coordinates_strictly_inside_overlap(forward)
    _assert_minimum_coordinates_strictly_inside_overlap(reverse)
    _assert_reversal(forward, reverse, distance)


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_ordinary_pair_reversal_swaps_components_and_coordinates(mode: str) -> None:
    distance = 3.0
    forward = _result(
        ar.estimate_ias_position(
            "C", "O", distance, mode=mode, distance_unit="bohr"
        )
    )
    reverse = _result(
        ar.estimate_ias_position(
            "O", "C", distance, mode=mode, distance_unit="bohr"
        )
    )
    _assert_reversal(forward, reverse, distance)


@pytest.mark.parametrize(
    ("mode", "atom_a", "atom_b", "distance_bohr"),
    [
        ("boundary", "C", "O", 3.0),
        ("minimum", *_AMBIGUOUS_CASE),
    ],
)
def test_distance_units_preserve_physical_geometry(
    mode: str,
    atom_a: str,
    atom_b: str,
    distance_bohr: float,
) -> None:
    distance_angstrom = distance_bohr * ar.BOHR_TO_ANGSTROM
    native = _result(
        ar.estimate_ias_position(
            atom_a,
            atom_b,
            distance_bohr,
            mode=mode,
            distance_unit="bohr",
        )
    )
    converted = _result(
        ar.estimate_ias_position(
            atom_a,
            atom_b,
            distance_angstrom,
            mode=mode,
            distance_unit="angstrom",
        )
    )
    assert converted.distance == distance_angstrom
    assert converted.method == native.method
    assert converted.status == native.status
    assert converted.cutoff_regime == native.cutoff_regime
    assert converted.position_from_a == pytest.approx(
        native.position_from_a * ar.BOHR_TO_ANGSTROM,
        rel=2.0e-15,
    )
    assert converted.position_from_b == pytest.approx(
        native.position_from_b * ar.BOHR_TO_ANGSTROM,
        rel=2.0e-15,
    )
    assert converted.cutoff_radius_a == pytest.approx(
        native.cutoff_radius_a * ar.BOHR_TO_ANGSTROM,
        rel=2.0e-15,
    )
    assert converted.cutoff_radius_b == pytest.approx(
        native.cutoff_radius_b * ar.BOHR_TO_ANGSTROM,
        rel=2.0e-15,
    )
    assert converted.contour_separation == pytest.approx(
        native.contour_separation * ar.BOHR_TO_ANGSTROM,
        rel=2.0e-15,
    )
    assert converted.alternative_position_from_a == (
        None
        if native.alternative_position_from_a is None
        else pytest.approx(
            native.alternative_position_from_a * ar.BOHR_TO_ANGSTROM,
            rel=2.0e-15,
        )
    )
    assert converted.alternative_position_from_b == (
        None
        if native.alternative_position_from_b is None
        else pytest.approx(
            native.alternative_position_from_b * ar.BOHR_TO_ANGSTROM,
            rel=2.0e-15,
        )
    )
    assert converted.search_resolution == (
        None
        if native.search_resolution is None
        else pytest.approx(
            native.search_resolution * ar.BOHR_TO_ANGSTROM,
            rel=2.0e-15,
        )
    )
    assert converted.rho_sum == pytest.approx(native.rho_sum, rel=2.0e-15)


@pytest.mark.parametrize(
    ("mode", "atom_a", "atom_b", "distance"),
    [
        ("boundary", "C", "O", 3.0),
        ("minimum", *_AMBIGUOUS_CASE),
    ],
)
def test_density_unit_conversion_cannot_change_scientific_decisions(
    mode: str,
    atom_a: str,
    atom_b: str,
    distance: float,
) -> None:
    native = _result(
        ar.estimate_ias_position(
            atom_a,
            atom_b,
            distance,
            mode=mode,
            distance_unit="bohr",
        )
    )
    converted = _result(
        ar.estimate_ias_position(
            atom_a,
            atom_b,
            distance,
            mode=mode,
            distance_unit="bohr",
            density_unit="electron/angstrom^3",
        )
    )
    unchanged = (
        "requested_mode",
        "method",
        "status",
        "position_from_a",
        "position_from_b",
        "fraction_from_a",
        "cutoff_radius_a",
        "cutoff_radius_b",
        "contour_separation",
        "cutoff_regime",
        "alternative_position_from_a",
        "alternative_position_from_b",
        "relative_depth_gap",
        "ambiguous",
        "search_resolution",
        "search_converged",
        "search_passes",
    )
    for field_name in unchanged:
        assert getattr(converted, field_name) == getattr(native, field_name)

    factor = 1.0 / ar.BOHR_TO_ANGSTROM**3
    for field_name in (
        "rho_a",
        "rho_b",
        "rho_sum",
        "cutoff_density",
        "alternative_rho_sum",
    ):
        native_value = getattr(native, field_name)
        converted_value = getattr(converted, field_name)
        if native_value is None:
            assert converted_value is None
        else:
            assert converted_value == pytest.approx(
                native_value * factor,
                rel=2.0e-15,
            )


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_deuterium_and_tritium_use_the_hydrogen_profile(mode: str) -> None:
    hydrogen = ar.estimate_ias_position(
        "H", "O", 2.0, mode=mode, distance_unit="bohr"
    )
    assert ar.estimate_ias_position(
        "D", "O", 2.0, mode=mode, distance_unit="bohr"
    ) == hydrogen
    assert ar.estimate_ias_position(
        "T", "O", 2.0, mode=mode, distance_unit="bohr"
    ) == hydrogen


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
def test_missing_profiles_return_none(mode: str) -> None:
    assert (
        ar.estimate_ias_position(
            "Rf", "O", 2.0, mode=mode, distance_unit="bohr"
        )
        is None
    )
    assert (
        ar.estimate_ias_position(
            "not-an-element", "O", 2.0, mode=mode, distance_unit="bohr"
        )
        is None
    )


@pytest.mark.parametrize(
    "distance",
    [0.0, -1.0, math.nan, math.inf, -math.inf, 20.0001, True, None, "bad"],
)
def test_invalid_distances_raise_value_error(distance: object) -> None:
    with pytest.raises(ValueError, match="distance"):
        ar.estimate_ias_position("H", "O", distance, distance_unit="bohr")


def test_distance_endpoint_and_arbitrarily_short_positive_values_are_valid() -> None:
    endpoint = _result(
        ar.estimate_ias_position("H", "H", 20.0, distance_unit="bohr")
    )
    short = _result(
        ar.estimate_ias_position("H", "H", 1.0e-12, distance_unit="bohr")
    )
    assert endpoint.position_from_a == 10.0
    assert short.position_from_a == 0.5e-12


@pytest.mark.parametrize("mode", ["boundary", "minimum"])
@pytest.mark.parametrize("distance_unit", ["bohr", "angstrom"])
def test_smallest_subnormal_homonuclear_midpoint_rounding_is_explicit(
    mode: str,
    distance_unit: str,
) -> None:
    distance = math.ulp(0.0)
    result = _result(
        ar.estimate_ias_position(
            "H", "H", distance, mode=mode, distance_unit=distance_unit
        )
    )

    assert result.method == "homonuclear_midpoint"
    assert result.position_from_a == distance / 2.0 == 0.0
    assert result.position_from_b == distance - result.position_from_a
    assert result.fraction_from_a == result.position_from_a / distance == 0.0


@pytest.mark.parametrize(("atom_a", "atom_b"), [("H", "O"), ("O", "H")])
def test_extreme_unlike_distance_cannot_return_a_nucleus_as_minimum(
    atom_a: str,
    atom_b: str,
) -> None:
    result = _result(
        ar.estimate_promolecular_density_minimum(
            atom_a,
            atom_b,
            2.0e-323,
            distance_unit="bohr",
        )
    )

    assert result.method == "none"
    assert result.status == "no_resolved_interior_minimum"
    assert result.position_from_a is None
    assert result.position_from_b is None


def test_invalid_mode_and_units_raise_value_error() -> None:
    with pytest.raises(ValueError, match="mode"):
        ar.estimate_ias_position("H", "O", 2.0, mode="automatic")
    with pytest.raises(ValueError, match="distance unit"):
        ar.estimate_proatomic_boundary("H", "O", 2.0, distance_unit="meter")
    with pytest.raises(ValueError, match="density unit"):
        ar.estimate_promolecular_density_minimum(
            "H", "O", 2.0, density_unit="electron/cm^3"
        )


def test_missing_dataset_raises_dataset_error() -> None:
    with pytest.raises(DatasetError, match="unknown dataset id"):
        ar.estimate_proatomic_boundary("H", "O", 2.0, set_id="missing")
