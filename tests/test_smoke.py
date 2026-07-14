from __future__ import annotations

import atomref as ar


def test_release_version() -> None:
    assert ar.__version__ == '0.2.0'


def test_basic_smoke_import_and_lookup() -> None:
    assert ar.get_covalent_radius('C') == 0.76
    assert ar.get_vdw_radius('C') == 1.77
