# atomref.proatoms

This module exposes the neutral-density and two-mode pairwise API:

- [ProatomicDensityProfile][atomref.ProatomicDensityProfile] and
  [ProatomicDensitySet][atomref.ProatomicDensitySet] for immutable radial data;
- [`get_proatomic_density()`][atomref.get_proatomic_density] for scalar
  positive-region log-log evaluation;
- [`estimate_proatomic_boundary()`][atomref.estimate_proatomic_boundary] for
  the stable default divider;
- [`estimate_promolecular_density_minimum()`][atomref.estimate_promolecular_density_minimum]
  for the optional cutoff-bounded, resolution-limited minimum proxy;
- [`estimate_ias_position()`][atomref.estimate_ias_position] for explicit mode
  dispatch;
- [IASPositionResult][atomref.IASPositionResult] for coordinates, statuses,
  cutoff/search diagnostics,
  units, and provenance.

See the [proatomic-density guide](../guide/proatomic_density.md) for source
identity, units, the 20-bohr range, fixed cutoff, mode selection, statuses, and
limitations.

::: atomref.proatoms
    options:
      members:
        - DEFAULT_PROATOMIC_DENSITY_SET
        - BOHR_TO_ANGSTROM
        - PROATOMIC_TAIL_CUTOFF
        - IAS_MINIMUM_RESOLUTION_BOHR
        - IASPositionResult
        - ProatomicDensitySet
        - ProatomicDensityProfile
        - list_proatomic_density_sets
        - list_proatomic_density_set_infos
        - get_proatomic_density_set_info
        - get_proatomic_density_set
        - get_proatomic_density_profile
        - get_proatomic_density
        - estimate_proatomic_boundary
        - estimate_promolecular_density_minimum
        - estimate_ias_position
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
