# atomref.xh

This module provides focused X–H bond-length helpers.

It is intentionally narrow:

- one packaged sparse target dataset, `csd_legacy_xh_cno`,
- one wrapper policy, [XHPolicy][atomref.XHPolicy],
- convenience helpers for listing packaged X–H sets and resolving X–H values.

The built-in quantity is keyed by the **parent element `X`** in `X–H` and is
currently aimed at hydrogen-position normalisation or related geometry
workflows.

In the default policy:

- `C`, `N`, and `O` use curated ConQuest/CSD defaults,
- other parent elements may be inferred from `cordero2008`,
- policy-backed predictors are supported as well, with conservative nested-fit
  defaults and one additional nested prediction step allowed by default,
- the API does not infer a rigorous molecular bond length or perform atom
  typing beyond the parent-element policy.

::: atomref.xh
    options:
      members:
        - XHSet
        - XHPolicy
        - DEFAULT_XH_POLICY
        - list_xh_sets
        - list_xh_set_infos
        - get_xh_set_info
        - get_xh_set
        - lookup_xh_bond_length
        - get_xh_bond_length
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
