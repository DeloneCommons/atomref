# Proatomic density

`atomref` supplies frozen neutral spherical proatomic-density profiles for H
through Lr. They come from the `atomref-proatoms` 2.0.0 dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`: PBE0, self-consistent spherical
fractional-occupation UKS, spin-free one-electron X2C, and the dyall-v4z basis.
The exact dataset metadata, source hashes, CC BY 4.0 attribution, and DOIs are
available through `get_proatomic_density_set_info()`.

Evaluate one scalar coordinate at a time:

```python
import atomref as ar

rho = ar.get_proatomic_density(
    "O",
    0.75,
    radius_unit="angstrom",
    density_unit="electron/bohr^3",
)

profile = ar.get_proatomic_density_profile("O")
rho_at_1_5_bohr = profile(1.5, radius_unit="bohr")
```

Radius and density units are independent. Radius coordinates accept `angstrom`
(the default) or `bohr`; density output accepts `electron/bohr^3` (the default)
or `electron/angstrom^3`.

The supported public interval is exactly 0 through 20 bohr, inclusive. The
stored snapshot retains one source point above 20 bohr only to bracket the
endpoint. Between positive stored knots, evaluation uses the dependency-free
`loglog_positive_bracketed_v1` contract: linear interpolation in `log(r)` and
`log(rho)`. Exact knots return their stored values. At zero and below the first
finite grid point, the first stored density is returned; this is a finite-grid
convention, not an exact evaluation at the nucleus. Negative, non-finite, and
above-domain radii raise `ValueError`; there is no extrapolation or zero fill.

Elements may be supplied as symbols or integer atomic numbers. Symbols follow
the package's normal element handling, and `D` and `T` use H's electronic
profile. Invalid values and elements beyond Lr return `None`; no neighboring-
element substitution, correlation, ionic selection, or scalar `ValuePolicy` is
applied.

The ZIP snapshot loads lazily through `get_builtin_set()`. Loaded sets, shared
grids, stored values, and cached profile views are immutable. This API describes
method-, basis-, state-, and sphericalization-defined isolated-atom references,
not unique basis-independent atomic observables or molecular densities.
