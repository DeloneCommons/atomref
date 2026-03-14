# Policies

A policy is the ordered rule set for selecting a value.

Resolution order in v0.1:

1. override
2. base dataset
3. transfers in order
4. fallback
5. missing

Built-in transfer models:

- `SubstitutionTransfer`
- `LinearTransfer`

`LinearTransfer` is intentionally limited to one predictor in v0.1, but the API
already accepts a predictor tuple so later multi-predictor linear models do not
require a redesign.

## Target vs support sets

`atomref` keeps the lookup behavior separate from the scientific classification
of a dataset. In addition, each built-in dataset now carries a package-level
`usage_role` such as `target` or `support`. This is how `rahm2016` can remain
available for linear transfer into `alvarez2013`-style vdW values without being
misrepresented as a direct condensed-phase vdW target set.
