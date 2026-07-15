from __future__ import annotations

import csv
import hashlib
from importlib import resources
import io
import math
import zipfile

import atomref as ar


_DATASET_ID = "pbe0_sfx2c_dyallv4z_h-lr_neutral_v2"
_ARCHIVE_NAME = "proatomic_density_neutral.zip"
_MEMBER_NAME = "proatomic_density_neutral.csv"
_EXPECTED_HEADER = ("r_bohr", *(f"z{z:03d}" for z in range(1, 104)))
_EXPECTED_ROWS = 1127
_MONOTONIC_REL_TOL = 1.0e-12
_EXPECTED_ARCHIVE_SHA256 = (
    "1ec0318c8bc8f6e71eb3125cf1d4387e4593d7bee8ff5ee5270fbcc32c70ec6b"
)
_EXPECTED_CSV_SHA256 = (
    "8478da862233c8874e36d65bb5eb762cdb9cbcb0e0278733c0f425ae00c2dcfe"
)


def _snapshot_csv_bytes() -> tuple[bytes, zipfile.ZipInfo, bytes]:
    archive_bytes = (
        resources.files("atomref.data").joinpath(_ARCHIVE_NAME).read_bytes()
    )
    with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
        assert archive.comment == b""
        members = archive.infolist()
        assert len(members) == 1
        member = members[0]
        csv_bytes = archive.read(member)
    return archive_bytes, member, csv_bytes


def test_neutral_snapshot_matches_pinned_scientific_fingerprints() -> None:
    archive_bytes, _, csv_bytes = _snapshot_csv_bytes()

    assert hashlib.sha256(archive_bytes).hexdigest() == _EXPECTED_ARCHIVE_SHA256
    assert hashlib.sha256(csv_bytes).hexdigest() == _EXPECTED_CSV_SHA256


def test_neutral_snapshot_has_exact_zip_and_csv_contract() -> None:
    _, member, csv_bytes = _snapshot_csv_bytes()

    assert member.filename == _MEMBER_NAME
    assert not member.is_dir()
    assert member.date_time == (1980, 1, 1, 0, 0, 0)
    assert member.compress_type == zipfile.ZIP_DEFLATED
    assert member.create_system == 3
    assert member.external_attr == 0o100644 << 16
    assert member.internal_attr == 0
    assert member.extra == b""
    assert member.comment == b""
    assert member.flag_bits & 0x1 == 0

    assert csv_bytes.endswith(b"\n")
    assert b"\r" not in csv_bytes
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"), newline="")))
    assert tuple(rows[0]) == _EXPECTED_HEADER
    assert len(rows) - 1 == _EXPECTED_ROWS
    assert all(len(row) == len(_EXPECTED_HEADER) for row in rows[1:])


def test_neutral_snapshot_values_satisfy_the_retained_domain_contract() -> None:
    _, _, csv_bytes = _snapshot_csv_bytes()
    rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"), newline="")))
    data_rows = rows[1:]

    radii = tuple(float(row[0]) for row in data_rows)
    assert len(radii) == _EXPECTED_ROWS
    assert all(math.isfinite(radius) and radius > 0.0 for radius in radii)
    assert all(right > left for left, right in zip(radii, radii[1:]))
    assert radii[-2] == 19.865456344881434
    assert radii[-2] < 20.0 < radii[-1]
    assert radii[-1] == 20.1644204667093

    for column_index in range(1, 104):
        profile = tuple(float(row[column_index]) for row in data_rows)
        assert all(math.isfinite(value) and value > 0.0 for value in profile)
        assert all(
            current <= previous
            or math.isclose(
                current,
                previous,
                rel_tol=_MONOTONIC_REL_TOL,
                abs_tol=0.0,
            )
            for previous, current in zip(profile, profile[1:])
        )


def test_neutral_snapshot_uses_generic_registry_discovery_and_caching() -> None:
    ref = ar.DatasetRef("proatomic_density", _DATASET_ID)

    assert "proatomic_density" in ar.list_quantities()
    assert ar.list_dataset_ids("proatomic_density") == (_DATASET_ID,)
    assert tuple(
        info.ref.set_id for info in ar.list_dataset_infos("proatomic_density")
    ) == (_DATASET_ID,)

    info = ar.get_dataset_info(ref)
    alias_info = ar.get_dataset_info(
        ar.DatasetRef("proatomic_density", "atomref-proatoms neutral v2")
    )
    assert alias_info.ref == ref
    assert info.coverage is not None
    assert info.coverage.n_values == 103
    assert info.coverage.z_min == 1
    assert info.coverage.z_max == 103
    assert info.coverage.has_placeholders is False

    dataset = ar.get_builtin_set(ref)
    via_alias = ar.get_builtin_set(
        ar.DatasetRef("proatomic_density", "atomref-proatoms neutral v2")
    )
    assert isinstance(dataset, ar.ElementRadialSet)
    assert via_alias is dataset
    assert dataset.info is info or dataset.info == info
    assert len(dataset.radii) == _EXPECTED_ROWS
    assert all(dataset.profiles_by_z[z] is not None for z in range(1, 104))
    assert all(dataset.profiles_by_z[z] is None for z in range(104, 119))
    assert all(
        len(dataset.profiles_by_z[z] or ()) == _EXPECTED_ROWS
        for z in range(1, 104)
    )


def test_neutral_snapshot_registry_records_pinned_source_and_license() -> None:
    info = ar.get_dataset_info(
        ar.DatasetRef("proatomic_density", _DATASET_ID)
    )
    assert info.storage is not None
    storage = info.storage

    expected = {
        "kind": "element_radial_csv_zip",
        "filename": _ARCHIVE_NAME,
        "member": _MEMBER_NAME,
        "radius_column": "r_bohr",
        "density_column_pattern": "z{z:03d}",
        "native_coordinate_unit": "bohr",
        "native_density_unit": "electron/bohr^3",
        "public_max_radius_bohr": 20.0,
        "retained_bracketing_radius_bohr": 20.1644204667093,
        "retained_rows": _EXPECTED_ROWS,
        "interpolation_contract": "loglog_positive_bracketed_v1",
        "monotonicity_relative_tolerance": _MONOTONIC_REL_TOL,
        "charge_scope": "neutral atoms only",
        "source_project": "atomref-proatoms",
        "source_release": "2.0.0",
        "source_dataset_id": "pbe0_sfx2c_dyallv4z_h-lr_spherical_v2",
        "source_profiles_sha256": (
            "b5520ab009542d52098dd6dbb920966d8d13377a4a5004f584a7bd15cd41c299"
        ),
        "source_metadata_sha256": (
            "32c833ca69fa0f7eb9ed32841aafc638123ff872861e636156610e417fc4c514"
        ),
        "basis_id": "dyall-v4z",
        "basis_sha256": (
            "0ee543855f8b1e7fbe9868d4abb844d8e8cc8b8c2694067b2b40de014bb4be94"
        ),
        "profile_data_version": "2.0.0",
        "electronic_method": "PBE0",
        "scf_model": "self-consistent spherical fractional-occupation UKS",
        "relativity": "spin-free one-electron X2C",
        "data_license": "CC BY 4.0",
        "data_license_url": "https://creativecommons.org/licenses/by/4.0/",
        "concept_doi": "10.5281/zenodo.21291021",
        "version_doi": "10.5281/zenodo.21291022",
    }
    assert {key: storage[key] for key in expected} == expected
    assert {reference.doi for reference in info.references} == {
        "10.5281/zenodo.21291021",
        "10.5281/zenodo.21291022",
    }
    assert "CC BY 4.0" in " ".join(info.notes)
