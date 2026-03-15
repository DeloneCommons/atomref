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

For policy-backed linear predictors, `LinearTransfer` separates two questions:

- which nested predictor values may be used to **fit** the linear model
  (`fit_sources`, `fit_max_depth`), and
- which nested predictor values may be used to **predict** the final requested
  element (`prediction_sources`, `prediction_max_depth`).

The defaults are intentionally conservative:

- fit only on nested predictor values that came directly from `base` or
  `override`,
- but allow one additional nested transfer step when evaluating the predictor
  for the requested element.

That default is meant for workflows such as a sparse X–H target set correlated
against a partial covalent-radii policy that is itself completed from a broader
support set.

::: atomref.transfer
