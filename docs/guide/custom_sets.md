# Custom sets

Custom element-indexed scalar datasets can be built with
`ElementScalarSet.from_mapping(...)` and then used directly in a `RadiiPolicy`
or a transfer model.

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
