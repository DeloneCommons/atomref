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

## Pairwise estimates

Three functions expose the Stage 4 pairwise model:

```python
boundary = ar.estimate_proatomic_boundary("C", "O", 1.5, distance_unit="bohr")
minimum = ar.estimate_promolecular_density_minimum(
    "C", "O", 1.5, distance_unit="bohr"
)
same_boundary = ar.estimate_ias_position(
    "C", "O", 1.5, mode="boundary", distance_unit="bohr"
)
```

Coordinates are measured from the first atom toward the second. `boundary` is
the dispatcher default: it returns the equal-neutral-proatom divider while the
two fixed tail contours overlap, and the midpoint of their gap after they
separate. `minimum` instead returns one practically resolved minimum of the
summed promolecular line density, searched only where both components reach
the fixed `1e-4 electron/bohr^3` cutoff. Its declared spatial resolution is
`0.01 bohr`, and it never silently switches to boundary mode. For unlike
atoms, any returned primary or alternative minimum lies strictly inside that
overlap interval. Raw candidates from every executed grid pass are combined
before one position-connected resolution grouping; distinct adjacent binary64
grid points are retained. A refinement that lands on a cutoff endpoint or
nucleus is discarded; when no strict-interior valley remains, the typed result
reports `no_resolved_interior_minimum` without a coordinate.

Both functions return an immutable `IASPositionResult` containing the method,
status, units, component densities, cutoff geometry, search diagnostics, and
dataset/interpolation/numerical-contract provenance. Valid pairs for which a
mode is not scientifically applicable return a typed result with no coordinate;
missing profiles return `None`.

These are neutral-proatom estimates. Neither mode locates a molecular QTAIM
zero-flux surface or an exact molecular-density critical point. The numerical
choice and its limitations are documented in the
[IAS method-selection study](../dev/ias_method_selection.md).
