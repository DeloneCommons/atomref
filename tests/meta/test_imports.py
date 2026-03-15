from __future__ import annotations

import importlib


MODULES = [
    'atomref',
    'atomref.elements',
    'atomref.registry',
    'atomref.transfer',
    'atomref.policy',
    'atomref.radii',
    'atomref.xh',
]


def test_imports() -> None:
    for name in MODULES:
        importlib.import_module(name)
