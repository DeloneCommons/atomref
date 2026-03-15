# atomref.transfer

Transfer models describe how missing target values may be restored from other
sources.

In the current runtime the built-in models are:

- direct substitution (`SubstitutionTransfer`),
- one-predictor linear transfer (`LinearTransfer`).

A transfer source may be:

- a packaged dataset reference,
- a custom `ElementScalarSet`,
- a generic `ValuePolicy`,
- a wrapper policy that exposes `as_value_policy()`.

`LinearTransfer` currently accepts exactly one predictor source at runtime, even
though the public API stores predictors as a tuple for forward compatibility.

::: atomref.transfer
