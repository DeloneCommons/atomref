# atomref.registry

This module contains the packaged data model.

If you want to understand how `atomref` classifies datasets, how aliases are
resolved, or how built-in CSV tables are turned into typed in-memory objects,
this is the key module to read.

The most important registry ideas are:

- **quantity** — the operational property family,
- **domain** — the key space used to index that quantity,
- **dataset** — one curated named table inside the quantity.

In the current runtime, the implemented lookup domain is `element`.
The registry still stores `domain` explicitly because the metadata design is
meant to stay reusable as the package grows.

::: atomref.registry
