# Quickstart

The two most important user-facing ideas in `atomref` are:

- `get_*` returns only the selected number,
- `lookup_*` returns the number **and** provenance metadata.

```pycon
>>> import atomref as ar
>>> ar.get_covalent_radius("C")
0.76
>>> ar.get_vdw_radius("O")
1.5
>>> lookup = ar.lookup_vdw_radius("Pm")
>>> lookup.value
2.8972265395148358
>>> lookup.source
'transfer_linear'
>>> lookup.resolved_from
(DatasetRef(quantity='atomic_radius', set_id='rahm2016'),)
```

Use `get_*` when you only need the value. Use `lookup_*` when you want to know
whether the result came from the preferred dataset, a support dataset, a policy
override, or a fallback.

You can inspect the packaged quantity layer directly:

```pycon
>>> import atomref as ar
>>> ar.list_quantities()
('covalent_radius', 'van_der_waals_radius', 'atomic_radius')
>>> ar.get_quantity_info("atomic_radius")
QuantityInfo(quantity='atomic_radius', domain='element', units='angstrom', description='Element-indexed isolated-atom or theory-defined atomic radii used as transferable support data.')
>>> [info.ref.set_id for info in ar.list_radii_set_infos("van_der_waals", usage_role="target")]
['bondi1964', 'rowland_taylor1996', 'alvarez2013', 'chernyshov2020']
```

And you can load a packaged set object directly:

```pycon
>>> import atomref as ar
>>> vdw = ar.get_radii_set("van_der_waals", "alvarez2013")
>>> vdw.get("O")
1.5
>>> raw = ar.get_builtin_set(ar.DatasetRef("atomic_radius", "rahm2016"))
>>> raw.get("Pm")
2.83
```

For longer, runnable examples see:

- the [notebook overview](notebooks.md),
- the [quickstart notebook page](../notebooks/01-quickstart.md),
- the [policies notebook page](../notebooks/02-policies-and-assessment.md),
- the [custom sets notebook page](../notebooks/03-custom-sets-and-discovery.md).
