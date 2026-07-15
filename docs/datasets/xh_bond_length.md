# X–H bond length

The `xh_bond_length` quantity intentionally covers a narrow set of reference
data.

Its purpose is not to claim a complete literature survey of X–H bond lengths.
Instead, it provides a stable, provenance-aware starting point for
hydrogen-normalisation workflows and related geometry code.

## Packaged target dataset

### CSD legacy X–H neutron-normalisation targets (`csd_legacy_xh_cno`)

- **What it is:** the fixed `C–H`, `N–H`, and `O–H` target lengths used by
  ConQuest for terminal-hydrogen normalisation.
- **Coverage:** only parent elements `C`, `N`, and `O`.
- **Values:** `C–H = 1.089 Å`, `N–H = 1.015 Å`, `O–H = 0.993 Å`.
- **Primary provenance:** the ConQuest user guide section *Hydrogen Atom
  Location in Crystal Structure Analyses*.
- **Secondary provenance:** Allen & Bruno (2010), which the ConQuest guide cites
  for these defaults.

## How `atomref` uses it

The built-in `DEFAULT_XH_POLICY` treats `csd_legacy_xh_cno` as a sparse target
set and restores missing parent elements through a fitted linear transfer from
`cordero2008` covalent radii.

That means the package draws a sharp line between:

- **curated dataset values** — currently only `C`, `N`, and `O`, and
- **policy-generated values** — inferred for other parent elements when the
  predictor policy can supply a covalent radius.

## Scope note

This is intentionally a small feature rather than a complete literature model
of X–H bonding. The documented sparse target and explicit fitted policy do not
claim broader X–H coverage or environment-specific bond lengths.
