# Architecture

Publicly, `atomref` provides scalar radii and X–H reference workflows together
with neutral radial proatomic-density evaluation and two explicit pairwise
neutral-proatom modes.

Internally, the package is built around four layers:

1. **elements** — stable element metadata and symbol canonicalization,
2. **registry** — curated quantity and dataset metadata plus generic packaged
   scalar/radial data loading,
3. **policy core** — generic value selection with overrides, transfers,
   fallbacks, blocked keys, and provenance,
4. **quantity features** — scalar convenience APIs such as `atomref.radii` and
   `atomref.xh`, plus immutable radial profiles and pairwise analysis in
   `atomref.proatoms`.

## Core terminology

A few terms are deliberately separated in the design:

- **quantity** — the operational property family being requested,
- **domain** — the key space used to index that quantity,
- **dataset** — one curated source payload inside the quantity,
- **policy** — the ordered rule set used to select a final value.

This separation is what allows the package to say, for example, that
`rahm2016` belongs to the `atomic_radius` quantity but can still act as support
data in a van der Waals policy.

## Domain support in the current runtime

The registry schema is domain-aware, but the current resolver intentionally
implements only one domain:

- `element`

Packaged element data currently use two explicit storage kinds:

- `element_scalar_csv` for dense-by-Z scalar tables,
- `element_radial_csv_zip` for a single-member ZIP containing shared-grid
  radial profiles.

`get_builtin_set()` dispatches both kinds and returns the `BuiltinSet` union of
`ElementScalarSet` and `ElementRadialSet`. Scalar consumers narrow that union
through `resolve_scalar_dataset_like()`.

The policy and transfer machinery remains intentionally scalar-only:
`ValuePolicy` resolves element scalars and transfer fitting uses element-wise
scalar overlap. Radial profiles receive no `ValuePolicy`, substitution, or
linear-transfer behavior.

The metadata keeps `domain` explicit now so later versions can extend the data
model without having to reinterpret existing registry entries.

## Policy resolution and transfer sources

The generic resolver works in a fixed order:

1. blocked keys,
2. overrides,
3. base dataset,
4. transfer models,
5. fallback,
6. missing.

Transfer sources can be:

- packaged datasets,
- custom `ElementScalarSet` objects,
- generic `ValuePolicy` objects,
- wrapper policies exposing `as_value_policy()`.

That last point is important. It means higher-level code can express
"infer values from my chosen covalent-radii policy" instead of being forced to
refer to one hard-coded predictor dataset.

## Nested-policy safeguards and cycle detection

Policy-backed transfer sources are materialized with more than just raw numeric
values. The resolver also tracks, per element:

- whether the value came from `base`, `override`, substitution, linear transfer,
  or fallback,
- the nested transfer depth that was required to produce it,
- placeholder status.

`LinearTransfer` uses that information twice:

- once when fitting the linear relation (`fit_sources` / `fit_max_depth`),
- again when deciding whether the predictor value for the requested element is
  admissible (`prediction_sources` / `prediction_max_depth`).

The default policy is intentionally conservative: fit only on direct nested
predictor values, but allow one additional nested completion step when
predicting the final requested element. This keeps the common two-stage use case
possible without silently training on arbitrarily long inference chains.

Cycle detection is handled with a context-local activation stack. Both generic
`ValuePolicy` objects and wrapper policies are tracked, so recursion through a
freshly materialized wrapper policy is still detected reliably and safely.

## Placeholder handling

Placeholder semantics stay attached to the value that was actually returned.
This means `LookupResult.is_placeholder` can be true for:

- a base lookup,
- a substitution transfer,
- a nested policy used as a transfer source.

A linear transfer normally returns a computed value and therefore does not carry
placeholder status itself. Instead, its provenance is carried by
`resolved_from`, explanatory notes, and `transfer_depth`.

## Why the design stays small

The package deliberately avoids a large object graph or a chemistry-specific DSL.
A quantity wrapper is usually only a thin adapter over the generic policy core.
That keeps the internals easy to test and lets other scientific packages reuse
`atomref` without requiring a larger application stack.

## Documentation and distribution boundary

The five files under `docs/notebooks/` are both the maintained Jupyter sources
and their documentation pages. `mkdocs-jupyter` renders their committed state
with execution disabled; `tools/check_notebooks.py` exercises temporary copies
one at a time through isolated, time-bounded standard Jupyter processes and
discards the results. Startup and cell timeouts remain separate, and a stalled
kernel cleanup or process exit is force-contained before the checker fails.
There is no exporter, generated notebook Markdown, source-copy step, or
output-freshness contract.

The wheel remains a focused runtime artifact containing package code, typing
metadata, legal notices, and curated data. The source distribution additionally
contains tests, tools, durable documentation, and the single notebook sources.
Base, `notebooks`, and `all` installations are validated from the built wheel
in separate temporary environments during release preparation. The `all`
variant is checked as the exact union of every declared optional dependency
group rather than as an alias for one feature group.
