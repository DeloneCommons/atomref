# Data curation

Packaged scalar tables are CSV files indexed by atomic number. The neutral
radial dataset is a shared-grid CSV payload inside a deterministic single-file
ZIP. Dataset metadata, storage declarations, provenance, aliases, coverage, and
attribution live in `src/atomref/data/registry.json`.

Generated scientific data must not be hand-edited.

## Classification

The registry keeps several concerns separate:

- `quantity` — the operational lookup target, such as `covalent_radius` or
  `proatomic_density`;
- `semantic_class` — what the dataset scientifically represents;
- `origin_class` — how its values were obtained;
- `usage_role` — whether it is a direct target or transfer support;
- `phase_context` — the physical context of the values;
- `storage.kind` — the validated packaged payload shape.

This is why `atomic_radius:rahm2016` remains an isolated-atom isodensity dataset
even when a radii policy uses it as support for a fitted van der Waals value.

## Neutral proatomic snapshot

`proatomic_density:pbe0_sfx2c_dyallv4z_h-lr_neutral_v2` is a deterministic
consumer snapshot of `atomref-proatoms` 2.0.0 dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`. It selects the neutral H–Lr profiles,
retains the source grid through the first point above 20 bohr so the public
endpoint remains bracketed, and does not interpolate or alter stored density
values during curation.

The registry records the upstream release and dataset identity, PBE0/spherical
fractional-occupation UKS/sf-X2C/dyall-v4z method summary, source and basis
hashes, public domain and interpolation contract, CC BY 4.0 data license, and
the concept and version-specific Zenodo DOIs. Package code remains under its
own LGPL license.

The maintainer-only builder reads a separately obtained immutable upstream
source tree; `atomref-proatoms` is not a runtime or build dependency:

```bash
python tools/build_proatomic_density_snapshot.py \
  --source-dir ../atomref-proatoms-reference-v2.0.0/upstream/data/profiles/pbe0_sfx2c_dyallv4z_h-lr_spherical_v2 \
  --check
```

Write mode is reserved for deliberate snapshot regeneration after a separately
reviewed data change. It is not part of ordinary documentation or release
builds.

## Validation

Run the registry validator after any metadata or payload change:

```bash
python tools/check_registry.py
```

It cross-checks metadata against every scalar and radial payload. Distribution
validation independently checks required members, attribution markers, and the
exact outer ZIP and inner CSV fingerprints in both source and wheel artifacts.
