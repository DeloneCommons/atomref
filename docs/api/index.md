# API

The public API is small on purpose.

Most users will spend most of their time in the top-level package namespace and
in the quantity-specific convenience helpers. The lower-level modules are still
documented because they expose the actual data model behind the package.

## Common tasks

- get a single value: use
  [`get_covalent_radius()`][atomref.get_covalent_radius],
  [`get_vdw_radius()`][atomref.get_vdw_radius], or
  [`get_xh_bond_length()`][atomref.get_xh_bond_length]
- evaluate a neutral profile or pairwise estimate: use
  [`get_proatomic_density()`][atomref.get_proatomic_density],
  [`estimate_proatomic_boundary()`][atomref.estimate_proatomic_boundary], or
  [`estimate_promolecular_density_minimum()`][atomref.estimate_promolecular_density_minimum]
- inspect provenance with the corresponding `lookup_*` function or the generic
  [`lookup_value()`][atomref.lookup_value]
- browse packaged datasets with [`list_quantities()`][atomref.list_quantities],
  [`get_quantity_info()`][atomref.get_quantity_info], or a quantity-specific
  metadata-listing helper
- load a packaged set directly with
  [`get_builtin_set()`][atomref.get_builtin_set]
- define a custom set with
  [`ElementScalarSet.from_mapping()`][atomref.ElementScalarSet.from_mapping]
- configure transfer-backed lookup with [ValuePolicy][atomref.ValuePolicy],
  [RadiiPolicy][atomref.RadiiPolicy], [XHPolicy][atomref.XHPolicy],
  [SubstitutionTransfer][atomref.SubstitutionTransfer], and
  [LinearTransfer][atomref.LinearTransfer]

## Module reference

- [Top-level package](atomref.md)
- [Exceptions](errors.md)
- [Elements](elements.md)
- [Registry and packaged datasets](registry.md)
- [Transfer models](transfer.md)
- [Generic policy core](policy.md)
- [Proatomic density and pairwise estimates](proatoms.md)
- [Radii API](radii.md)
- [X–H API](xh.md)
