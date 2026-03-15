# Atomic radius

The `atomic_radius` quantity exists in v0.1 to hold support datasets that are
scientifically useful but should not be presented as direct condensed-phase vdW
radii.

## Rahm isodensity atomic radii (`rahm2016`)

This is currently the only built-in atomic-radius dataset.

- **What it is:** radii for isolated neutral atoms defined by the
  ρ = 0.001 e/bohr³ electron-density isosurface.
- **Source idea:** a consistent theory-based atomic size measure derived from
  computed electron densities.
- **Coverage:** broad, but not complete for the full periodic table.
- **Why it matters here:** it correlates well with structural vdW radii and is a
  useful support baseline when a condensed-phase target set is incomplete.
- **How `atomref` uses it:** support-only dataset for linear transfer into
  target vdW values such as `alvarez2013`.

This is an important example of the package philosophy: a dataset can be very
useful algorithmically without being mislabeled as something it is not.
