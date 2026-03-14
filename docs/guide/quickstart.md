# Quickstart

```python
import atomref as ar

print(ar.get_covalent_radius("C"))
print(ar.get_vdw_radius("O"))

m = ar.lookup_vdw_radius("Pm")
print(m.value)
print(m.source)
print(m.resolved_from)
```

Use `get_*` when you only need the number, and `lookup_*` when you need
provenance.

You can also inspect the packaged quantity layer directly:

```python
import atomref as ar

print(ar.list_quantities())
print(ar.get_quantity_info("atomic_radius"))
print(ar.list_dataset_infos("covalent_radius"))
print(ar.list_radii_set_infos("van_der_waals", usage_role="target"))
```

You can also retrieve the packaged set object directly:

```python
import atomref as ar

vdw = ar.get_radii_set("van_der_waals", "alvarez2013")
print(vdw.get("O"))

raw = ar.get_builtin_set(ar.DatasetRef("atomic_radius", "rahm2016"))
print(raw.get("Pm"))
```

Need runnable versions of these examples? See the notebooks page and the
matching notebook files in the repository:

- [`01-quickstart.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/notebooks/01-quickstart.ipynb)
- [`02-policies-and-assessment.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/notebooks/02-policies-and-assessment.ipynb)
- [`03-custom-sets-and-discovery.ipynb`](https://github.com/DeloneCommons/atomref/blob/main/notebooks/03-custom-sets-and-discovery.ipynb)
