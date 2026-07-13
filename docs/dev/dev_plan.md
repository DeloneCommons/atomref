# Development plan

The authoritative implementation plan is the root-level
[`DEV_PLAN.md`](https://github.com/DeloneCommons/atomref/blob/main/DEV_PLAN.md).
This compact page exists only for the current documentation structure and will
be removed during the planned `0.2.1` documentation cleanup.

## Current `0.2.0` direction

The accepted density work provides neutral H–Lr spherical proatomic profiles
and scalar log–log evaluation. Stage 4 now defines two explicit pairwise modes:

- a default stable proatomic boundary based on homonuclear symmetry, equal
  proatomic contributions, and a fixed low-density contour fallback;
- an optional, cutoff-bounded and resolution-limited promolecular density
  minimum for Bader-oriented comparison.

The mode-selection evidence and limitations are summarized in
[Pairwise boundary and IAS-proxy method selection](ias_method_selection.md).

Neither mode is an exact molecular-density QTAIM surface.
