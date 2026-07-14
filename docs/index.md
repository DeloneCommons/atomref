# atomref

[![CI](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml)
[![Docs](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/atomref.svg)](https://pypi.org/project/atomref/)
[![Python Versions](https://img.shields.io/pypi/pyversions/atomref.svg)](https://pypi.org/project/atomref/)
[![License](https://img.shields.io/pypi/l/atomref.svg)](https://github.com/DeloneCommons/atomref/blob/main/LICENSE)

`atomref` is a small pure-Python package for **curated atomic reference data**,
**provenance-aware lookup policies**, and neutral-proatom reference workflows
used by geometry and structure-analysis algorithms.

It is not meant to be yet another periodic-table encyclopedia. The package is
for code that needs stable atomic reference values with explicit provenance,
clear fallback behavior, and honest handling of incomplete preferred datasets.

What you get in the current release line:

- stable element metadata,
- curated named radii sets,
- provisional X–H bond-length support for hydrogen-normalisation workflows,
- dataset provenance and coverage metadata,
- deterministic lookup policies,
- substitution and linear transfer from support datasets or policies into target datasets,
- guarded nested policy-backed transfers with explicit transfer depth,
  conservative fit/prediction controls, and cycle detection,
- user-defined custom element-indexed scalar sets,
- frozen neutral H–Lr spherical proatomic-density profiles with scalar,
  unit-aware evaluation,
- a stable pairwise neutral-proatom boundary and an optional cutoff-bounded,
  resolution-limited promolecular-minimum proxy.

## Core terms

`atomref` uses a small vocabulary on purpose.

- **quantity** — the operational property family being requested, such as
  `covalent_radius`, `van_der_waals_radius`, `atomic_radius`, or
  `xh_bond_length`, or `proatomic_density`.
- **domain** — the key space used to index that quantity. In the current
  runtime, the supported domain is `element`, meaning lookups are keyed by an
  element symbol.
- **dataset** — one curated named scalar table or radial-profile payload inside
  a quantity, such as `cordero2008`, `alvarez2013`, or the neutral H–Lr
  proatomic set.
- **policy** — the ordered rule set that decides what scalar value to return
  when the preferred dataset is incomplete.

The metadata layer records `domain` and storage kind explicitly. The current
runtime supports the `element` domain with packaged scalar tables and one
shared-grid radial-profile family. Lookup policies, substitution, and linear
transfer intentionally remain scalar-only; radial profiles are never completed
by correlation or neighboring-element substitution.

## Why this exists

Scientific software often wants a complete lookup table, but the best dataset
for the job is rarely complete. `atomref` makes that situation explicit.
Instead of hiding ad hoc defaults inside algorithm code, you choose a target
set, describe how missing values may be restored, and keep provenance on what
was actually returned.

The built-in default behavior is intentionally simple and practical:

- **Cordero covalent radii** (`cordero2008`) are the preferred covalent target
  set, with missing values substituted from the **legacy CSD covalent radii**
  (`csd_legacy_cov`).
- **Alvarez van der Waals radii** (`alvarez2013`) are the preferred vdW target
  set, with missing values restored from the **Rahm isodensity atomic radii**
  (`rahm2016`) through a fitted linear transfer.
- **CSD/ConQuest hydrogen-normalisation defaults** (`csd_legacy_xh_cno`) are a
  provisional sparse X–H target set for `C`, `N`, and `O`, with other parent
  elements inferred from **Cordero covalent radii** through a fitted linear
  transfer.

Nested policy predictors are supported too. `LinearTransfer` separates
**fit-time** use of nested predictor values from **prediction-time** use. By default, the fit may use only direct nested
values, while the final requested element may still use one additional
nested completion step. That is a useful compromise for workflows such as
provisional X–H inference from a chosen covalent-radii policy.

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
>>> lookup.transfer_depth
1
>>> lookup.resolved_from
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
>>> ar.get_proatomic_density("O", 0.75)
0.1141799693379811
>>> boundary = ar.estimate_proatomic_boundary("C", "O", 1.5, distance_unit="bohr")
>>> boundary.method, boundary.status
('equal_proatom_density', 'ok')
```

`get_*` returns only the number. `lookup_*` returns a `LookupResult` that also
records where the value came from, whether a transfer model or policy source was
involved, and how many transfer steps were needed (`transfer_depth`).

You can inspect the packaged quantity and dataset catalog directly:

```pycon
>>> import atomref as ar
>>> ar.list_quantities()
('covalent_radius', 'van_der_waals_radius', 'atomic_radius', 'xh_bond_length', 'proatomic_density')
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
>>> info = ar.get_proatomic_density_set_info()
>>> radial = ar.get_builtin_set(info.ref)
>>> type(radial).__name__
'ElementRadialSet'
```

The proatomic profiles are isolated neutral spherical references, not molecular
electron densities. Pairwise `boundary` mode is the stable default. Optional
`minimum` mode searches only above the fixed `1e-4 electron/bohr^3` per-atom
tail cutoff and has a practical resolution of `0.01 bohr`; it may return an
explicit diagnostic status without a coordinate. See the
[proatomic-density guide](https://delonecommons.github.io/atomref/guide/proatomic_density/)
for the 20-bohr domain, units, provenance, mode selection, and physical
limitations.

## Notebook walkthroughs

The repository ships example notebooks for the main workflows. The first three
are also available as rendered Markdown pages. The `0.2.0` proatomic notebooks
are saved, executed source artifacts with outputs and plots.

- [Notebook overview](https://delonecommons.github.io/atomref/guide/notebooks/)
- [Quickstart notebook](https://delonecommons.github.io/atomref/notebooks/01-quickstart/)
- [Policies and assessment notebook](https://delonecommons.github.io/atomref/notebooks/02-policies-and-assessment/)
- [Custom sets and discovery notebook](https://delonecommons.github.io/atomref/notebooks/03-custom-sets-and-discovery/)
- [IAS method-selection study](https://delonecommons.github.io/atomref/dev/ias_method_selection/)
- [Executed proatomic density and IAS feature notebook](https://github.com/DeloneCommons/atomref/blob/main/notebooks/05-proatomic-density-and-ias.ipynb)

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
  every packaged scalar and radial payload,
- `python tools/check_notebooks.py` — validate saved release-notebook state and
  execute notebook code cells,
- `python tools/export_notebooks.py` — turn notebooks into Markdown pages for
  the docs,
- `python tools/gen_readme.py` — regenerate `README.md` from this page,
- `python tools/release_check.py` — run the full release-preparation checklist,
  including linting, tests, docs, builds, and artifact validation.

See the [tools README](https://github.com/DeloneCommons/atomref/blob/main/tools/README.md)
for a short description of each script.
