# Install

For normal use, install the runtime package:

```bash
pip install atomref
```

`atomref` is pure Python and has no required runtime dependencies outside the
standard library.

For local development, documentation work, and tests, install the editable
package together with the main extras:

```bash
pip install -e ".[test,docs,dev]"
```

Those extras currently cover:

- `test` — pytest and test-only compatibility helpers,
- `docs` — MkDocs and API documentation tooling,
- `dev` — flake8, build, and release metadata checks.
