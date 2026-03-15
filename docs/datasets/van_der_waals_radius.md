# van der Waals radius

The van der Waals quantity intentionally includes several target sets with
different scientific backgrounds. This lets users choose between a classic
historical compilation, structural contact-derived sets, and compatibility-only
legacy tables.

## Bondi van der Waals radii (`bondi1964`)

A classic historical reference set compiled from mixed experimental sources.

- **What it is:** the traditional Bondi vdW table used throughout chemistry.
- **Coverage:** limited, especially for transition metals and heavier elements.
- **Why you might use it:** historical consistency or comparison with older
  literature and software defaults.

## Rowland & Taylor nonbonded-contact radii (`rowland_taylor1996`)

A small but influential structural set derived from organic-crystal nonbonded
contacts.

- **What it is:** a condensed-phase structural vdW set focused on common organic
  elements.
- **Coverage:** intentionally narrow.
- **Why you might use it:** organic-crystal contact analysis and comparisons to
  classic contact-distance literature.

## Alvarez van der Waals radii (`alvarez2013`)

This is the main van der Waals target set in the current release line.

- **What it is:** a broad structural vdW set derived from statistical analysis
  of many interatomic distances in the Cambridge Structural Database.
- **Coverage:** broad, but still incomplete for some elements.
- **Why you might use it:** it is a strong default for general condensed-phase
  geometry and contact work.
- **How `atomref` uses it:** direct target set for vdW lookup, with missing
  values restored from support data when requested by policy.

## Chernyshov line-of-sight vdW radii (`chernyshov2020`)

A reduced element-wise view of a more atom-type-aware structural analysis.

- **What it is:** vdW radii inferred from line-of-sight contact classification.
- **Coverage:** focused on elements common in molecular crystals.
- **Why you might use it:** you want a contact-derived set informed by the LoS
  idea while still using a simple element-wise API.

## Legacy CSD van der Waals radii (`csd_legacy_vdw`)

A compatibility-oriented table used historically in CSD tools.

- **What it is:** an older practical vdW table with placeholder conventions.
- **Coverage:** broad practical coverage, but not a modern scientific target
  set.
- **How `atomref` uses it:** support-only data for legacy compatibility and
  future migration work.
