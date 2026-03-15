# Development plan

## Current status (implemented in the `0.1.x` line)

- stable element metadata
- curated covalent, van der Waals, and atomic-radius support datasets
- explicit provenance and coverage metadata
- generic value-policy core plus radii and X–H convenience wrappers
- substitution and linear transfer
- custom element-indexed scalar sets
- policy-backed transfer sources
- nested-policy safeguards, transfer-depth tracking, and cycle detection
- provisional X–H support via `csd_legacy_xh_cno`, `XHPolicy`, and
  `DEFAULT_XH_POLICY`

## Planned for `0.2.x`

- broader X–H datasets and policies
- experimental plus computational support sets
- pairwise helper logic such as reference sums and normalization schemes
- restoration of incomplete experimental data from broader-support predictors

## Longer-term design ideas

- radial atomic reference functions
- simple proto-density support based on spherically averaged atomic data

## Possible future directions

- more radii sets
- uncertainty and confidence flags
- ion-specific or atom-type-specific domains
- density-derived radii and related reference transforms
