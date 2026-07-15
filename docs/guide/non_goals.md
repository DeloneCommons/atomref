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

The package is about **curated atomic references and explicit selection or
model semantics**. That includes provenance-aware scalar lookup, transfer from
broader support datasets, frozen neutral spherical proatomic profiles, and the
two documented pairwise reference-atom modes.

The pairwise helpers are not molecular electron-density calculations or exact
QTAIM surfaces. Radial data are not completed through scalar policy,
correlation, or neighboring-element substitution.

Future versions may widen the range of supported *reference-data families*, but
the package should still remain a small reference-data layer rather than a full
chemistry platform.
