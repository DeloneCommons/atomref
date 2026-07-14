# Notebook gallery

`atomref` ships five explanatory Jupyter notebooks. These are the actual
committed `.ipynb` sources rendered directly by MkDocs—there is no generated
Markdown copy or parallel notebook tree.

Documentation builds show the committed Markdown, code, mathematics, saved
text, and saved PNG plots. They do not execute or rewrite the notebooks. A
separate release check runs temporary copies through a standard Jupyter kernel,
fails on execution exceptions, and discards the temporary outputs without
comparing them with the committed files.

## User workflows

- [Quickstart](../notebooks/01-quickstart.ipynb) introduces direct scalar
  values, provenance-carrying lookup, and dataset discovery.
- [Policies and assessment](../notebooks/02-policies-and-assessment.ipynb)
  explains ordered restoration, fitted transfers, provenance, and policy
  summaries.
- [Custom sets and discovery](../notebooks/03-custom-sets-and-discovery.ipynb)
  builds a user-provided scalar set and inspects the packaged catalog.
- [Proatomic density and IAS workflows](../notebooks/05-proatomic-density-and-ias.ipynb)
  covers profile provenance, unit-aware evaluation, both pairwise modes,
  diagnostic cases, formulas, and saved plots.

## Supporting numerical study

- [IAS method-selection study](../notebooks/04-ias-method-selection-study.ipynb)
  records the numerical evidence behind the stable boundary and practical
  minimum contracts. It is supporting information, not an alternative runtime
  implementation.

The durable scientific summary is also available in
[Pairwise boundary and IAS-proxy method selection](../dev/ias_method_selection.md).

## Notebook sources

The canonical file for every rendered page is available here for viewing or
download:

- [`01-quickstart.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/docs/notebooks/01-quickstart.ipynb)
- [`02-policies-and-assessment.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/docs/notebooks/02-policies-and-assessment.ipynb)
- [`03-custom-sets-and-discovery.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/docs/notebooks/03-custom-sets-and-discovery.ipynb)
- [`04-ias-method-selection-study.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/docs/notebooks/04-ias-method-selection-study.ipynb)
- [`05-proatomic-density-and-ias.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/docs/notebooks/05-proatomic-density-and-ias.ipynb)

## Run notebooks locally

Install all direct notebook dependencies with:

```bash
pip install "atomref[notebook]"
```

The notebooks are designed for a standard Python Jupyter kernel. Saved outputs
are examples, not a byte-for-byte reproducibility promise: timing, rendering
metadata, and PNG bytes may vary when a notebook is deliberately rerun.
