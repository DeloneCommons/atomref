from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from types import MappingProxyType

import pytest

import atomref as ar
from atomref.errors import DatasetError
import atomref.proatoms as proatoms
import atomref.registry as registry


_DATASET_ID = "pbe0_sfx2c_dyallv4z_h-lr_neutral_v2"


def _synthetic_power_law_profile() -> ar.ProatomicDensityProfile:
    ref = ar.DatasetRef("proatomic_density", "synthetic_power_law")
    info = ar.DatasetInfo(
        ref=ref,
        domain="element",
        units="electron/bohr^3",
        name="Synthetic power law",
        storage=MappingProxyType(
            {
                "native_coordinate_unit": "bohr",
                "native_density_unit": "electron/bohr^3",
                "public_max_radius_bohr": 8.0,
                "interpolation_contract": "loglog_positive_bracketed_v1",
            }
        ),
    )
    radii = (0.25, 1.0, 4.0, 8.0)
    coefficient = 7.25
    exponent = -2.75
    densities = tuple(coefficient * radius**exponent for radius in radii)
    dataset = ar.ElementRadialSet(
        ref=ref,
        info=info,
        radii=radii,
        profiles_by_z=(None, densities),
    )
    return ar.ProatomicDensityProfile(
        dataset=dataset,
        atomic_number=1,
    )


def test_density_set_discovery_aliases_and_generic_loader_identity() -> None:
    assert ar.list_proatomic_density_sets() == (_DATASET_ID,)
    assert tuple(
        info.ref.set_id for info in ar.list_proatomic_density_set_infos()
    ) == (_DATASET_ID,)

    info = ar.get_proatomic_density_set_info("atomref-proatoms neutral v2")
    dataset = ar.get_proatomic_density_set("atomref-proatoms neutral v2")
    generic = ar.get_builtin_set(ar.DatasetRef("proatomic_density", _DATASET_ID))
    assert info.ref.set_id == _DATASET_ID
    assert dataset is generic
    assert isinstance(dataset, ar.ProatomicDensitySet)


@pytest.mark.parametrize("symbol", ["H", "C", "O", "Fe", "La", "U", "Lr"])
def test_representative_h_through_lr_profiles_load(symbol: str) -> None:
    profile = ar.get_proatomic_density_profile(symbol)
    assert profile is not None
    assert profile.symbol == symbol
    assert profile.atomic_number == ar.get_element(symbol).z
    assert profile.dataset is ar.get_proatomic_density_set()
    assert profile.ref == profile.info.ref


def test_all_h_through_lr_profiles_are_available() -> None:
    for element in ar.iter_elements():
        if element.z > 103:
            break
        profile = ar.get_proatomic_density_profile(element.symbol)
        assert profile is not None, element.symbol
        assert profile.atomic_number == element.z


@pytest.mark.parametrize(
    ("atomic_number", "symbol"),
    [(1, "H"), (8, "O"), (103, "Lr")],
)
def test_integer_atomic_numbers_use_canonical_cached_profiles(
    atomic_number: int,
    symbol: str,
) -> None:
    profile = ar.get_proatomic_density_profile(atomic_number)
    assert profile is ar.get_proatomic_density_profile(symbol)
    assert profile is not None
    assert profile.atomic_number == atomic_number
    assert profile.symbol == symbol
    assert ar.get_proatomic_density(
        atomic_number,
        1.0,
        radius_unit="bohr",
    ) == ar.get_proatomic_density(symbol, 1.0, radius_unit="bohr")


@pytest.mark.parametrize("atomic_number", [104, 0, -1, True, False])
def test_invalid_or_unsupported_atomic_numbers_return_none(
    atomic_number: int,
) -> None:
    assert ar.get_proatomic_density_profile(atomic_number) is None
    assert ar.get_proatomic_density(atomic_number, 1.0) is None


def test_bool_does_not_poison_integer_atomic_number_resolution_cache() -> None:
    proatoms._get_element_by_atomic_number_cached.cache_clear()
    assert ar.get_proatomic_density_profile(True) is None
    assert ar.get_proatomic_density_profile(1) is ar.get_proatomic_density_profile(
        "H"
    )


def test_isotopes_invalid_symbols_and_unsupported_elements() -> None:
    hydrogen = ar.get_proatomic_density_profile("H")
    assert ar.get_proatomic_density_profile("D") is hydrogen
    assert ar.get_proatomic_density_profile("T") is hydrogen
    assert ar.get_proatomic_density("D", 0.5) == ar.get_proatomic_density("H", 0.5)
    assert ar.get_proatomic_density("T", 0.5) == ar.get_proatomic_density("H", 0.5)
    for symbol in ("Rf", "Og", "not-an-element", "", None):
        assert ar.get_proatomic_density_profile(symbol) is None
        assert ar.get_proatomic_density(symbol, 0.5) is None


def test_set_and_profile_cache_reuse_and_public_immutability() -> None:
    profile = ar.get_proatomic_density_profile("O")
    assert profile is not None
    assert ar.get_proatomic_density_profile("o") is profile
    assert ar.get_proatomic_density_profile("O") is profile
    assert isinstance(profile.radii, tuple)
    assert isinstance(profile.densities, tuple)
    with pytest.raises(FrozenInstanceError):
        profile.symbol = "N"
    with pytest.raises(TypeError):
        profile.densities[0] = 0.0
    with pytest.raises(FrozenInstanceError):
        profile.dataset.radii = ()


def test_profile_identity_is_derived_and_repr_is_concise() -> None:
    dataset = ar.get_proatomic_density_set()
    profile = ar.ProatomicDensityProfile(dataset=dataset, atomic_number=1)
    assert profile.symbol == "H"
    assert profile.atomic_number == 1
    assert repr(profile) == (
        "ProatomicDensityProfile(atomic_number=1, symbol='H')"
    )
    assert len(repr(profile)) < 100
    with pytest.raises(TypeError, match="unexpected keyword argument 'symbol'"):
        ar.ProatomicDensityProfile(
            dataset=dataset,
            atomic_number=1,
            symbol="O",
        )


def test_profile_rejects_dataset_metadata_reference_mismatch() -> None:
    valid = _synthetic_power_law_profile()
    mismatched_info = ar.DatasetInfo(
        ref=ar.DatasetRef("proatomic_density", "different"),
        domain=valid.info.domain,
        units=valid.info.units,
        name=valid.info.name,
        storage=valid.info.storage,
    )
    mismatched = ar.ElementRadialSet(
        ref=valid.ref,
        info=mismatched_info,
        radii=valid.radii,
        profiles_by_z=valid.dataset.profiles_by_z,
    )
    with pytest.raises(DatasetError, match="reference does not match"):
        ar.ProatomicDensityProfile(dataset=mismatched, atomic_number=1)


def test_packaged_density_loading_is_lazy_and_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_reader = registry._read_package_data_bytes
    calls = 0

    def counting_reader(filename: str) -> bytes:
        nonlocal calls
        calls += 1
        return real_reader(filename)

    registry._load_builtin_set.cache_clear()
    registry._load_radial_csv_zip.cache_clear()
    proatoms._get_profile_cached.cache_clear()
    monkeypatch.setattr(registry, "_read_package_data_bytes", counting_reader)
    try:
        ar.get_proatomic_density_set_info()
        assert calls == 0
        first = ar.get_proatomic_density_profile("O")
        assert first is not None
        assert calls == 1
        assert ar.get_proatomic_density_profile("O") is first
        assert ar.get_proatomic_density("O", 0.75) is not None
        assert calls == 1
    finally:
        registry._load_builtin_set.cache_clear()
        registry._load_radial_csv_zip.cache_clear()
        proatoms._get_profile_cached.cache_clear()


def test_origin_first_grid_point_and_exact_stored_knots() -> None:
    profile = ar.get_proatomic_density_profile("O")
    assert profile is not None
    assert profile(0.0, radius_unit="bohr") == 358.401594629436
    assert profile(profile.radii[0] / 2.0, radius_unit="bohr") == (
        358.401594629436
    )
    assert profile(profile.radii[0], radius_unit="bohr") == 358.401594629436
    expected_knots = {
        100: (4.453688832606716e-06, 358.4005490198518),
        500: (0.0017522632545894682, 326.9578641098411),
        1000: (3.0704265133844744, 0.0015857375047883448),
        1125: (19.865456344881434, 1.1086022497194577e-36),
    }
    for index, (radius, density) in expected_knots.items():
        assert profile.radii[index] == radius
        assert profile.densities[index] == density
        assert profile(radius, radius_unit="bohr") == density


def test_exact_public_endpoint_and_out_of_range_radii() -> None:
    profile = ar.get_proatomic_density_profile("O")
    assert profile is not None
    endpoint = profile(20.0, radius_unit="bohr")
    endpoint_angstrom = profile(20.0 * ar.BOHR_TO_ANGSTROM)
    assert math.isfinite(endpoint) and endpoint > 0.0
    assert endpoint_angstrom == pytest.approx(endpoint, rel=2.0e-15)
    with pytest.raises(ValueError, match="exceeds the public limit"):
        profile(math.nextafter(20.0, math.inf), radius_unit="bohr")
    with pytest.raises(ValueError, match="exceeds the public limit"):
        profile(20.01, radius_unit="bohr")
    with pytest.raises(ValueError, match="exceeds the public limit"):
        profile(math.nextafter(20.0 * ar.BOHR_TO_ANGSTROM, math.inf))


@pytest.mark.parametrize("radius", [-1.0, math.nan, math.inf, -math.inf])
def test_negative_and_non_finite_radii_raise(radius: float) -> None:
    with pytest.raises(ValueError, match="radius"):
        ar.get_proatomic_density("O", radius, radius_unit="bohr")


def test_unknown_units_raise() -> None:
    with pytest.raises(ValueError, match="unknown radius unit"):
        ar.get_proatomic_density("O", 1.0, radius_unit="meter")
    with pytest.raises(ValueError, match="unknown density unit"):
        ar.get_proatomic_density("O", 1.0, density_unit="kg/m^3")


def test_synthetic_power_law_is_exact_under_loglog_interpolation() -> None:
    profile = _synthetic_power_law_profile()
    coefficient = 7.25
    exponent = -2.75
    for radius in (0.5, 2.0, 6.0):
        expected = coefficient * radius**exponent
        assert profile(radius, radius_unit="bohr") == pytest.approx(
            expected,
            rel=2.0e-15,
        )


def test_interpolation_is_loglog_positive_and_continuous_at_knots() -> None:
    profile = _synthetic_power_law_profile()
    left_density = profile.densities[1]
    right_density = profile.densities[2]
    midpoint = math.sqrt(profile.radii[1] * profile.radii[2])
    expected_loglog = math.sqrt(left_density * right_density)
    linear_midpoint = (left_density + right_density) / 2.0
    interpolated = profile(midpoint, radius_unit="bohr")
    assert interpolated == pytest.approx(expected_loglog, rel=2.0e-15)
    assert not math.isclose(interpolated, linear_midpoint, rel_tol=1.0e-3)
    assert interpolated > 0.0

    for knot in profile.radii[1:-1]:
        exact = profile(knot, radius_unit="bohr")
        left = profile(math.nextafter(knot, 0.0), radius_unit="bohr")
        right = profile(math.nextafter(knot, math.inf), radius_unit="bohr")
        assert left == pytest.approx(exact, rel=2.0e-14)
        assert right == pytest.approx(exact, rel=2.0e-14)


def test_nonpositive_density_data_are_rejected_without_zero_fill() -> None:
    valid = _synthetic_power_law_profile()
    invalid_dataset = ar.ElementRadialSet(
        ref=valid.ref,
        info=valid.info,
        radii=valid.radii,
        profiles_by_z=(None, (valid.densities[0], 0.0, *valid.densities[2:])),
    )
    with pytest.raises(DatasetError, match="finite and positive"):
        ar.ProatomicDensityProfile(
            dataset=invalid_dataset,
            atomic_number=1,
        )


@pytest.mark.parametrize("symbol", ["H", "O", "Fe", "U", "Lr"])
def test_packaged_profiles_are_positive_and_non_increasing(symbol: str) -> None:
    profile = ar.get_proatomic_density_profile(symbol)
    assert profile is not None
    assert all(value > 0.0 for value in profile.densities)
    assert all(
        current <= previous
        or math.isclose(current, previous, rel_tol=1.0e-12, abs_tol=0.0)
        for previous, current in zip(profile.densities, profile.densities[1:])
    )


def test_radius_and_density_units_are_independent() -> None:
    profile = ar.get_proatomic_density_profile("O")
    assert profile is not None
    radius_bohr = 1.75
    assert ar.BOHR_TO_ANGSTROM == 0.529177210903
    radius_angstrom = radius_bohr * 0.529177210903
    native = profile(radius_bohr, radius_unit="bohr")
    equivalent = profile(radius_angstrom, radius_unit="angstrom")
    converted = profile(
        radius_bohr,
        radius_unit="bohr",
        density_unit="electron/angstrom^3",
    )
    assert equivalent == pytest.approx(native, rel=2.0e-15)
    assert converted == pytest.approx(
        native / 0.529177210903**3,
        rel=2.0e-15,
    )
    assert profile.ref == ar.get_proatomic_density_profile("O").ref
    assert profile.interpolation_contract == "loglog_positive_bracketed_v1"


def test_documented_units_are_function_defaults() -> None:
    profile = ar.get_proatomic_density_profile("O")
    assert profile is not None
    radius_angstrom = 0.75
    assert profile(radius_angstrom) == profile(
        radius_angstrom,
        radius_unit="angstrom",
        density_unit="electron/bohr^3",
    )
    assert ar.get_proatomic_density("O", radius_angstrom) == profile(radius_angstrom)


def test_missing_density_dataset_raises_dataset_error() -> None:
    with pytest.raises(DatasetError, match="unknown dataset id"):
        ar.get_proatomic_density_profile("O", set_id="missing")


def test_scalar_accessors_remain_narrow_after_density_use() -> None:
    assert isinstance(
        ar.get_radii_set("covalent", "cordero2008"),
        ar.ElementScalarSet,
    )
    assert isinstance(ar.get_xh_set("csd_legacy_xh_cno"), ar.ElementScalarSet)
    with pytest.raises(DatasetError, match="radial payload; scalar dataset required"):
        ar.ValuePolicy(base=ar.get_proatomic_density_set())
