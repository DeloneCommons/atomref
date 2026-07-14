# atomref.proatoms

This module exposes the accepted `0.2.0` density and two-mode pairwise API:

- `ProatomicDensityProfile` and `ProatomicDensitySet` for immutable radial data;
- `get_proatomic_density_profile()` and `get_proatomic_density()` for scalar
  positive-region log-log evaluation;
- `estimate_proatomic_boundary()` for the stable default divider;
- `estimate_promolecular_density_minimum()` for the optional cutoff-bounded,
  resolution-limited minimum proxy;
- `estimate_ias_position()` for explicit mode dispatch;
- `IASPositionResult` for coordinates, statuses, cutoff/search diagnostics,
  units, and provenance.

See the [proatomic-density guide](../guide/proatomic_density.md) for source
identity, units, the 20-bohr range, fixed cutoff, mode selection, statuses, and
limitations.

::: atomref.proatoms
