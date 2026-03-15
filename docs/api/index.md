# API

The public API is small on purpose.

Most users will spend most of their time in the top-level package namespace and
in the radii helpers. The lower-level modules are still documented because they
expose the actual data model behind the package.

## Common tasks

- get a single value: use `get_covalent_radius(...)` or `get_vdw_radius(...)`
- inspect provenance: use `lookup_covalent_radius(...)` or
  `lookup_vdw_radius(...)`
- browse packaged datasets: use `list_quantities()`, `get_quantity_info(...)`,
  `list_dataset_infos(...)`, or `list_radii_set_infos(...)`
- load a packaged set directly: use `get_builtin_set(...)` or `get_radii_set(...)`
- define a custom set: use `ElementScalarSet.from_mapping(...)`
- define transfer-backed lookup behavior: use `RadiiPolicy`,
  `SubstitutionTransfer`, and `LinearTransfer`

## Module reference

- [Top-level package](atomref.md)
- [Elements](elements.md)
- [Registry and packaged datasets](registry.md)
- [Transfer models](transfer.md)
- [Generic policy core](policy.md)
- [Radii API](radii.md)
