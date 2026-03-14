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
