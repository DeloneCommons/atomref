# Policies

A policy tells `atomref` how to answer the question “what value should I use for
this element?”

That may sound simple, but in practice scientific datasets are often
incomplete. A policy makes the decision process explicit instead of hiding it in
algorithm code.

## Resolution order

In v0.1 every lookup follows the same ordered path:

1. **Override**
2. **Base dataset**
3. **Transfer models**, in the order you listed them
4. **Fallback**
5. **Missing**

Each step has a specific meaning.

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

Built-in transfer models in v0.1 are:

- `SubstitutionTransfer` — take a value directly from another dataset,
- `LinearTransfer` — infer a target-equivalent value from a support dataset
  through a fitted linear model.

`LinearTransfer` already accepts a tuple of predictors in the API, but the v0.1
runtime intentionally supports exactly one predictor dataset. That keeps the
implementation simple now while leaving room for later multi-predictor linear
models.

### Fallback

A fallback is a constant last-resort value. It is useful when an algorithm must
receive *some* number even if both the base dataset and transfer sources are
missing a value.

### Missing

If nothing above can produce a value and no fallback was configured, the result
is simply missing. In that case `get_*` returns `None`, while `lookup_*`
returns a `LookupResult` with `source="missing"` and explanatory notes.

## Target datasets and support datasets

`atomref` separates **what a dataset is used for** from **what it scientifically
represents**.

That is why the package stores:

- the operational **quantity**,
- the scientific **semantic class**,
- the package-level **usage role**.

This distinction matters for datasets such as **Rahm isodensity atomic radii**
(`rahm2016`). They are useful support data for restoring missing van der Waals
radii, but they are not the same thing as a condensed-phase structural vdW
radius set. In `atomref`, that difference is recorded in the metadata instead of
being hidden.

## Example

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

With that policy:

- xenon uses the explicit override,
- elements present in `alvarez2013` use the base vdW value,
- missing elements may be restored from `rahm2016`,
- anything still unresolved remains missing unless you also set a fallback.
