# atomref.policy

This module contains the generic resolver that sits below the radii-specific and
X–H-specific convenience APIs.

Use it when you want to work directly with the shared value-selection engine:

- [ValuePolicy][atomref.ValuePolicy] — generic element-domain configuration,
- [`lookup_value()`][atomref.lookup_value] — one value with provenance,
- [`get_value()`][atomref.get_value] — only the numeric value,
- [LookupResult][atomref.LookupResult] — the structured resolver result.

A few practical notes:

- The current runtime supports **element-domain** scalar policies.
- `ValuePolicy` normalizes element-symbol overrides eagerly.
- Transfer sources may be packaged datasets, custom sets, generic policies, or
  wrapper policies that expose `as_value_policy()`.
- `LookupResult.is_placeholder` refers to the returned numeric value itself, not
  to whether any transfer happened.
- `LookupResult.transfer_depth` counts how many transfer steps were involved in
  the returned numeric value.
- Nested lookup is cycle-checked across both generic `ValuePolicy` objects and
  wrapper policies such as `RadiiPolicy` and `XHPolicy`.

::: atomref.policy
    options:
      members:
        - LookupSource
        - LookupResult
        - ValuePolicy
        - lookup_value
        - get_value
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
