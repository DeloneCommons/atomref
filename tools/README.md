# tools

This directory contains small maintenance scripts used during development and
release preparation.

## Scripts

- `build_proatomic_density_snapshot.py` — verify the pinned local
  `atomref-proatoms` 2.0.0 source and write or check the deterministic neutral
  H–Lr consumer ZIP. This is a maintainer-only tool and performs no network
  access.
- `check_dist.py` — verify wheel and source-distribution contents and optionally
  test clean base, `notebooks`, and `all` installations from the built wheel.
- `check_notebooks.py` — smoke-execute each temporary notebook copy in an
  isolated standard Jupyter child process, enforce startup, cell, and complete
  process timeouts, and discard the resulting outputs.
- `check_registry.py` — validate curated registry metadata against every
  packaged scalar and radial payload.
- `gen_readme.py` — regenerate `README.md` from `docs/index.md`.
- `release_check.py` — run the full release-preparation checklist,
  including linting, tests, docs, a clean committed-source build with
  conventional archive modes, and artifact validation.

## Typical commands

```bash
python tools/check_registry.py
python tools/check_notebooks.py
python tools/gen_readme.py
python tools/check_dist.py dist --check-installs
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
