# atomref development plan

> **Status:** No active near-term development plan  
> **Plan lifecycle state:** `CLOSED`  
> **Current completed development line:** `atomref 0.2.1`  
> **Scientific data source:** `atomref-proatoms 2.0.0`, dataset `pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`

## 1. Current state

The `0.2.x` development cycle is complete. Its scientific implementation,
documentation, notebooks, packaging, and release preparation have been
independently reviewed and accepted.

`atomref` is now a small, dependency-free-core package providing cited atomic
reference data and frozen spherical free-atom electron densities for
crystallographic, quantum-chemical, and molecular-structure algorithms.

The completed package scope includes:

- scalar radii and X–H reference data with explicit provenance and policy
  behavior;
- generic discovery and loading of packaged scalar and radial datasets;
- neutral spherical proatomic-density profiles for H–Lr;
- scalar density evaluation over the documented `0–20 bohr` domain;
- a stable neutral-proatom boundary estimate;
- an optional resolution-limited promolecular line-density minimum;
- complete public API documentation, adoption-oriented user documentation,
  directly rendered notebooks, and validated release artifacts.

There is currently **no active implementation stage, scheduled feature release,
or close-term roadmap**. Routine maintenance may address confirmed defects,
compatibility problems, documentation corrections, packaging issues, or
security concerns. Any substantial feature requires a new, separately reviewed
development plan.

Completed `0.2.x` implementation history belongs in the changelog, Git history,
release records, documentation, and tests rather than in this file.

## 2. Durable project constraints

Future work should preserve the following principles unless the repository owner
explicitly approves a revised contract:

- Keep the core runtime pure Python, without required third-party dependencies
  or runtime network access.
- Preserve explicit dataset identity, provenance, licensing, units, supported
  ranges, and charge/state scope.
- Do not silently substitute elements, correlate missing profiles, infer ionic
  states, or apply scalar fallback/transfer policies to radial profiles.
- Keep packaged datasets integrated through the existing registry and
  `get_builtin_set()` machinery rather than adding unrelated loading paths.
- Preserve the distinction between the stable proatomic-boundary mode and the
  optional promolecular-minimum mode. Neither should be represented as an exact
  molecular QTAIM boundary or critical point.
- Avoid speculative frameworks and abstractions. Add dependencies, public
  objects, files, or architectural layers only when required by demonstrated
  use cases.
- Preserve scientific and numerical behavior across documentation, packaging,
  and maintenance-only releases unless a confirmed defect is documented and
  protected by regression tests.
- Keep `docs/index.md` as the source of `README.md`, maintain one source for each
  notebook, and continue validating installed wheel and source-distribution
  contents.

## 3. Current known scope limits

The present implementation is intentionally limited:

- proatomic profiles are neutral, spherical reference densities for H–Lr;
- scalar profile evaluation is supported only within `0–20 bohr`;
- no ionic, fractional-charge, environment-dependent, or self-consistent
  stockholder model is provided;
- pairwise boundary and minimum results are reference-atom proxies, not
  molecular-density QTAIM results;
- no vectorized array API, three-dimensional density-grid generator, periodic
  image summation, or molecular-density construction is included;
- X–H support retains its documented dataset and parent-element limitations.

These are accepted scope boundaries, not active defects.

## 4. Possible future directions

The following ideas are non-binding. They do not authorize implementation and
have no assigned order, milestone, or version.

### Atomic data and states

- Add ionic proatomic datasets with an evidence-based, explicit state-selection
  design.
- Add further scalar or radial atomic reference properties when a concrete
  downstream use case and suitable source data exist.
- Support user-supplied radial datasets while preserving the same metadata,
  validation, and evaluation contracts.

### Numerical and spatial APIs

- Add optional NumPy-based vectorized profile evaluation if profiling and real
  workloads justify it.
- Generate single-atom and promolecular densities on three-dimensional grids.
- Design nonperiodic and periodic grid support together, including triclinic
  cells, explicit units, memory/chunking policy, and correct periodic-image
  enumeration.
- Add lightweight stockholder-initialization or common crystallographic-grid
  helpers where they provide clear interoperability value.

### Scientific validation

- Build a curated molecular-density/QTAIM benchmark comparing midpoint,
  equal-proatom boundary, and promolecular-minimum coordinates.
- Reassess cutoff and practical-resolution policies only from benchmark
  evidence, without silently changing established semantics.
- Optimize repeated pair evaluation only after downstream profiling identifies
  a meaningful bottleneck.

### Maintenance and engineering

- Introduce static type checking or small internal cleanups when they provide
  clear maintenance value.
- Strengthen mixed-license and artifact validation as additional datasets are
  added.
- Revisit registry or storage abstractions only when a new real data family
  cannot be represented cleanly by the current design.

## 5. Starting future development

Before implementing any direction above:

1. Select one concrete problem and document the user or scientific need.
2. Define the data source, provenance, scientific meaning, supported domain,
   public API, compatibility constraints, dependencies, and explicit
   exclusions.
3. Prepare a small staged plan with acceptance tests and release criteria.
4. Review and approve that plan before coding.
5. Mark the new plan `ACTIVE`; until then, this file remains a closed,
   non-actionable roadmap.

Do not interpret the possible directions in this file as committed work or as
permission to begin implementation.
