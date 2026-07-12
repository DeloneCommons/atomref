from __future__ import annotations

from collections.abc import Callable
import importlib.util
import io
from pathlib import Path
import sys
import zipfile

import pytest

from atomref.elements import iter_elements


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools" / "build_proatomic_density_snapshot.py"

spec = importlib.util.spec_from_file_location("snapshot_builder_tool", MODULE_PATH)
assert spec is not None and spec.loader is not None
snapshot_builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = snapshot_builder
spec.loader.exec_module(snapshot_builder)


_Metadata = dict[str, dict[str, dict[str, object]]]
_EXPECTED_Z = tuple(range(1, 104))
_SYMBOL_BY_Z = {
    element.z: element.symbol
    for element in iter_elements()
    if element.z in _EXPECTED_Z
}


def _state_id(z: int) -> str:
    return f"neutral_z{z:03d}"


def _column_name(z: int) -> str:
    return f"rho_e_bohr3__{_state_id(z)}"


def _synthetic_metadata(
    *,
    state_order: tuple[int, ...] = _EXPECTED_Z,
    column_order: tuple[int, ...] = _EXPECTED_Z,
) -> _Metadata:
    states: dict[str, dict[str, object]] = {}
    columns: dict[str, dict[str, object]] = {}
    for z in state_order:
        states[_state_id(z)] = {
            "symbol": _SYMBOL_BY_Z[z],
            "z": z,
            "charge": 0,
            "electron_count": z,
            "multiplicity": 1,
        }
    for z in column_order:
        columns[_column_name(z)] = {
            "state_id": _state_id(z),
            "symbol": _SYMBOL_BY_Z[z],
            "z": z,
            "charge": 0,
            "electron_count": z,
            "multiplicity": 1,
        }
    return {"states": states, "columns": columns}


def _remove_neutral_state(metadata: _Metadata) -> None:
    metadata["states"].pop(_state_id(8))


def _duplicate_neutral_state(metadata: _Metadata) -> None:
    metadata["states"]["duplicate_neutral_z008"] = dict(
        metadata["states"][_state_id(8)]
    )


def _remove_selected_column(metadata: _Metadata) -> None:
    metadata["columns"].pop(_column_name(8))


def _disagree_with_state(metadata: _Metadata) -> None:
    metadata["columns"][_column_name(8)]["multiplicity"] = 3


def test_zip_builder_is_deterministic_and_normalizes_member_metadata() -> None:
    csv_bytes = b"r_bohr,z001\n1e-6,1.0\n"

    first = snapshot_builder.build_deterministic_zip(csv_bytes)
    second = snapshot_builder.build_deterministic_zip(csv_bytes)
    assert first == second

    with zipfile.ZipFile(io.BytesIO(first), mode="r") as archive:
        assert archive.comment == b""
        assert len(archive.infolist()) == 1
        member = archive.infolist()[0]
        assert member.filename == snapshot_builder.ARCHIVE_MEMBER
        assert member.date_time == (1980, 1, 1, 0, 0, 0)
        assert member.compress_type == zipfile.ZIP_DEFLATED
        assert member.create_system == 3
        assert member.external_attr == 0o100644 << 16
        assert member.internal_attr == 0
        assert member.extra == b""
        assert member.comment == b""
        assert archive.read(member) == csv_bytes


def test_neutral_selection_is_metadata_driven_and_returns_in_z_order() -> None:
    odd_then_even = tuple(range(1, 104, 2)) + tuple(range(2, 104, 2))
    metadata = _synthetic_metadata(
        state_order=tuple(reversed(_EXPECTED_Z)),
        column_order=odd_then_even,
    )

    selected = snapshot_builder._select_neutral_columns(metadata)

    assert selected == tuple((z, _column_name(z)) for z in _EXPECTED_Z)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        pytest.param(
            _remove_neutral_state,
            "neutral-state coverage must be exact Z=1..103",
            id="missing-neutral-z",
        ),
        pytest.param(
            _duplicate_neutral_state,
            "multiple neutral states for Z=8",
            id="duplicate-neutral-z",
        ),
        pytest.param(
            _remove_selected_column,
            "selected state 'neutral_z008' maps to 0 CSV columns",
            id="missing-selected-column",
        ),
        pytest.param(
            _disagree_with_state,
            "state/column metadata disagree for 'neutral_z008': multiplicity",
            id="state-column-disagreement",
        ),
    ),
)
def test_neutral_selection_rejects_invalid_metadata(
    mutate: Callable[[_Metadata], None],
    message: str,
) -> None:
    metadata = _synthetic_metadata()
    mutate(metadata)

    with pytest.raises(snapshot_builder.SnapshotError, match=message):
        snapshot_builder._select_neutral_columns(metadata)


def test_pinned_source_reader_rejects_hash_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "profiles.csv"
    source.write_bytes(b"not the pinned source")

    with pytest.raises(snapshot_builder.SnapshotError, match="SHA-256 mismatch"):
        snapshot_builder._read_pinned(
            source,
            expected_sha256="0" * 64,
            label="profiles.csv",
        )


def test_check_mode_rejects_output_byte_mismatch(tmp_path: Path) -> None:
    output = tmp_path / "snapshot.zip"
    output.write_bytes(b"stale snapshot")

    with pytest.raises(snapshot_builder.SnapshotError, match="snapshot differs"):
        snapshot_builder._check_output(output, b"expected snapshot")
