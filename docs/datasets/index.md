# Datasets

The package distinguishes between:

- **quantity** — the operational property being requested,
- **semantic class** — what the dataset scientifically represents,
- **origin / phase context** — how and where it was derived.

This is what keeps support-only datasets such as `rahm2016` usable without
misclassifying them as direct condensed-phase vdW radii.

For programmatic inspection, use `atomref.list_quantities()`, `atomref.get_quantity_info(...)`, and `atomref.list_dataset_infos(...)`.

Dataset metadata also carries a package-level `usage_role`, which currently
distinguishes direct target sets from support-only sets used for substitution or
linear transfer. Use `atomref.list_dataset_ids(..., usage_role=...)` to inspect
that layer programmatically.
