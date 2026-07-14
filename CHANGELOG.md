# Changelog

## 0.2.1 - 2026-07-14

### Added

- Complete structured public API documentation with rendered typed signatures,
  parameters, returns, raised errors, attributes, examples, and cross-references.
- An `all` extra that exactly mirrors the complete user-facing `notebook` extra.
- Clean built-wheel installation checks for the base package, `notebook`, and
  `all` extras.

### Changed

- Repositioned the documentation home page and generated README around rapid
  installation, first use, scientific provenance, and adoption by downstream
  structure-analysis software.
- Rendered the maintained `.ipynb` notebooks directly in MkDocs with committed
  Markdown, code, mathematics, text output, and PNG plots.
- Replaced the bespoke notebook execution/export path with one temporary
  standard-Jupyter smoke check that discards its execution results.

### Packaging

- Declared the renderer, execution client, notebook format library, kernel, and
  plotting library in both `notebook` and `all`, while keeping documentation,
  test, lint, build, and release tools out of `all`.
- Updated CI, source-distribution checks, and release preparation for the final
  single-source notebook layout and isolated artifact installations.
- Build release artifacts from a clean committed-source extraction and reject
  nonstandard executable modes on ordinary wheel and source-distribution files.
- Removed generated notebook Markdown, the custom exporter, export-sync tests,
  and the duplicate documentation copy of the development plan.

### Scientific behavior

- No density values, cutoff radii, pairwise modes, selected coordinates,
  statuses, packaged scientific data, or other numerical behavior changed.

## 0.2.0 - 2026-07-14

### Added

- A packaged, immutable neutral H–Lr spherical proatomic-density dataset derived
  reproducibly from `atomref-proatoms` 2.0.0 dataset
  `pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`, with exact source, basis, license,
  hash, and DOI metadata.
- Cached profile retrieval and dependency-free scalar density evaluation with
  independent radius and density units, positive-region log–log interpolation,
  and a strict 0–20 bohr public radius domain.
- `estimate_proatomic_boundary()` for the stable neutral-proatom divider and
  `estimate_promolecular_density_minimum()` for the optional cutoff-bounded,
  resolution-limited promolecular line-density minimum proxy.
- `estimate_ias_position()` with explicit `boundary` and `minimum` modes;
  `boundary` is the default and minimum mode never silently falls back to it.
- Immutable `IASPositionResult` values with coordinates, explicit diagnostic
  statuses, component densities, cutoff/search information, units, and
  numerical/data provenance.
- Executed method-selection and feature notebooks with saved outputs and plots.

### Changed

- `get_builtin_set()` now dispatches both scalar CSV and shared-grid radial ZIP
  datasets through the same registry machinery. Existing scalar policies,
  radii values, X–H behavior, and `0.1.x` APIs remain unchanged.
- The package now identifies itself as version `0.2.0` and includes proatomic
  density, electron density, interatomic-surface, and IAS discovery keywords.

### Documentation

- Added the neutral proatomic-density and pairwise guide, complete
  `atomref.proatoms` API reference, exact cutoff/range/unit/status guidance, and
  links to the saved release notebooks.
- Updated the home page and architecture description for radial datasets and
  the accepted two-mode pairwise API without performing the broader planned
  documentation redesign.

### Packaging

- Included the deterministic proatomic-density ZIP in wheels and source
  distributions and added independent content validation.
- Added an optional `notebook` extra for Matplotlib; runtime dependencies remain
  empty.
- Extended CI, notebook checks, distribution-content checks, release checks,
  and clean-wheel smoke tests for density evaluation, both pairwise modes, and
  dispatcher equivalence.

## 0.1.4 - 2026-03-15

### Added

- `LookupResult.transfer_depth`, which records how many transfer steps were
  involved in the returned numeric value.
- Explicit nested-policy safeguards for `LinearTransfer` via:
  - `fit_sources`
  - `fit_max_depth`
  - `prediction_sources`
  - `prediction_max_depth`
- Regression tests covering generic-policy cycles, wrapper-policy cycles,
  conservative nested-fit defaults, and explicit opt-in for deeper nested
  linear workflows.

### Changed

- Nested policy-backed linear transfers are now guarded in two phases:
  conservative defaults are used for fit training, while one additional nested
  completion step remains allowed at prediction time.
- Linear-transfer fitting now distinguishes direct predictor values from nested
  policy-derived predictor values.
- Cycle detection now tracks both generic policies and wrapper policies using a
  context-local activation stack, so recursion through freshly materialized
  wrapper policies is detected reliably and safely.
- Radii and X–H convenience helpers now resolve through wrapper-aware cycle
  tracking rather than materializing a fresh generic policy for each public
  lookup call.

### Documentation

- Expanded the transfer and policy docs to explain nested-policy safeguards,
  `transfer_depth`, and cycle detection.
- Added guidance on when chained correlations are scientifically reasonable and
  how to opt in deliberately when broader fit training is desired.

## 0.1.3 - 2026-03-15

### Added

- Support for using generic policies and wrapper policies as transfer sources in
  `SubstitutionTransfer` and `LinearTransfer`.
- Public `atomref.xh` module docs and examples for policy-backed predictor
  workflows.

### Changed

- `LinearTransfer` now treats predictors as **sources** rather than only raw
  datasets, while still keeping the current runtime to one predictor at a time.
- Generic policy resolution now supports blocked element keys, which is used by
  the X–H helper to prevent invalid `H` parent-element lookups.
- Transfer results now preserve nested-policy provenance through
  `resolved_from` and explanatory notes when a policy source is involved.

## 0.1.2 - 2026-03-15

### Added

- New `xh_bond_length` quantity family.
- Packaged provisional X–H dataset `csd_legacy_xh_cno` with ConQuest/CSD
  hydrogen-normalisation targets for `C`, `N`, and `O`.
- New `atomref.xh` convenience layer with `XHPolicy`, `DEFAULT_XH_POLICY`, set
  listing helpers, and X–H lookup helpers.

### Documentation

- Added X–H dataset and API pages.
- Documented the provisional scope of X–H support in `0.1.x` and the planned
  broader follow-up in `0.2.x`.

## 0.1.1 - 2026-03-15

### Added

- Public generic lookup helpers `lookup_value(...)` and `get_value(...)`.
- Tests for alias normalization, immutable metadata, non-finite-value rejection,
  collision detection, and explicit placeholder notes.

### Changed

- Registry metadata returned by `get_dataset_info(...)` is now frozen so callers
  cannot mutate the cached registry state.
- Dataset-alias resolution now normalizes Unicode and dash variants more
  robustly.
- Custom-set construction and policy configuration now reject normalized-key
  collisions and non-finite numeric values.
- Radii-specific wrappers now reject negative override and fallback values.
- Base and substitution lookups now emit explicit placeholder notes when the
  returned numeric value is a dataset placeholder.
- `LinearTransfer` now validates empty-predictor and invalid-`min_points`
  configurations eagerly.
- The docs now explain the distinction between quantity, domain, dataset, and
  policy, and clarify that the current runtime supports only the `element`
  domain.

## 0.1.0 - 2026-03-15

First public release.

### Added

- Packaged element metadata and curated radii tables.
- Quantity-aware registry metadata that separates operational lookup quantity
  from scientific classification and dataset usage role.
- Provenance-aware radii policies with deterministic resolution order.
- Substitution and linear-transfer support for restoring missing values from
  curated support datasets.
- Public helpers for inspecting quantities, dataset metadata, and packaged
  built-in sets.
- Runnable notebooks together with generated Markdown notebook pages in the
  documentation.
- Validation and maintenance tools for registry checks, notebook export, README
  generation, and distribution-artifact inspection.

### Documentation

- Expanded dataset guides with citations and selection-oriented descriptions.
- Added module-level API pages and notebook walkthroughs.
- Added developer-facing curation and tooling notes.

### Packaging

- Built and validated wheel and source-distribution artifacts.
- Added CI coverage for linting, tests, docs builds, notebook sync, and
  distribution checks.
