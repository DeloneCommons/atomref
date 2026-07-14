# Install

## Lightweight runtime

Install the dependency-free runtime for radii, X–H, density, registry, policy,
and pairwise APIs:

```bash
pip install atomref
```

`atomref` supports Python 3.10 and later. Its required runtime dependency set is
empty; every core calculation uses the Python standard library and packaged
data.

Verify the installation with a useful result:

```bash
python -c "import atomref as ar; print(ar.get_covalent_radius('C'))"
```

## Notebook-capable installation

Install the direct notebook renderer, standard Jupyter execution support,
kernel, and plotting dependency with:

```bash
pip install "atomref[notebook]"
```

This extra is needed to run the shipped `.ipynb` examples locally. It is not
needed to use any `atomref` runtime API or to read the rendered notebooks on the
documentation site.

## All user-facing optional features

Install the union of current user-facing feature extras with:

```bash
pip install "atomref[all]"
```

In `0.2.1`, notebooks are the only optional user-facing feature, so `all` and
`notebook` intentionally contain the same dependency entries. `all` is the
stable choice for applications that want every optional user capability as new
feature extras are added later. It does not include pytest, lint, build,
upload, or release tools.

## Contributor environment

For repository development, install the editable package and the contributor
groups required by the task:

```bash
pip install -e ".[test,dev,docs,notebook]"
```

- `test` provides the test runner.
- `dev` provides lint, build, and distribution-metadata checks.
- `docs` provides MkDocs, Material, and typed API-documentation tooling.
- `notebook` provides direct notebook rendering, Jupyter execution, a Python
  kernel, and plotting.

Run the full local release-candidate validation with:

```bash
python tools/release_check.py
```

That command requires a clean worktree, builds fresh artifacts from a temporary
extraction of the committed `HEAD` with conventional file modes, and validates
clean base, `notebook`, and `all` installations in temporary virtual
environments.
