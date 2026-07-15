# atomref

[![CI](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/ci.yml)
[![Docs](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml/badge.svg)](https://github.com/DeloneCommons/atomref/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/atomref.svg)](https://pypi.org/project/atomref/)
[![Python Versions](https://img.shields.io/pypi/pyversions/atomref.svg)](https://pypi.org/project/atomref/)
[![License](https://img.shields.io/pypi/l/atomref.svg)](https://github.com/DeloneCommons/atomref/blob/main/LICENSE)

Documentation: https://delonecommons.github.io/atomref

`atomref` provides cited atomic properties and frozen spherical free-atom
electron densities through a small Python API for crystallographic,
quantum-chemical, and molecular-structure algorithms.

Use it when your software needs dependable atomic radii, X–H reference lengths,
neutral proatomic densities, or pairwise reference-atom boundaries without
embedding another project-local table and its fallback rules. The core runtime
is pure Python and has **no required third-party dependencies**.

## Install and get a useful result

```bash
pip install atomref
```

```python
import atomref as ar

covalent_c = ar.get_covalent_radius("C")
xh_n = ar.get_xh_bond_length("N")
rho_o = ar.get_proatomic_density("O", 0.75)
boundary = ar.estimate_proatomic_boundary("C", "O", 1.43)
minimum = ar.estimate_promolecular_density_minimum("C", "O", 1.43)
```

The scalar results above are in documented units: radii and X–H lengths use
angstrom, while the density call returns electron/bohr³ by default. Pairwise
coordinates are measured from the first atom toward the second. For this C–O
example, `boundary` is the stable equal-proatom divider and `minimum` is the
optional, resolution-limited minimum of the summed promolecular line density.

[Start with the quickstart](https://delonecommons.github.io/atomref/guide/quickstart/)
or open the [complete API reference](https://delonecommons.github.io/atomref/api/).

## What it solves

- **Bond and contact geometry:** select named covalent and van der Waals radii
  instead of scattering constants through structure code.
- **Hydrogen normalization:** obtain provisional, provenance-aware X–H target
  lengths keyed by the parent element.
- **Incomplete reference tables:** use explicit substitution or fitted transfer
  policies and inspect how a value was obtained.
- **Free-atom density sampling:** evaluate immutable neutral H–Lr spherical
  profiles with explicit coordinate and density units over a strict 0–20 bohr
  domain.
- **Pairwise reference-atom models:** choose a stable proatomic boundary or an
  explicitly cutoff-bounded promolecular-minimum proxy without presenting
  either as an exact molecular QTAIM surface.

Most convenience functions come in two forms:

```pycon
>>> import atomref as ar
>>> ar.get_vdw_radius("Pm")
2.8972265395148358
>>> result = ar.lookup_vdw_radius("Pm")
>>> result.source, result.transfer_depth
('transfer_linear', 1)
>>> result.resolved_from
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
```

`get_*` returns the selected number. `lookup_*` returns a typed `LookupResult`
with the source, supporting datasets, placeholder state, fit information, and
transfer depth.

## Why adopt `atomref`?

A local constants file is easy to start and difficult to maintain. It usually
accumulates uncited values, silent replacements for missing elements, ambiguous
units, and behavior that cannot be reviewed independently of the consuming
algorithm. `atomref` keeps those concerns in one versioned layer:

- every packaged dataset has a stable identifier, coverage metadata, and
  bibliographic provenance;
- lookup rules are explicit and deterministic rather than hidden in callers;
- direct, substituted, fitted, fallback, placeholder, and missing results stay
  distinguishable;
- public types, units, valid ranges, and failure behavior are documented;
- packaged data and attribution are checked in both wheel and source
  distributions;
- the dependency-free runtime can be embedded in lightweight scientific tools.

The package does not claim that one table or policy is universally correct. It
makes the selected reference and the assumptions around it visible.

## Installation choices

The base install is sufficient for every runtime API:

```bash
pip install atomref
```

Install the notebook extra to run the shipped Jupyter examples and their plots:

```bash
pip install "atomref[notebook]"
```

Install all current user-facing optional features with:

```bash
pip install "atomref[all]"
```

Contributor test, lint, build, upload, and release tools are intentionally not
part of `all`. See the [installation guide](https://delonecommons.github.io/atomref/guide/install/)
for development setup.

## Data, provenance, and scientific scope

The scalar catalog includes named covalent, van der Waals, atomic-isodensity,
and provisional X–H datasets. Registry metadata separates the requested
quantity from scientific classification and from whether a dataset is a direct
target or transfer support.

The neutral proatomic profiles are a deterministic packaged snapshot of the
`atomref-proatoms` 2.0.0 dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`. They cover H–Lr and record the PBE0,
self-consistent spherical fractional-occupation UKS, spin-free one-electron
X2C, and dyall-v4z definition, source hashes, CC BY 4.0 data license, and both
concept and version-specific DOIs.

These profiles are isolated, neutral, spherical reference atoms—not molecular
electron densities. Density evaluation is scalar, and the public radius domain
is exactly 0–20 bohr. Pairwise `boundary` mode is the stable default. Optional
`minimum` mode searches only where both proatoms remain above
`1e-4 electron/bohr^3`, has a declared `0.01 bohr` resolution, and may return a
typed diagnostic without a coordinate.

- [Dataset catalog and provenance](https://delonecommons.github.io/atomref/datasets/)
- [Proatomic-density and pairwise scientific guide](https://delonecommons.github.io/atomref/guide/proatomic_density/)
- [Policy guide](https://delonecommons.github.io/atomref/guide/policies/)
- [Explicit non-goals](https://delonecommons.github.io/atomref/guide/non_goals/)

## Executable notebook documentation

The documentation renders the actual committed `.ipynb` files directly,
including Markdown, code, mathematics, saved text, and saved PNG plots. Site
builds do not execute or rewrite them; a separate temporary Jupyter smoke check
verifies that their code still runs.

- [Notebook overview](https://delonecommons.github.io/atomref/guide/notebooks/)
- [Quickstart notebook](https://delonecommons.github.io/atomref/notebooks/01-quickstart/)
- [Policies and assessment notebook](https://delonecommons.github.io/atomref/notebooks/02-policies-and-assessment/)
- [Custom sets and discovery notebook](https://delonecommons.github.io/atomref/notebooks/03-custom-sets-and-discovery/)
- [IAS method-selection study](https://delonecommons.github.io/atomref/notebooks/04-ias-method-selection-study/)
- [Proatomic density and IAS workflows](https://delonecommons.github.io/atomref/notebooks/05-proatomic-density-and-ias/)

## Dataset and policy discovery

The lower-level registry is available when an application needs to choose or
report an exact source:

```pycon
>>> import atomref as ar
>>> ar.list_quantities()
('covalent_radius', 'van_der_waals_radius', 'atomic_radius', 'xh_bond_length', 'proatomic_density')
>>> [info.ref.set_id for info in ar.list_dataset_infos(
...     "van_der_waals_radius", usage_role="target"
... )]
['bondi1964', 'rowland_taylor1996', 'alvarez2013', 'chernyshov2020']
>>> profile_info = ar.get_proatomic_density_set_info()
>>> profile_info.ref.set_id
'pbe0_sfx2c_dyallv4z_h-lr_neutral_v2'
```

Custom element-indexed scalar sets can participate in the same policy layer.
Radial profiles deliberately do not: no scalar `ValuePolicy`, neighboring-
element substitution, or fitted correlation is applied to density data.

## Use in scientific software

`atomref` is a standalone package for physicochemical and structural-analysis
software that needs curated atomic properties, proatomic densities, or explicit
reference-data policy. Purely mathematical packages can remain independent of
those choices until a consuming application needs atomic context.

## Maintainer checks

The repository keeps a small set of release tools:

- `python tools/check_registry.py` validates registry metadata against every
  packaged scalar and radial payload;
- `python tools/check_notebooks.py` smoke-executes temporary notebook copies
  through a standard Jupyter kernel and discards the results;
- `python tools/gen_readme.py` regenerates this README from `docs/index.md`;
- `python tools/release_check.py` runs lint, tests, strict docs, distribution
  checks, and clean artifact-installation checks.

See the [tools README](https://github.com/DeloneCommons/atomref/blob/main/tools/README.md)
for the maintainer-only data snapshot workflow and command details.

---

This README is generated from `docs/index.md`.

To regenerate it:

```bash
python tools/gen_readme.py
```

Edit the documentation sources instead of editing `README.md` directly.
