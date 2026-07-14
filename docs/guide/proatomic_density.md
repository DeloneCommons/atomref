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
`log(rho)`. Exact knots return their stored values. Over `0 <= r <=` the first
positive stored radius, the first stored density is returned; this is a
finite-grid convention, not an exact evaluation at the nucleus. Negative,
non-finite, and above-domain radii raise `ValueError`; there is no extrapolation
or zero fill.

Elements may be supplied as symbols or integer atomic numbers. Symbols follow
the package's normal element handling, and `D` and `T` use H's electronic
profile. Invalid values and elements beyond Lr return `None`; no neighboring-
element substitution, correlation, ionic selection, or scalar `ValuePolicy` is
applied.

The ZIP snapshot loads lazily through `get_builtin_set()`. Loaded sets, shared
grids, stored values, and cached profile views are immutable. This API describes
method-, basis-, state-, and sphericalization-defined isolated-atom references,
not unique basis-independent atomic observables or molecular densities.

The metadata names the immutable source as `atomref-proatoms` 2.0.0, dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`, and records the source profile,
metadata, and basis hashes. The imported profile data are CC BY 4.0; package
code has its own license. Use `get_proatomic_density_set_info()` to retain this
provenance in downstream work.

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

Pair distances must satisfy `0 < R <= 20 bohr`; the default input unit is
angstrom. Coordinates are measured from the first atom toward the second and
are returned in the selected distance unit. Distance and density units are
independent, just as they are for profile evaluation.

Reversing atom A and atom B maps every returned primary or alternative
coordinate `x` to `R - x`, swaps A/B component fields, and relabels
`dominant_atom` and its role. Method, status, total density, cutoff regime, and
orientation-independent search diagnostics remain equivalent under that
relabeling.

`boundary` is the dispatcher default and the recommended stable geometry-facing
choice. Identical atoms return exactly `R/2`. While unlike-atom cutoff contours
overlap, it returns the equal-neutral-proatom-density divider. After the
contours separate, it returns the midpoint of their low-density gap. Complete
one-atom dominance is reported without inventing a coordinate.

`minimum` is an optional, Bader-oriented neutral-promolecular proxy. It searches
for one practically resolved minimum of the summed line density only inside the
meaningful-overlap interval. That interval uses a fixed per-atom cutoff of
exactly `1e-4 electron/bohr^3`; the cutoff is a model tail policy, not a
universal interaction threshold. The declared minimum resolution is
`0.01 bohr`. The mode deliberately coalesces or rejects sub-resolution
features, may expose one competitive alternative, and never silently switches
to boundary mode. A candidate at a cutoff endpoint or nucleus is not a valid
strict-interior minimum.

## Results and diagnostic statuses

Both functions return an immutable `IASPositionResult` containing the method,
status, units, component densities, cutoff geometry, search diagnostics, and
dataset/interpolation/numerical-contract provenance. Valid pairs for which a
mode is not scientifically applicable return a typed result with no coordinate;
missing profiles return `None`.

Always inspect `method`, `status`, and `position_from_a`. The explicit statuses
are:

| Status | Meaning |
|---|---|
| `ok` | The requested mode returned its ordinary result. |
| `low_density_gap` | The fixed cutoff contours are separated; boundary mode may return the gap midpoint, while minimum mode returns no coordinate. |
| `one_atom_dominates` | No interior equal-contribution boundary exists for the unlike pair. |
| `no_resolved_interior_minimum` | Minimum mode found no strict-interior valley at its practical resolution. |
| `boundary_dominated` | A selected interior minimum exists, but an internuclear-interval boundary is lower. |
| `ambiguous_competing_minima` | A competitive resolved alternative is reported. |
| `search_unstable` | Required search passes did not agree at the declared resolution. |

`ambiguous`, `search_converged`, `search_passes`, `dominant_atom`, and the
alternative-position fields preserve the corresponding diagnostics. The result
also records the exact dataset ID, interpolation contract, cutoff density, and
pairwise numerical contract.

## Choosing a mode and understanding the limit

Use `boundary` for a stable pairwise divider in geometry, Voronoi/Laguerre
calibration, and similar reference-atom workflows. Use `minimum` only when a
cutoff-bounded promolecular line-density valley is the intended quantity and a
resolution-limited non-result is acceptable.

These are neutral-proatom estimates. Neither mode locates a molecular QTAIM
zero-flux surface or an exact molecular-density critical point. They do not add
ionic, environment-dependent, vectorized, molecular-density, or grid-density
behavior. See the executed
[feature notebook on GitHub](https://github.com/DeloneCommons/atomref/blob/main/notebooks/05-proatomic-density-and-ias.ipynb)
for the public workflows and the [IAS method-selection
study](../dev/ias_method_selection.md) for the numerical decision and archived
all-minima limitations.
