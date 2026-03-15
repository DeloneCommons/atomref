# atomref.xh

This module provides the provisional X–H bond-length helpers introduced in the
`0.1.x` line.

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
- fuller X–H literature support is planned for `0.2.x`.

::: atomref.xh
