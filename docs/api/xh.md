# atomref.xh

This module provides the provisional X–H bond-length helpers available in the
current release line.

It is intentionally narrow:

- one packaged sparse target dataset, `csd_legacy_xh_cno`,
- one wrapper policy, `XHPolicy`,
- convenience helpers for listing packaged X–H sets and resolving X–H values.

The built-in quantity is keyed by the **parent element `X`** in `X–H` and is
currently aimed at hydrogen-position normalisation or related geometry
workflows.

In the default policy:

- `C`, `N`, and `O` use curated ConQuest/CSD defaults,
- other parent elements may be inferred from `cordero2008`,
- policy-backed predictors are supported as well, with conservative nested-fit
  defaults and one additional nested prediction step allowed by default,
- fuller X–H literature support is planned for `0.2.x`.

::: atomref.xh
