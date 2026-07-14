# atomref.registry

This module contains the packaged data model.

If you want to understand how `atomref` classifies datasets, how aliases are
resolved, or how built-in scalar CSV and radial ZIP/CSV payloads become typed
in-memory objects, this is the key module to read.

The most important registry ideas are:

- **quantity** — the operational property family,
- **domain** — the key space used to index that quantity,
- **dataset** — one curated named source payload inside the quantity.

In the current runtime, the implemented lookup domain is `element`.
The registry still stores `domain` explicitly because the metadata design is
meant to stay reusable as the package grows.

[`get_builtin_set()`][atomref.get_builtin_set] dispatches `element_scalar_csv` and
`element_radial_csv_zip` storage and returns the `BuiltinSet` union. Policy
consumers explicitly narrow that result to `ElementScalarSet`; radial profiles
do not participate in scalar policy or transfer behavior.

::: atomref.registry
    options:
      members:
        - QuantityId
        - DomainId
        - DatasetRef
        - Reference
        - CoverageInfo
        - QuantityInfo
        - DatasetInfo
        - ElementScalarSet
        - ElementRadialSet
        - BuiltinSet
        - ScalarDatasetLike
        - list_quantities
        - get_quantity_info
        - list_dataset_ids
        - list_dataset_infos
        - get_dataset_info
        - get_builtin_set
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
