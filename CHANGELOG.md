# Changelog

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
