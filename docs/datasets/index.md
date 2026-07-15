# Datasets

`atomref` does not treat all datasets as interchangeable lookup tables.
Instead, the package records several layers of classification:

- **quantity** — the operational property being requested,
- **domain** — the key space used to index that quantity,
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
- `atomref.list_xh_set_infos(...)`

If you only need dataset ids, use `list_dataset_ids(...)`, `list_radii_sets(...)`,
or `list_xh_sets(...)`.
If you want the packaged values themselves, use `get_builtin_set(...)`,
`get_radii_set(...)`, or `get_xh_set(...)`.

## Neutral proatomic-density snapshot

The `proatomic_density` quantity currently contains the dataset
`pbe0_sfx2c_dyallv4z_h-lr_neutral_v2`: a truncated neutral H–Lr (Z = 1–103)
packaged snapshot of the `atomref-proatoms` 2.0.0 dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`. Its public radial domain is 0–20 bohr;
one original source point above 20 bohr is retained only to bracket that limit.
The native density unit is electron/bohr³.

The profiles use PBE0, self-consistent spherical fractional-occupation UKS,
spin-free one-electron X2C, and the dyall-v4z basis. These are method-, basis-,
state-, and sphericalization-defined reference densities, not unique
basis-independent atomic observables. Detailed state and generation metadata
remain in the exact upstream 2.0.0 archive.

The imported data are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
separately from the `atomref` code license. Cite both the
[atomref-proatoms concept DOI](https://doi.org/10.5281/zenodo.21291021) and the
[version-specific 2.0.0 DOI](https://doi.org/10.5281/zenodo.21291022).

## Built-in quantity families

- [Covalent radius](covalent_radius.md)
- [van der Waals radius](van_der_waals_radius.md)
- [Atomic radius](atomic_radius.md)
- [X–H bond length](xh_bond_length.md)
- [Proatomic density](../guide/proatomic_density.md)
