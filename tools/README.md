# tools

This directory contains small maintenance scripts used during development and
release preparation.

## Scripts

- `build_proatomic_density_snapshot.py` — verify the pinned local
  `atomref-proatoms` 2.0.0 source and write or check the deterministic neutral
  H–Lr consumer ZIP. This is a maintainer-only tool and performs no network
  access.
- `check_dist.py` — verify that wheel and source-distribution artifacts contain
  the key files expected by the project.
- `check_notebooks.py` — validate notebook JSON and execute notebook code cells.
- `check_registry.py` — validate curated registry metadata against packaged CSV
  tables.
- `export_notebooks.py` — render the bundled notebooks into Markdown pages under
  `docs/notebooks/`.
- `gen_readme.py` — regenerate `README.md` from `docs/index.md`.
- `release_check.py` — run the full release-preparation checklist,
  including linting, tests, docs, builds, and artifact validation.

## Typical commands

```bash
python tools/check_registry.py
python tools/check_notebooks.py
python tools/export_notebooks.py
python tools/gen_readme.py
python tools/release_check.py
```

## Neutral proatomic-density snapshot

Run the snapshot builder against the immutable local reference dataset. Write
mode regenerates the packaged archive; check mode rebuilds it in memory and
requires an exact byte-for-byte match:

```bash
python tools/build_proatomic_density_snapshot.py \
  --source-dir ../atomref-proatoms-reference-v2.0.0/upstream/data/profiles/pbe0_sfx2c_dyallv4z_h-lr_spherical_v2 \
  --write

python tools/build_proatomic_density_snapshot.py \
  --source-dir ../atomref-proatoms-reference-v2.0.0/upstream/data/profiles/pbe0_sfx2c_dyallv4z_h-lr_spherical_v2 \
  --check
```

The upstream project is not an `atomref` dependency. Keep its complete source
data outside this repository and do not edit the generated ZIP by hand.

The main project README is generated from the documentation home page. To change
`README.md`, edit `docs/index.md` and then run `python tools/gen_readme.py`.
