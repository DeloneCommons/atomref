<!-- This file is generated from the matching notebook. -->
<!-- Regenerate with: python tools/export_notebooks.py -->
[Open the original notebook on GitHub](https://github.com/DeloneCommons/atomref/blob/main/notebooks/01-quickstart.ipynb)
# atomref quickstart

This notebook covers the main public API in v0.1: element helpers, direct
`get_*` calls, provenance-carrying `lookup_*` calls, and packaged dataset
discovery.
```python
import atomref as ar

print(ar.get_element('Cl'))
print(ar.list_quantities())
```
**Output**
```text
Element(z=17, symbol='Cl', name='Chlorine')
('covalent_radius', 'van_der_waals_radius', 'atomic_radius', 'xh_bond_length')
```
```python
r_c = ar.get_covalent_radius('C')
r_vdw = ar.get_vdw_radius('O')
print(r_c)
print(r_vdw)
assert r_c == 0.76
assert r_vdw == 1.50
```
**Output**
```text
0.76
1.5
```
```python
lookup = ar.lookup_vdw_radius('Pm')
print(f"{lookup.value:.12f}")
print(lookup.source)
print(lookup.resolved_from)
assert lookup.source == 'transfer_linear'
```
**Output**
```text
2.897226539515
transfer_linear
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
```
```python
quantity = ar.get_quantity_info('atomic_radius')
print(quantity.quantity, quantity.domain, quantity.units)

for info in ar.list_dataset_infos('van_der_waals_radius', usage_role='target'):
    print(info.ref.set_id, info.name, info.usage_role)
```
**Output**
```text
atomic_radius element angstrom
bondi1964 Bondi van der Waals radii target
rowland_taylor1996 Rowland & Taylor nonbonded contact radii target
alvarez2013 Alvarez van der Waals radii target
chernyshov2020 Chernyshov LoS van der Waals radii target
```
```python
vdw = ar.get_radii_set('van_der_waals', 'alvarez2013')
print(vdw.get('O'))

support = ar.get_builtin_set(ar.DatasetRef('atomic_radius', 'rahm2016'))
print(support.get('Pm'))
```
**Output**
```text
1.5
2.83
```
