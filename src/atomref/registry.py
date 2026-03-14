"""Dataset registry and packaged element-scalar set loading."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import csv
import json
from functools import lru_cache
from importlib import resources

from .elements import canonicalize_element_symbol, get_element, iter_elements
from .errors import DatasetError

QuantityId = str
DomainId = str


@dataclass(frozen=True, slots=True)
class DatasetRef:
    quantity: QuantityId
    set_id: str


@dataclass(frozen=True, slots=True)
class Reference:
    authors: str | None = None
    year: int | None = None
    title: str | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    publisher: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class CoverageInfo:
    n_values: int
    z_min: int | None = None
    z_max: int | None = None
    has_placeholders: bool = False
    covered_z: tuple[int, ...] = ()
    missing_z: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class QuantityInfo:
    quantity: QuantityId
    domain: DomainId
    units: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    ref: DatasetRef
    domain: DomainId
    units: str | None
    name: str
    description: str | None = None
    usage_role: str | None = None
    semantic_class: str | None = None
    origin_class: str | None = None
    phase_context: str | None = None
    method_summary: str | None = None
    placeholder_value: float | None = None
    extraction_source: str | None = None
    aliases: tuple[str, ...] = ()
    references: tuple[Reference, ...] = ()
    notes: tuple[str, ...] = ()
    storage: Mapping[str, object] | None = None
    coverage: CoverageInfo | None = None


@dataclass(frozen=True, slots=True)
class ElementScalarSet:
    ref: DatasetRef
    info: DatasetInfo
    values_by_z: tuple[float | None, ...]

    @classmethod
    def from_mapping(
        cls,
        *,
        ref: DatasetRef,
        values: Mapping[str, float | None],
        name: str,
        units: str | None,
        description: str | None = None,
        usage_role: str = "user",
        semantic_class: str = "user",
        origin_class: str = "user",
        phase_context: str | None = None,
        references: Iterable[Reference] = (),
        notes: Iterable[str] = (),
        placeholder_value: float | None = None,
    ) -> "ElementScalarSet":
        n_z = max(e.z for e in iter_elements())
        values_by_z: list[float | None] = [None] * (n_z + 1)

        for key, value in values.items():
            sym = _normalize_element_domain_symbol(key)
            elem = get_element(sym)
            if elem is None:
                raise DatasetError(f"invalid element symbol in custom set: {key!r}")
            values_by_z[elem.z] = None if value is None else float(value)

        covered_z = tuple(
            z for z, value in enumerate(values_by_z) if z > 0 and value is not None
        )
        has_placeholders = False
        if placeholder_value is not None:
            has_placeholders = any(
                value is not None and abs(value - placeholder_value) < 1e-12
                for value in values_by_z[1:]
            )

        info = DatasetInfo(
            ref=ref,
            domain="element",
            units=units,
            name=name,
            description=description,
            usage_role=usage_role,
            semantic_class=semantic_class,
            origin_class=origin_class,
            phase_context=phase_context,
            placeholder_value=placeholder_value,
            aliases=(),
            references=tuple(references),
            notes=tuple(notes),
            storage=None,
            coverage=CoverageInfo(
                n_values=len(covered_z),
                z_min=min(covered_z) if covered_z else None,
                z_max=max(covered_z) if covered_z else None,
                has_placeholders=has_placeholders,
                covered_z=covered_z,
                missing_z=tuple(z for z in range(1, n_z + 1) if values_by_z[z] is None),
            ),
        )
        return cls(ref=ref, info=info, values_by_z=tuple(values_by_z))

    def get(self, symbol: str | None) -> float | None:
        sym = _normalize_element_domain_symbol(symbol)
        elem = get_element(sym)
        if elem is None:
            return None
        return self.values_by_z[elem.z]


DatasetLike = DatasetRef | ElementScalarSet


def _normalize_element_domain_symbol(symbol: str | None) -> str | None:
    cand = canonicalize_element_symbol(symbol)
    if cand in {"D", "T"}:
        return "H"
    return cand


@lru_cache(maxsize=1)
def _load_registry_json() -> dict[str, object]:
    path = resources.files("atomref.data").joinpath("registry.json")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise DatasetError("invalid registry.json: expected JSON object")
    return data


def _get_quantities_mapping() -> Mapping[str, object]:
    quantities = _load_registry_json().get("quantities")
    if not isinstance(quantities, dict):
        raise DatasetError("invalid registry.json: missing quantities mapping")
    return quantities


def _get_datasets_mapping() -> Mapping[str, object]:
    datasets = _load_registry_json().get("datasets")
    if not isinstance(datasets, dict):
        raise DatasetError("invalid registry.json: missing datasets mapping")
    return datasets


def _datasets_for_quantity(quantity: QuantityId) -> Mapping[str, object]:
    datasets = _get_datasets_mapping().get(quantity)
    if not isinstance(datasets, dict):
        raise DatasetError(f"unknown quantity: {quantity!r}")
    return datasets


def list_quantities() -> tuple[str, ...]:
    return tuple(_get_quantities_mapping().keys())


def get_quantity_info(quantity: QuantityId) -> QuantityInfo:
    raw = _get_quantities_mapping().get(quantity)
    if not isinstance(raw, dict):
        raise DatasetError(f"unknown quantity: {quantity!r}")
    domain = raw.get("domain") if isinstance(raw.get("domain"), str) else None
    if domain is None:
        raise DatasetError(f"missing domain for quantity: {quantity!r}")
    units = raw.get("units") if isinstance(raw.get("units"), str) else None
    description = (
        raw.get("description") if isinstance(raw.get("description"), str) else None
    )
    return QuantityInfo(
        quantity=quantity, domain=domain, units=units, description=description
    )


def _canonicalize_alias_token(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _resolve_set_id(quantity: QuantityId, set_id: str) -> str:
    by_quantity = _datasets_for_quantity(quantity)
    if set_id in by_quantity:
        return set_id

    wanted = _canonicalize_alias_token(set_id)
    for actual_id, raw_entry in by_quantity.items():
        if _canonicalize_alias_token(actual_id) == wanted:
            return actual_id
        if isinstance(raw_entry, dict):
            aliases = raw_entry.get("aliases", ())
            if isinstance(aliases, list):
                for alias in aliases:
                    if (
                        isinstance(alias, str)
                        and _canonicalize_alias_token(alias) == wanted
                    ):
                        return actual_id
    raise DatasetError(f"unknown dataset id for {quantity!r}: {set_id!r}")


def list_dataset_ids(
    quantity: QuantityId, *, usage_role: str | None = None
) -> tuple[str, ...]:
    dataset_ids = tuple(_datasets_for_quantity(quantity).keys())
    if usage_role is None:
        return dataset_ids

    filtered: list[str] = []
    wanted = usage_role.strip().lower()
    for set_id in dataset_ids:
        info = get_dataset_info(DatasetRef(quantity, set_id))
        role = (info.usage_role or "").strip().lower()
        if role == wanted:
            filtered.append(set_id)
    return tuple(filtered)


def list_dataset_infos(
    quantity: QuantityId, *, usage_role: str | None = None
) -> tuple[DatasetInfo, ...]:
    return tuple(
        get_dataset_info(DatasetRef(quantity, set_id))
        for set_id in list_dataset_ids(quantity, usage_role=usage_role)
    )


def _coerce_reference(obj: object) -> Reference:
    if not isinstance(obj, dict):
        raise DatasetError("invalid reference entry in registry.json")
    return Reference(
        authors=obj.get("authors") if isinstance(obj.get("authors"), str) else None,
        year=obj.get("year") if isinstance(obj.get("year"), int) else None,
        title=obj.get("title") if isinstance(obj.get("title"), str) else None,
        venue=obj.get("venue") if isinstance(obj.get("venue"), str) else None,
        doi=obj.get("doi") if isinstance(obj.get("doi"), str) else None,
        url=obj.get("url") if isinstance(obj.get("url"), str) else None,
        publisher=(
            obj.get("publisher") if isinstance(obj.get("publisher"), str) else None
        ),
        note=obj.get("note") if isinstance(obj.get("note"), str) else None,
    )


def _coerce_coverage(obj: object) -> CoverageInfo | None:
    if not isinstance(obj, dict):
        return None
    covered = obj.get("covered_z")
    missing = obj.get("missing_z")
    covered_z = tuple(int(z) for z in covered) if isinstance(covered, list) else ()
    missing_z = tuple(int(z) for z in missing) if isinstance(missing, list) else ()
    return CoverageInfo(
        n_values=int(obj["n_values"]),
        z_min=int(obj["z_min"]) if isinstance(obj.get("z_min"), int) else None,
        z_max=int(obj["z_max"]) if isinstance(obj.get("z_max"), int) else None,
        has_placeholders=bool(obj.get("has_placeholders", False)),
        covered_z=covered_z,
        missing_z=missing_z,
    )


def get_dataset_info(ref: DatasetRef) -> DatasetInfo:
    actual_set_id = _resolve_set_id(ref.quantity, ref.set_id)
    actual_ref = DatasetRef(quantity=ref.quantity, set_id=actual_set_id)

    quantities = _get_quantities_mapping()
    quantity_info = quantities.get(actual_ref.quantity)
    if not isinstance(quantity_info, dict):
        raise DatasetError(f"unknown quantity: {actual_ref.quantity!r}")

    units = (
        quantity_info.get("units")
        if isinstance(quantity_info.get("units"), str)
        else None
    )
    domain = (
        quantity_info.get("domain")
        if isinstance(quantity_info.get("domain"), str)
        else None
    )
    if domain is None:
        raise DatasetError(f"missing domain for quantity: {actual_ref.quantity!r}")

    raw_entry = _datasets_for_quantity(actual_ref.quantity).get(actual_ref.set_id)
    if not isinstance(raw_entry, dict):
        raise DatasetError(f"unknown dataset: {actual_ref}")

    refs_raw = raw_entry.get("references", [])
    references = (
        tuple(_coerce_reference(item) for item in refs_raw)
        if isinstance(refs_raw, list)
        else ()
    )
    aliases_raw = raw_entry.get("aliases", [])
    aliases = (
        tuple(item for item in aliases_raw if isinstance(item, str))
        if isinstance(aliases_raw, list)
        else ()
    )
    notes_raw = raw_entry.get("notes", [])
    notes = (
        tuple(item for item in notes_raw if isinstance(item, str))
        if isinstance(notes_raw, list)
        else ()
    )
    storage = (
        raw_entry.get("storage") if isinstance(raw_entry.get("storage"), dict) else None
    )

    return DatasetInfo(
        ref=actual_ref,
        domain=domain,
        units=units,
        name=(
            raw_entry.get("name")
            if isinstance(raw_entry.get("name"), str)
            else actual_ref.set_id
        ),
        description=(
            raw_entry.get("description")
            if isinstance(raw_entry.get("description"), str)
            else None
        ),
        usage_role=(
            raw_entry.get("usage_role")
            if isinstance(raw_entry.get("usage_role"), str)
            else None
        ),
        semantic_class=(
            raw_entry.get("semantic_class")
            if isinstance(raw_entry.get("semantic_class"), str)
            else None
        ),
        origin_class=(
            raw_entry.get("origin_class")
            if isinstance(raw_entry.get("origin_class"), str)
            else None
        ),
        phase_context=(
            raw_entry.get("phase_context")
            if isinstance(raw_entry.get("phase_context"), str)
            else None
        ),
        method_summary=(
            raw_entry.get("method_summary")
            if isinstance(raw_entry.get("method_summary"), str)
            else None
        ),
        placeholder_value=(
            float(raw_entry["placeholder_value"])
            if raw_entry.get("placeholder_value") is not None
            else None
        ),
        extraction_source=(
            raw_entry.get("extraction_source")
            if isinstance(raw_entry.get("extraction_source"), str)
            else None
        ),
        aliases=aliases,
        references=references,
        notes=notes,
        storage=storage,
        coverage=_coerce_coverage(raw_entry.get("coverage")),
    )


@lru_cache(maxsize=None)
def _load_csv_columns(filename: str) -> dict[str, tuple[float | None, ...]]:
    path = resources.files("atomref.data").joinpath(filename)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "z" not in reader.fieldnames:
            raise DatasetError(f"invalid CSV file: {filename!r}")
        columns = [name for name in reader.fieldnames if name != "z"]
        values: dict[str, list[float | None]] = {name: [None] * 119 for name in columns}
        for row in reader:
            z_text = row.get("z")
            if z_text is None:
                continue
            z = int(z_text)
            for name in columns:
                raw = row.get(name)
                if raw is None:
                    values[name][z] = None
                    continue
                raw = raw.strip()
                values[name][z] = float(raw) if raw else None
    return {name: tuple(vals) for name, vals in values.items()}


@lru_cache(maxsize=None)
def get_builtin_set(ref: DatasetRef) -> ElementScalarSet:
    info = get_dataset_info(ref)
    if info.domain != "element":
        raise DatasetError(
            f"only element-domain datasets are supported in v0.1: {info.ref!r}"
        )
    if not isinstance(info.storage, Mapping):
        raise DatasetError(f"missing storage metadata for dataset: {info.ref!r}")

    filename = info.storage.get("filename")
    column = info.storage.get("column")
    if not isinstance(filename, str) or not isinstance(column, str):
        raise DatasetError(f"invalid storage metadata for dataset: {info.ref!r}")

    table = _load_csv_columns(filename)
    if column not in table:
        raise DatasetError(f"column {column!r} not found in {filename!r}")

    return ElementScalarSet(ref=info.ref, info=info, values_by_z=table[column])


def resolve_dataset_like(dataset: DatasetLike) -> ElementScalarSet:
    if isinstance(dataset, ElementScalarSet):
        return dataset
    return get_builtin_set(dataset)


def _is_placeholder_value(info: DatasetInfo, value: float) -> bool:
    if info.placeholder_value is None:
        return False
    return abs(value - info.placeholder_value) < 1e-12
