# tools

This directory contains small maintenance scripts used during development and
release preparation.

## Scripts

- `check_dist.py` — verify that wheel and source-distribution artifacts contain
  the key files expected by the project.
- `check_notebooks.py` — validate notebook JSON and execute notebook code cells.
- `check_registry.py` — validate curated registry metadata against packaged CSV
  tables.
- `export_notebooks.py` — render the bundled notebooks into Markdown pages under
  `docs/notebooks/`.
- `gen_readme.py` — regenerate `README.md` from `docs/index.md`.

## Typical commands

```bash
python tools/check_registry.py
python tools/check_notebooks.py
python tools/export_notebooks.py
python tools/gen_readme.py
```

The main project README is generated from the documentation home page. To change
`README.md`, edit `docs/index.md` and then run `python tools/gen_readme.py`.
