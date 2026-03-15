# Covalent radius

The covalent-radius quantity in v0.1 is aimed at bond-detection and related
geometry workflows. It currently ships one preferred target dataset and one
legacy support dataset.

## Cordero covalent radii (`cordero2008`)

This is the main covalent-radius target set in `atomref` v0.1.

- **What it is:** a broad covalent-radius compilation based mainly on
  crystallographic bond distances.
- **Why it matters:** it is a modern, widely used reference set for element-wise
  covalent radii.
- **Coverage:** broad coverage across the periodic table, but not complete for
  every element.
- **How `atomref` uses it:** direct target dataset for covalent-radius lookup.

If you want one covalent set to start with, this is usually the right first
choice.

## Legacy CSD covalent radii (`csd_legacy_cov`)

This set reflects the older covalent radii historically used in CSD software for
bond perception.

- **What it is:** a practical, legacy-oriented bond-assignment table.
- **Why it matters:** it has long been used in chemistry software and contains
  placeholder conventions that are still relevant for compatibility work.
- **Coverage:** broad practical coverage, with explicit placeholder values for
  elements not covered by the historical table.
- **How `atomref` uses it:** support dataset for substitution when the preferred
  Cordero target set is missing a value.

Because it contains legacy placeholders, it is not the preferred scientific
starting point. It is mainly useful as a support layer and for compatibility
with older workflows.
