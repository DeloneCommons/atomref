# atomref

`atomref` is a small pure-Python package for curated atomic reference data and
policy-based lookup in geometry and structure-analysis code.

It is **not** a periodic-table encyclopedia. The package is meant to sit under
higher-level scientific software and provide:

- stable element metadata,
- named radii sets,
- explicit dataset provenance,
- deterministic lookup policies,
- transfer from broader-support datasets into narrower target sets.

For v0.1 the public scope is intentionally radii-first.

## Why this exists

Many geometry algorithms need a complete reference table, but the scientifically
preferred dataset is often incomplete. `atomref` makes that situation explicit:
choose a target dataset, add one or more transfer steps, and keep provenance on
what was returned.

The default examples mirror the current `molcryst` behavior:

- covalent radii: use `cordero2008`, substitute from `csd_legacy_cov`
- van der Waals radii: use `alvarez2013`, linearly transfer from
  `atomic_radius:rahm2016`

## Quick example

```python
import atomref as ar

r_c = ar.get_covalent_radius("C")
r_vdw = ar.get_vdw_radius("O")

lookup = ar.lookup_vdw_radius("Pm")
print(lookup.value, lookup.source, lookup.resolved_from)
```

## Public API split: `get_*` vs `lookup_*`

- `get_*` returns only the selected numeric value, or `None`.
- `lookup_*` returns the provenance-carrying `LookupResult` object.

This follows the current `molcryst` pattern.

## Current built-in quantities

- `covalent_radius`
- `van_der_waals_radius`
- `atomic_radius` (support quantity; currently used for transfer from
  `rahm2016`)

## Relationship to the Delone Commons ecosystem

`atomref` is intended to be reusable outside the surrounding ecosystem, but it
fits naturally beneath:

- `molcryst`
- `pyvoro2`
- `pbcgraph`

Those packages should consume atomic reference data from `atomref` rather than
re-curating such datasets independently.
