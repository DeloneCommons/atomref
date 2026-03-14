# Datasets

The package distinguishes between:

- **quantity** — the operational property being requested,
- **semantic class** — what the dataset scientifically represents,
- **origin / phase context** — how and where it was derived.

This is what keeps support-only datasets such as `rahm2016` usable without
misclassifying them as direct condensed-phase vdW radii.

For programmatic inspection, use `atomref.list_quantities()` and `atomref.get_quantity_info(...)`.
