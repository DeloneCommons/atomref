# Non-goals

`atomref` is intentionally narrow.

It is **not** trying to be:

- a general periodic-table encyclopedia,
- a home for arbitrary atomic or chemical properties,
- a structure parser,
- a crystallographic symmetry package,
- a structure-inference engine,
- a Voronoi / tessellation library,
- an environment-specific chemistry model,
- a machine-learning framework for extrapolating unseen chemistry.

The package is about **curated reference data and explicit lookup policies**.
That includes provenance, transfer from broader support datasets, and stable API
surfaces that higher-level scientific code can rely on.

Future versions may widen the range of supported *reference-data families* — for
example X–H distances or radial atomic reference functions — but the package
should still remain a small reference-data layer rather than a full chemistry
platform.
