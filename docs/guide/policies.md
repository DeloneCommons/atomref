# Policies

A policy tells `atomref` how to answer the question “what value should I use for
this element?”

That may sound simple, but in practice scientific datasets are often
incomplete. A policy makes the decision process explicit instead of hiding it in
algorithm code.

## Terms used in the policy layer

A few terms appear repeatedly in the API and docs:

- **quantity** — the operational property family being requested.
- **domain** — the lookup key space. In the current runtime that means
  `element`, so lookups are keyed by element symbol.
- **dataset** — a curated named table inside one quantity.
- **policy** — the ordered rule set used to resolve missing values.

The quantity and dataset live in the curated registry. The policy is the
selection logic that sits on top of them.

## Resolution order

In `0.1.x` every lookup follows the same ordered path:

1. **Blocked key** (optional)
2. **Override**
3. **Base dataset**
4. **Transfer models**, in the order you listed them
5. **Fallback**
6. **Missing**

Each step has a specific meaning.

### Blocked key

Some quantity wrappers need to declare that certain domain keys should never be
resolved, even if a transfer model could otherwise invent a number. The current
X–H helper uses this for `H`, because `xh_bond_length` is keyed by the parent
atom `X` in `X–H`, not by hydrogen itself.

### Override

An override is a value you provide directly for a specific element. It wins over
everything else and is useful when you want to pin one or two elements without
changing the whole dataset.

### Base dataset

The base dataset is the preferred source. For example, the default covalent
policy starts from the **Cordero covalent radii** (`cordero2008`), and the
default vdW policy starts from the **Alvarez van der Waals radii**
(`alvarez2013`).

### Transfer

A transfer model is used only when the base dataset has no value for the
requested element.

Built-in transfer models in `0.1.x` are:

- `SubstitutionTransfer` — take a value directly from another dataset or policy,
- `LinearTransfer` — infer a target-equivalent value from another dataset or
  policy through a fitted linear model.

`LinearTransfer` already accepts a tuple of predictors in the API, but the
current runtime intentionally supports exactly one predictor source. That keeps
the implementation simple now while leaving room for later multi-predictor
linear models.

Transfer sources can now be:

- a packaged dataset reference (`DatasetRef`),
- a custom `ElementScalarSet`,
- a generic `ValuePolicy`,
- a wrapper policy such as `RadiiPolicy` or `XHPolicy`.

When a transfer source is itself a policy, `atomref` uses the values selected by
that policy. This lets higher-level workflows express things like “infer X–H
lengths from my chosen covalent-radii policy” instead of hard-coding a specific
support dataset.

### Fallback

A fallback is a constant last-resort value. It is useful when an algorithm must
receive *some* number even if both the base dataset and transfer sources are
missing a value.

### Missing

If nothing above can produce a value and no fallback was configured, the result
is simply missing. In that case `get_*` returns `None`, while `lookup_*`
returns a `LookupResult` with `source="missing"` and explanatory notes.

## Placeholder values and `is_placeholder`

Some support datasets use placeholder numbers to stand in for “unknown but keep
this legacy table dense enough for downstream heuristics”.

`LookupResult.is_placeholder` answers one narrow question:

> Is the **returned numeric value itself** marked as a placeholder by the source
> that supplied it?

It does **not** mean “a transfer happened”. Examples:

- a base lookup can have `is_placeholder=True` if the base dataset contains a
  placeholder value,
- a substitution transfer can also have `is_placeholder=True` if it copied a
  placeholder from the transfer source,
- a linear transfer is computed, not copied, so `is_placeholder` is normally
  `False`.

## Target datasets and support datasets

`atomref` separates **what a dataset is used for** from **what it scientifically
represents**.

That is why the package stores:

- the operational **quantity**,
- the lookup **domain**,
- the scientific **semantic class**,
- the package-level **usage role**.

This distinction matters for datasets such as **Rahm isodensity atomic radii**
(`rahm2016`). They are useful support data for restoring missing van der Waals
radii, but they are not the same thing as a condensed-phase structural vdW
radius set. In `atomref`, that difference is recorded in the metadata instead of
being hidden.

## Examples

A standard dataset-backed transfer:

```python
import atomref as ar

policy = ar.RadiiPolicy(
    kind="van_der_waals",
    base_set="alvarez2013",
    transfers=(
        ar.LinearTransfer(
            predictors=(ar.DatasetRef("atomic_radius", "rahm2016"),),
        ),
    ),
    overrides={"Xe": 2.10},
)
```

A policy-backed transfer source:

```python
import atomref as ar

xh_policy = ar.XHPolicy(
    base_set="csd_legacy_xh_cno",
    transfers=(
        ar.LinearTransfer(
            predictors=(ar.DEFAULT_COVALENT_POLICY,),
            min_points=3,
        ),
    ),
)
```

With that X–H policy:

- `C`, `N`, and `O` use the curated ConQuest defaults,
- missing parent elements may be inferred from the **selected covalent-radii
  policy**, not just from one hard-coded support dataset,
- if the predictor policy itself needed a transfer to produce a covalent radius,
  the resulting `LookupResult` still records that provenance in `resolved_from`
  and `notes`.
