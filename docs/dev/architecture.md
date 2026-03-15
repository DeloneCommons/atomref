# Architecture

Publicly, `atomref` is still radii-first, with a small provisional X–H helper.

Internally, the package is built around four layers:

1. **elements** — stable element metadata and symbol canonicalization,
2. **registry** — curated quantity and dataset metadata plus packaged data
   loading,
3. **policy core** — generic value selection with overrides, transfers,
   fallbacks, blocked keys, and provenance,
4. **quantity wrappers** — convenience APIs such as `atomref.radii` and
   `atomref.xh`.

## Core terminology

A few terms are deliberately separated in the design:

- **quantity** — the operational property family being requested,
- **domain** — the key space used to index that quantity,
- **dataset** — one curated source table inside the quantity,
- **policy** — the ordered rule set used to select a final value.

This separation is what allows the package to say, for example, that
`rahm2016` belongs to the `atomic_radius` quantity but can still act as support
data in a van der Waals policy.

## Domain support in the current runtime

The registry schema is domain-aware, but the current resolver intentionally
implements only one domain:

- `element`

That means:

- packaged built-in sets are currently element-indexed scalar tables,
- `ValuePolicy` resolves element symbols,
- transfer fitting is performed over element-wise overlap.

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

## Placeholder handling

Placeholder semantics stay attached to the value that was actually returned.
This means `LookupResult.is_placeholder` can be true for:

- a base lookup,
- a substitution transfer,
- a nested policy used as a transfer source.

A linear transfer normally returns a computed value and therefore does not carry
placeholder status itself.

## Why the design stays small

The package deliberately avoids a large object graph or a chemistry-specific DSL.
A quantity wrapper is usually only a thin adapter over the generic policy core.
That keeps the internals easy to test and lets other scientific packages reuse
`atomref` without bringing in the rest of the Delone Commons stack.
