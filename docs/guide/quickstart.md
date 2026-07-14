# Quickstart

Install the lightweight runtime:

```bash
pip install atomref
```

Then request the reference values needed by a structure workflow:

```pycon
>>> import atomref as ar
>>> ar.get_covalent_radius("C")
0.76
>>> ar.get_vdw_radius("O")
1.5
>>> ar.get_xh_bond_length("N")
1.015
```

Packaged radii and X–H lengths are in angstrom. `get_*` is the concise path
when an algorithm only needs the selected number.

## Keep provenance with the result

Use the matching `lookup_*` helper when a result must record how it was chosen:

```pycon
>>> lookup = ar.lookup_vdw_radius("Pm")
>>> lookup.value
2.8972265395148358
>>> lookup.source
'transfer_linear'
>>> lookup.transfer_depth
1
>>> lookup.resolved_from
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
```

A `LookupResult` distinguishes direct, overridden, substituted, fitted,
fallback, placeholder, and missing values. See the [policy guide](policies.md)
when you need to configure that resolution process.

## Evaluate a neutral proatomic density

The density API accepts an element symbol or atomic number and evaluates one
scalar radius at a time:

```pycon
>>> rho = ar.get_proatomic_density(
...     "O",
...     0.75,
...     radius_unit="angstrom",
...     density_unit="electron/bohr^3",
... )
>>> rho
0.1141799693379811
```

The packaged neutral H–Lr profiles have a strict 0–20 bohr public radius domain.
Radius and density units are selected independently. Invalid or out-of-range
radii raise `ValueError`; unsupported elements return `None`.

## Choose a pairwise reference-atom mode

For a C–O pair at 1.43 Å:

```pycon
>>> boundary = ar.estimate_proatomic_boundary("C", "O", 1.43)
>>> boundary.method, boundary.status
('equal_proatom_density', 'ok')
>>> minimum = ar.estimate_promolecular_density_minimum("C", "O", 1.43)
>>> minimum.method, minimum.status
('promolecular_density_minimum', 'ok')
>>> ar.estimate_ias_position("C", "O", 1.43) == boundary
True
```

`boundary` is the stable default: it uses homonuclear symmetry, equal neutral-
proatom contributions in the meaningful-overlap region, and a fixed contour-
gap rule at long separation. `minimum` is an optional, cutoff-bounded,
`0.01 bohr`-resolution proxy for a minimum of the summed promolecular line
density. It may return an explicit non-result and never silently switches to
boundary mode.

Neither result is an exact molecular-density QTAIM surface. Read the
[scientific guide](proatomic_density.md) before using pairwise coordinates in a
scientific interpretation.

## Inspect or load an exact dataset

The registry lets an application report and select exact sources:

```pycon
>>> ar.list_quantities()
('covalent_radius', 'van_der_waals_radius', 'atomic_radius', 'xh_bond_length', 'proatomic_density')
>>> [info.ref.set_id for info in ar.list_radii_set_infos(
...     "van_der_waals", usage_role="target"
... )]
['bondi1964', 'rowland_taylor1996', 'alvarez2013', 'chernyshov2020']
>>> vdw = ar.get_radii_set("van_der_waals", "alvarez2013")
>>> vdw.get("O")
1.5
```

## Continue with executable examples

- [Notebook overview](notebooks.md)
- [Quickstart notebook](../notebooks/01-quickstart.ipynb)
- [Policies and assessment notebook](../notebooks/02-policies-and-assessment.ipynb)
- [Custom sets and discovery notebook](../notebooks/03-custom-sets-and-discovery.ipynb)
- [IAS method-selection study](../notebooks/04-ias-method-selection-study.ipynb)
- [Proatomic density and IAS workflows](../notebooks/05-proatomic-density-and-ias.ipynb)
