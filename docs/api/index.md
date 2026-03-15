# API

The public API is small on purpose.

Most users will spend most of their time in the top-level package namespace and
in the quantity-specific convenience helpers. The lower-level modules are still
documented because they expose the actual data model behind the package.

## Common tasks

- get a single value: use `get_covalent_radius(...)`, `get_vdw_radius(...)`, or
  `get_xh_bond_length(...)`
- inspect provenance: use `lookup_covalent_radius(...)`,
  `lookup_vdw_radius(...)`, `lookup_xh_bond_length(...)`, or the generic
  `lookup_value(...)`
- browse packaged datasets: use `list_quantities()`, `get_quantity_info(...)`,
  `list_dataset_infos(...)`, `list_radii_set_infos(...)`, or
  `list_xh_set_infos(...)`
- load a packaged set directly: use `get_builtin_set(...)`, `get_radii_set(...)`,
  or `get_xh_set(...)`
- define a custom set: use `ElementScalarSet.from_mapping(...)`
- define transfer-backed lookup behavior: use `ValuePolicy`, `RadiiPolicy`,
  `XHPolicy`, `SubstitutionTransfer`, and `LinearTransfer`

## Module reference

- [Top-level package](atomref.md)
- [Elements](elements.md)
- [Registry and packaged datasets](registry.md)
- [Transfer models](transfer.md)
- [Generic policy core](policy.md)
- [Radii API](radii.md)
- [X–H API](xh.md)
