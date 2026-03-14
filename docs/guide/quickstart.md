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
