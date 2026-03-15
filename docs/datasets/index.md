# Datasets

`atomref` does not treat all datasets as interchangeable lookup tables.
Instead, the package records several layers of classification:

- **quantity** — the operational property being requested,
- **semantic class** — what the dataset scientifically represents,
- **origin class** — how the values were obtained,
- **phase context** — what physical context they describe,
- **usage role** — whether the package treats the dataset as a direct target set
  or as support data for transfer.

This is what allows a dataset such as **Rahm isodensity atomic radii**
(`rahm2016`) to be useful in van der Waals workflows without pretending that it
is itself a condensed-phase structural vdW-radius set.

## Programmatic inspection

The most useful catalog helpers are:

- `atomref.list_quantities()`
- `atomref.get_quantity_info(...)`
- `atomref.list_dataset_infos(...)`
- `atomref.list_radii_set_infos(...)`

If you only need dataset ids, use `list_dataset_ids(...)` or `list_radii_sets(...)`.
If you want the packaged values themselves, use `get_builtin_set(...)` or
`get_radii_set(...)`.

## Built-in quantity families in v0.1

- [Covalent radius](covalent_radius.md)
- [van der Waals radius](van_der_waals_radius.md)
- [Atomic radius](atomic_radius.md)
