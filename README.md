# atomref

[![CI](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml)
[![Docs](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/atomref.svg)](https://pypi.org/project/atomref/)
[![Python Versions](https://img.shields.io/pypi/pyversions/atomref.svg)](https://pypi.org/project/atomref/)
[![License](https://img.shields.io/pypi/l/atomref.svg)](https://github.com/DeloneCommons/atomref/blob/main/LICENSE)

`atomref` is a small pure-Python package for **curated atomic reference data**
and **provenance-aware lookup policies** used by geometry and
structure-analysis algorithms.

It is not meant to be yet another periodic-table encyclopedia. The package is
for code that needs stable atomic reference values with explicit provenance,
clear fallback behavior, and honest handling of incomplete preferred datasets.

What you get in the current `0.1.x` line:

- stable element metadata,
- curated named radii sets,
- provisional X–H bond-length support for hydrogen-normalisation workflows,
- dataset provenance and coverage metadata,
- deterministic lookup policies,
- substitution and linear transfer from support datasets or policies into target datasets,
- user-defined custom element-indexed scalar sets.

## Core terms

`atomref` uses a small vocabulary on purpose.

- **quantity** — the operational property family being requested, such as
  `covalent_radius`, `van_der_waals_radius`, `atomic_radius`, or
  `xh_bond_length`.
- **domain** — the key space used to index that quantity. In the current
  runtime, the supported domain is `element`, meaning lookups are keyed by an
  element symbol.
- **dataset** — one curated named table inside a quantity, such as
  `cordero2008`, `alvarez2013`, or `csd_legacy_xh_cno`.
- **policy** — the ordered rule set that decides what value to return when the
  preferred dataset is incomplete.

The metadata layer already records `domain` explicitly because the package is
built for later extension, but the current runtime intentionally keeps the
implementation narrow and stable: **v0.1 resolves only element-domain scalar
values**.

## Why this exists

Scientific software often wants a complete lookup table, but the best dataset
for the job is rarely complete. `atomref` makes that situation explicit.
Instead of hiding ad hoc defaults inside algorithm code, you choose a target
set, describe how missing values may be restored, and keep provenance on what
was actually returned.

The default `0.1.x` behavior is intentionally simple and practical:

- **Cordero covalent radii** (`cordero2008`) are the preferred covalent target
  set, with missing values substituted from the **legacy CSD covalent radii**
  (`csd_legacy_cov`).
- **Alvarez van der Waals radii** (`alvarez2013`) are the preferred vdW target
  set, with missing values restored from the **Rahm isodensity atomic radii**
  (`rahm2016`) through a fitted linear transfer.
- **CSD/ConQuest hydrogen-normalisation defaults** (`csd_legacy_xh_cno`) are a
  provisional sparse X–H target set for `C`, `N`, and `O`, with other parent
  elements inferred from **Cordero covalent radii** through a fitted linear
  policy.

## Quick example

```pycon
>>> import atomref as ar
>>> ar.get_covalent_radius("C")
0.76
>>> ar.get_vdw_radius("O")
1.5
>>> ar.get_xh_bond_length("N")
1.015
>>> lookup = ar.lookup_vdw_radius("Pm")
>>> lookup.value
2.8972265395148358
>>> lookup.source
'transfer_linear'
>>> lookup.resolved_from
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
```

`get_*` returns only the number. `lookup_*` returns a `LookupResult` that also
records where the value came from and whether a transfer model or policy source
was involved.

You can inspect the packaged quantity and dataset catalog directly:

```pycon
>>> import atomref as ar
>>> ar.list_quantities()
('covalent_radius', 'van_der_waals_radius', 'atomic_radius', 'xh_bond_length')
>>> ar.get_quantity_info("xh_bond_length")
QuantityInfo(quantity='xh_bond_length', domain='element', units='angstrom', description='Element-indexed reference X-H bond lengths keyed by parent element X and intended for hydrogen-position normalisation or related geometry workflows.')
>>> [info.ref.set_id for info in ar.list_dataset_infos("van_der_waals_radius", usage_role="target")]
['bondi1964', 'rowland_taylor1996', 'alvarez2013', 'chernyshov2020']
```

You can also load a packaged set directly:

```pycon
>>> import atomref as ar
>>> vdw = ar.get_radii_set("van_der_waals", "alvarez2013")
>>> vdw.get("O")
1.5
>>> xh = ar.get_xh_set("csd_legacy_xh_cno")
>>> xh.get("C")
1.089
```

## Notebook walkthroughs

The repository ships example notebooks for the main `0.1.x` workflows. In the
documentation they are also available as rendered Markdown pages, so users can
read them without opening Jupyter first.

- [Notebook overview](https://delonecommons.github.io/atomref/guide/notebooks/)
- [Quickstart notebook](https://delonecommons.github.io/atomref/notebooks/01-quickstart/)
- [Policies and assessment notebook](https://delonecommons.github.io/atomref/notebooks/02-policies-and-assessment/)
- [Custom sets and discovery notebook](https://delonecommons.github.io/atomref/notebooks/03-custom-sets-and-discovery/)

## Relationship to Delone Commons

`atomref` is designed as a standalone package, but within Delone Commons it is
primarily intended to support chemistry-aware packages such as:

- `molcryst`, for covalent-bond detection, contact analysis, and hydrogen workflows,
- future `chemvoro`, for chemistry-aware contact and hydrogen workflows.

By contrast, `pyvoro2` and `pbcgraph` are intentionally general mathematical
packages and are not direct consumers of `atomref`.

## Data curation and developer tools

The repository also ships small maintenance tools. The most important ones are:

- `python tools/check_registry.py` — validate curated registry metadata against
  packaged CSV tables,
- `python tools/check_notebooks.py` — execute notebook code cells,
- `python tools/export_notebooks.py` — turn notebooks into Markdown pages for
  the docs,
- `python tools/gen_readme.py` — regenerate `README.md` from this page,
- `python tools/release_check.py` — run the full release-preparation checklist,
  including linting, tests, docs, builds, and artifact validation.

See the [tools README](https://github.com/DeloneCommons/atomref/blob/main/tools/README.md)
for a short description of each script.

---

This README is generated from `docs/index.md`.

To regenerate it:

```bash
python tools/gen_readme.py
```

Edit the documentation sources instead of editing `README.md` directly.
