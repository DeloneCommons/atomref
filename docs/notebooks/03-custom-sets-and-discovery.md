<!-- This file is generated from the matching notebook. -->
<!-- Regenerate with: python tools/export_notebooks.py -->
[Open the original notebook on GitHub](https://github.com/DeloneCommons/atomref/blob/main/notebooks/03-custom-sets-and-discovery.ipynb)
# Custom sets and dataset discovery

This notebook shows how to define a small user-provided set, plug it into a
policy, and inspect the packaged dataset catalog.
```python
import atomref as ar
```
```python
custom_cov = ar.ElementScalarSet.from_mapping(
    ref=ar.DatasetRef("covalent_radius", "demo_user_cov"),
    values={"C": 0.77, "O": 0.67},
    name="Demo user covalent set",
    units="angstrom",
    description="Example custom set for notebook usage.",
    notes=("Notebook example",),
)

policy = ar.RadiiPolicy(
    kind="covalent",
    base_set=custom_cov,
    transfers=(
        ar.SubstitutionTransfer(
            source=ar.DatasetRef("covalent_radius", "cordero2008")
        ),
    ),
)

for symbol in ("C", "O", "N"):
    print(symbol, ar.lookup_covalent_radius(symbol, policy=policy))
```
**Output**
```text
C LookupResult(value=0.77, source='base', target=DatasetRef(quantity='covalent_radius', set_id='demo_user_cov'), resolved_from=(DatasetRef(quantity='covalent_radius', set_id='demo_user_cov'),), is_placeholder=False, fit=None, notes=(), transfer_depth=0)
O LookupResult(value=0.67, source='base', target=DatasetRef(quantity='covalent_radius', set_id='demo_user_cov'), resolved_from=(DatasetRef(quantity='covalent_radius', set_id='demo_user_cov'),), is_placeholder=False, fit=None, notes=(), transfer_depth=0)
N LookupResult(value=0.71, source='transfer_substitution', target=DatasetRef(quantity='covalent_radius', set_id='demo_user_cov'), resolved_from=(DatasetRef(quantity='covalent_radius', set_id='cordero2008'),), is_placeholder=False, fit=None, notes=('missing in base set; substituted from transfer source',), transfer_depth=1)
```
```python
for info in ar.list_radii_set_infos("van_der_waals", usage_role="target"):
    print(info.ref.set_id, info.semantic_class, info.origin_class, info.phase_context)

rahm = ar.get_dataset_info(ar.DatasetRef("atomic_radius", "rahm2016"))
print(rahm.name)
print(rahm.semantic_class, rahm.phase_context, rahm.usage_role)
```
**Output**
```text
bondi1964 vdw_compiled compiled_experimental mixed_or_legacy
rowland_taylor1996 vdw_structural structural condensed_phase
alvarez2013 vdw_structural structural condensed_phase
chernyshov2020 vdw_structural_typed_reduced structural condensed_phase
Rahm isodensity atomic radii (ρ=0.001 e/bohr³)
atomic_isodensity isolated_atom support
```
