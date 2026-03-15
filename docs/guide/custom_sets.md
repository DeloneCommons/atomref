# Custom sets

`atomref` is not limited to the packaged tables. You can build a small
user-defined element-indexed scalar dataset and use it as a base dataset or as a
support dataset inside a transfer-backed policy.

The simplest entry point is `ElementScalarSet.from_mapping(...)`.

```python
from atomref import DatasetRef, ElementScalarSet, RadiiPolicy

custom = ElementScalarSet.from_mapping(
    ref=DatasetRef("covalent_radius", "my_cov"),
    values={"C": 0.75, "H": 0.31},
    name="My custom covalent radii",
    units="angstrom",
)

policy = RadiiPolicy(kind="covalent", base_set=custom)
```

This is useful when you want to:

- test an alternative reference table,
- pin a small project-specific dataset without creating a full package fork,
- combine a user dataset with built-in support data through substitution or
  linear transfer.

In v0.1 custom sets are element-domain scalar datasets, which keeps the data
model small and stable. Later versions may add more specialized domains, but
custom element-wise sets are already enough for many geometry workflows.
