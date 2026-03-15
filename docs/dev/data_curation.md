# Data curation

Packaged tables are stored as CSV files indexed by atomic number. Dataset
metadata and provenance live in `src/atomref/data/registry.json`.

Placeholder values are modeled as dataset metadata, not as hard-coded Python
constants.

The registry distinguishes several orthogonal concerns:

- `quantity` — the operational lookup target, such as `covalent_radius` or
  `van_der_waals_radius`
- `semantic_class` — what the dataset scientifically represents
- `usage_role` — whether the dataset is intended as a direct target set or as
  support data for transfer
- `phase_context` — the physical context of the underlying values

This matters for support-only datasets such as `atomic_radius:rahm2016`, which
is packaged as atomic support data and then used by the default van der Waals
policy through linear transfer.

To check that metadata and packaged tables stay synchronized, run:

```bash
python tools/check_registry.py
```
