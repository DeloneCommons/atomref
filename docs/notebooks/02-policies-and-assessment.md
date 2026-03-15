<!-- This file is generated from the matching notebook. -->
<!-- Regenerate with: python tools/export_notebooks.py -->
[Open the original notebook on GitHub](https://github.com/DeloneCommons/atomref/blob/main/notebooks/02-policies-and-assessment.ipynb)
# Policies and assessment

This notebook shows how `atomref` resolves missing values through ordered
policy steps and how to inspect policy-level behavior.
```python
import atomref as ar
```
```python
covalent_policy = ar.RadiiPolicy(
    kind='covalent',
    base_set='cordero2008',
    transfers=(
        ar.SubstitutionTransfer(
            source=ar.DatasetRef('covalent_radius', 'csd_legacy_cov')
        ),
    ),
)
lookup = ar.lookup_covalent_radius('Bk', policy=covalent_policy)
print(lookup.source)
print(f"{lookup.value:.12f}")
print(lookup.resolved_from)
```
**Output**
```text
transfer_substitution
1.540000000000
(DatasetRef(quantity='covalent_radius', set_id='csd_legacy_cov'),)
```
```python
vdw_policy = ar.RadiiPolicy(
    kind='van_der_waals',
    base_set='alvarez2013',
    transfers=(
        ar.LinearTransfer(
            predictors=(ar.DatasetRef('atomic_radius', 'rahm2016'),)
        ),
    ),
)
lookup = ar.lookup_vdw_radius('Pm', policy=vdw_policy)
print(f"{lookup.value:.12f}")
print(lookup.source)
print(
    f"slope={lookup.fit.coefficients[0]:.12f} intercept={lookup.fit.intercept:.12f} n={lookup.fit.n_points}"
)
```
**Output**
```text
2.897226539515
transfer_linear
slope=1.135336645553 intercept=-0.315776167399 n=90
```
```python
assessment = ar.assess_radii_policy(
    ['C', 'Xe', 'Pm', 'Bk'],
    policy=vdw_policy,
    detail=True,
)
print(assessment.n_base, assessment.n_transfer_linear, assessment.n_missing)
for row in assessment.per_element:
    value = 'None' if row.lookup.value is None else f"{row.lookup.value:.12f}"
    print(row.symbol, row.lookup.source, value)
```
**Output**
```text
3 1 0
C base 1.770000000000
Xe base 2.060000000000
Pm transfer_linear 2.897226539515
Bk base 3.400000000000
```
