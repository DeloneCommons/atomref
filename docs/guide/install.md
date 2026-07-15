# Install

## Lightweight runtime

Install the dependency-free runtime for radii, X–H, density, registry, policy,
and pairwise APIs:

```bash
pip install atomref
```

`atomref` requires Python 3.10 or later. The `0.2.1` CI matrix covers Python
3.10 through 3.14. Its required runtime dependency set is empty; every core
calculation uses the Python standard library and packaged data.

Verify the installation with a useful result:

```bash
python -c "import atomref as ar; print(ar.get_covalent_radius('C'))"
```

## Notebook tooling

Install the direct notebook renderer, standard Jupyter execution support,
kernel, and plotting dependency with:

```bash
pip install "atomref[notebooks]"
```

The plural `notebooks` name describes the shipped notebook collection and does
not imply installation of the Jupyter Notebook server application. This extra
is needed to execute or render the committed `.ipynb` examples locally. It is
not needed to use any `atomref` runtime API or to read the rendered notebooks on
the documentation site.

## Complete optional environment

Install every optional dependency declared by the project with:

```bash
pip install "atomref[all]"
```

In `0.2.1`, `all` is the exact deduplicated union of `test`, `notebooks`,
`docs`, and `dev`. It therefore includes notebook tooling, documentation
tooling, pytest, linting, build, and distribution-validation dependencies. The
base package remains dependency-free.

## Contributor environment

For a complete editable repository environment, use:

```bash
pip install -e ".[all]"
```

Install a narrower group when only one task is needed:

- `test` provides pytest and the Python 3.10 TOML compatibility dependency.
- `notebooks` provides notebook rendering and execution, a Python kernel, and
  plotting.
- `docs` provides MkDocs, Material, and typed API-documentation tooling.
- `dev` provides lint, build, and distribution-metadata checks.

Run the full local release validation with:

```bash
python tools/release_check.py
```

That command requires a clean worktree, builds fresh artifacts from a temporary
extraction of the committed `HEAD` with conventional file modes, and validates
clean base, `notebooks`, and `all` installations in temporary virtual
environments.
