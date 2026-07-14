"""Dataset registry and packaged element-set loading."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import csv
from functools import lru_cache
from importlib import resources
import io
import json
import math
import stat
from types import MappingProxyType
import unicodedata
import zipfile
import zlib

from .elements import canonicalize_element_symbol, get_element, iter_elements
from .errors import DatasetError

QuantityId = str
"""Typing alias for a registry quantity identifier."""

DomainId = str
"""Typing alias for a registry lookup-domain identifier."""


@dataclass(frozen=True, slots=True)
class DatasetRef:
    """Stable reference to a packaged dataset.

    Attributes:
        quantity: Operational property family, such as ``"covalent_radius"``
            or ``"proatomic_density"``.
        set_id: Canonical dataset identifier or an accepted alias when the
            reference is passed to a registry lookup.

    Examples:
        >>> DatasetRef("covalent_radius", "cordero2008")
        DatasetRef(quantity='covalent_radius', set_id='cordero2008')
    """

    quantity: QuantityId
    set_id: str


@dataclass(frozen=True, slots=True)
class Reference:
    """Bibliographic record attached to packaged dataset metadata.

    Attributes:
        authors: Author string as recorded by the curated metadata.
        year: Publication year.
        title: Work title.
        venue: Journal, repository, or other publication venue.
        doi: DOI without an implied URL prefix.
        url: Source or publication URL.
        publisher: Publisher or archive name.
        note: Additional attribution or interpretation note.
    """

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
    """Coverage summary for an element-indexed dataset.

    Attributes:
        n_values: Number of non-missing element values or profiles.
        z_min: Lowest covered atomic number, or `None` for empty coverage.
        z_max: Highest covered atomic number, or `None` for empty coverage.
        has_placeholders: Whether at least one covered scalar equals the
            dataset's declared placeholder value.
        covered_z: Covered atomic numbers in increasing order.
        missing_z: Missing atomic numbers in increasing order.
    """

    n_values: int
    z_min: int | None = None
    z_max: int | None = None
    has_placeholders: bool = False
    covered_z: tuple[int, ...] = ()
    missing_z: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class QuantityInfo:
    """Metadata shared by all datasets that belong to one quantity.

    Attributes:
        quantity: Registry quantity identifier.
        domain: Lookup domain. The current resolver supports ``"element"``.
        units: Scientific units shared by the quantity, or `None` when the
            quantity is unitless or unspecified.
        description: Human-readable quantity description.
    """

    quantity: QuantityId
    domain: DomainId
    units: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    """Curated metadata for one packaged dataset.

    This object keeps operational classification such as `ref.quantity` and
    `usage_role` separate from scientific classification such as
    `semantic_class` and `phase_context`.

    Attributes:
        ref: Canonical quantity and dataset identifier.
        domain: Lookup domain, currently ``"element"`` for packaged data.
        units: Units of stored scalar values or density profiles.
        name: Human-readable dataset name.
        description: Concise scientific description.
        usage_role: Operational role such as ``"target"`` or ``"support"``.
        semantic_class: Scientific class of the values.
        origin_class: Origin category used during curation.
        phase_context: Physical phase or environment associated with values.
        method_summary: Concise computational or experimental method.
        placeholder_value: Declared scalar placeholder, if one exists.
        extraction_source: Record of the upstream extraction source.
        aliases: Accepted alternative dataset identifiers.
        references: Bibliographic and source records.
        notes: Additional immutable metadata notes.
        storage: Read-only packaged-storage description, or `None` for a custom
            in-memory set.
        coverage: Element-coverage summary, when available.
    """

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
    """Immutable element-indexed scalar dataset stored by atomic number.

    Attributes:
        ref: Dataset identity.
        info: Curated metadata, including the scientific units.
        values_by_z: Dense immutable tuple indexed by atomic number. Index zero
            is unused and missing elements contain `None`.

    Notes:
        Scalar values have the units recorded by `info.units`. Policies and
        transfers do not perform unit conversion, so custom sources combined in
        one policy must use compatible units.
    """

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
        """Build a custom element-domain dataset from a symbol-keyed mapping.

        Args:
            ref: Stable identity for the custom dataset.
            values: Element symbols mapped to finite scalar values or `None`.
                Symbols are canonicalized, and D/T map to H.
            name: Human-readable dataset name.
            units: Scientific units for every non-missing value, or `None`.
            description: Optional scientific description.
            usage_role: Operational role. Defaults to ``"user"``.
            semantic_class: Scientific classification. Defaults to ``"user"``.
            origin_class: Origin classification. Defaults to ``"user"``.
            phase_context: Optional physical phase or environment.
            references: Bibliographic records to preserve with the set.
            notes: Additional metadata notes.
            placeholder_value: Optional finite scalar used as a placeholder.

        Returns:
            A frozen [ElementScalarSet][atomref.registry.ElementScalarSet] with
            coverage metadata computed for the packaged periodic table.

        Raises:
            DatasetError: If an element key is invalid, two keys normalize to
                the same element, or a value is not finite.

        Examples:
            >>> custom = ElementScalarSet.from_mapping(
            ...     ref=DatasetRef("covalent_radius", "my_set"),
            ...     values={"C": 0.76, "O": 0.66},
            ...     name="My radii",
            ...     units="angstrom",
            ... )
            >>> custom.get("O")
            0.66
        """

        n_z = max(e.z for e in iter_elements())
        values_by_z: list[float | None] = [None] * (n_z + 1)
        seen_keys: dict[str, str] = {}

        placeholder_f = (
            None
            if placeholder_value is None
            else _coerce_finite_float(
                placeholder_value,
                what=f"placeholder value for custom dataset {ref.set_id!r}",
            )
        )

        for key, value in values.items():
            sym = _normalize_element_domain_symbol(key)
            elem = get_element(sym)
            if elem is None:
                raise DatasetError(f"invalid element symbol in custom set: {key!r}")
            previous = seen_keys.get(sym)
            if previous is not None and previous != key:
                raise DatasetError(
                    "custom-set keys "
                    f"{previous!r} and {key!r} both normalize to {sym!r}"
                )
            seen_keys[sym] = key
            values_by_z[elem.z] = (
                None
                if value is None
                else _coerce_finite_float(
                    value,
                    what=f"value for element {key!r} in custom dataset {ref.set_id!r}",
                )
            )

        covered_z = tuple(
            z for z, value in enumerate(values_by_z) if z > 0 and value is not None
        )
        has_placeholders = False
        if placeholder_f is not None:
            has_placeholders = any(
                value is not None and abs(value - placeholder_f) < 1e-12
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
            placeholder_value=placeholder_f,
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
        """Return one element's scalar value.

        Args:
            symbol: Symbol-like element token, or `None`. D/T map to H.

        Returns:
            The stored scalar in `info.units`, or `None` for an invalid or
            uncovered element.
        """

        sym = _normalize_element_domain_symbol(symbol)
        elem = get_element(sym)
        if elem is None:
            return None
        return self.values_by_z[elem.z]


@dataclass(frozen=True, slots=True)
class ElementRadialSet:
    """Immutable element-indexed radial profiles sampled on one shared grid.

    Attributes:
        ref: Dataset identity.
        info: Curated metadata and storage description.
        radii: Shared immutable radial grid in the storage-declared coordinate
            unit.
        profiles_by_z: Dense immutable tuple of profiles indexed by atomic
            number. Index zero is unused and missing profiles contain `None`.
    """

    ref: DatasetRef
    info: DatasetInfo
    radii: tuple[float, ...]
    profiles_by_z: tuple[tuple[float, ...] | None, ...]

    def get(self, element: str | int | None) -> tuple[float, ...] | None:
        """Return the immutable sampled profile for one element.

        Args:
            element: Symbol-like token, integer atomic number, or `None`. D/T
                map to H; booleans are rejected despite being integer subclasses.

        Returns:
            The stored profile in the density units described by `info`, or
            `None` for an invalid or uncovered element.
        """

        if isinstance(element, int) and not isinstance(element, bool):
            z = element
        elif isinstance(element, str) or element is None:
            sym = _normalize_element_domain_symbol(element)
            elem = get_element(sym)
            if elem is None:
                return None
            z = elem.z
        else:
            return None
        if z <= 0 or z >= len(self.profiles_by_z):
            return None
        return self.profiles_by_z[z]


BuiltinSet = ElementScalarSet | ElementRadialSet
"""Union of packaged scalar and radial dataset payloads."""

ScalarDatasetLike = DatasetRef | ElementScalarSet
"""Typing alias for packaged references and custom scalar datasets."""


_DASH_TRANSLATION = str.maketrans(
    {
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "−": "-",
    }
)


def _normalize_element_domain_symbol(symbol: str | None) -> str | None:
    """Normalize element-domain symbols and fold D/T onto hydrogen."""

    cand = canonicalize_element_symbol(symbol)
    if cand in {"D", "T"}:
        return "H"
    return cand


@lru_cache(maxsize=1)
def _load_registry_json() -> dict[str, object]:
    """Load the packaged registry JSON as a validated top-level mapping."""

    path = resources.files("atomref.data").joinpath("registry.json")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise DatasetError("invalid registry.json: expected JSON object")
    return data


def _freeze_json_like(value: object) -> object:
    """Recursively freeze JSON-like metadata structures.

    Registry metadata is cached globally. Returning raw dicts or lists from that
    cache would let callers mutate shared package state through the metadata
    objects returned by [get_dataset_info][atomref.registry.get_dataset_info].
    """

    if isinstance(value, dict):
        frozen = {str(key): _freeze_json_like(item) for key, item in value.items()}
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_freeze_json_like(item) for item in value)
    return value


def _coerce_finite_float(value: object, *, what: str) -> float:
    """Return `value` as a finite float or raise
    [DatasetError][atomref.errors.DatasetError].
    """

    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise DatasetError(f"{what} must be a finite float") from exc
    if not math.isfinite(out):
        raise DatasetError(f"{what} must be a finite float")
    return out


def _get_quantities_mapping() -> Mapping[str, object]:
    """Return the raw ``quantities`` mapping from ``registry.json``."""

    quantities = _load_registry_json().get("quantities")
    if not isinstance(quantities, dict):
        raise DatasetError("invalid registry.json: missing quantities mapping")
    return quantities


def _get_datasets_mapping() -> Mapping[str, object]:
    """Return the raw ``datasets`` mapping from ``registry.json``."""

    datasets = _load_registry_json().get("datasets")
    if not isinstance(datasets, dict):
        raise DatasetError("invalid registry.json: missing datasets mapping")
    return datasets


def _datasets_for_quantity(quantity: QuantityId) -> Mapping[str, object]:
    """Return the dataset table for one quantity or raise on unknown input."""

    datasets = _get_datasets_mapping().get(quantity)
    if not isinstance(datasets, dict):
        raise DatasetError(f"unknown quantity: {quantity!r}")
    return datasets


def list_quantities() -> tuple[str, ...]:
    """List packaged quantity identifiers in registry order.

    Returns:
        Canonical quantity identifiers in their curated registry order.

    Raises:
        DatasetError: If the packaged registry is unavailable or malformed.
    """

    return tuple(_get_quantities_mapping().keys())


def get_quantity_info(quantity: QuantityId) -> QuantityInfo:
    """Return quantity-level metadata for a packaged quantity.

    Args:
        quantity: Canonical registry quantity identifier.

    Returns:
        Immutable [QuantityInfo][atomref.registry.QuantityInfo] for the requested
        quantity.

    Raises:
        DatasetError: If the quantity is unknown or its metadata is malformed.

    Examples:
        >>> get_quantity_info("covalent_radius").units
        'angstrom'
    """

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
        quantity=quantity,
        domain=domain,
        units=units,
        description=description,
    )


def _canonicalize_alias_token(value: str) -> str:
    """Normalize a dataset id or alias for case-insensitive comparison."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.translate(_DASH_TRANSLATION)
    return " ".join(normalized.strip().lower().split())


def _resolve_set_id(quantity: QuantityId, set_id: str) -> str:
    """Resolve a dataset id or alias to its canonical packaged set id."""

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
    """List packaged dataset identifiers for a quantity.

    Args:
        quantity: Canonical registry quantity identifier.
        usage_role: Optional case-insensitive role filter, such as ``"target"``
            or ``"support"``. `None` includes every role.

    Returns:
        Canonical dataset identifiers in curated registry order.

    Raises:
        DatasetError: If the quantity is unknown or registry metadata is
            malformed.
    """

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
    """Return packaged dataset metadata objects for a quantity.

    Args:
        quantity: Canonical registry quantity identifier.
        usage_role: Optional case-insensitive role filter. `None` includes every
            role.

    Returns:
        Immutable [DatasetInfo][atomref.registry.DatasetInfo] objects in curated
        registry order.

    Raises:
        DatasetError: If the quantity is unknown or registry metadata is
            malformed.
    """

    return tuple(
        get_dataset_info(DatasetRef(quantity, set_id))
        for set_id in list_dataset_ids(quantity, usage_role=usage_role)
    )


def _coerce_reference(obj: object) -> Reference:
    """Coerce a raw registry entry into [Reference][atomref.registry.Reference]."""

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
    """Coerce raw metadata into [CoverageInfo][atomref.registry.CoverageInfo]."""

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
    """Return curated metadata for a packaged dataset reference.

    Args:
        ref: Quantity and dataset identifier. Dataset aliases are accepted with
            Unicode-dash, case, and surrounding-whitespace normalization.

    Returns:
        Immutable metadata whose `ref` contains the canonical dataset ID.

    Raises:
        DatasetError: If the quantity or dataset is unknown, or registry
            metadata is malformed.

    Examples:
        >>> info = get_dataset_info(
        ...     DatasetRef("covalent_radius", "cordero2008")
        ... )
        >>> info.units
        'angstrom'
    """

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
        _freeze_json_like(raw_entry.get("storage"))
        if isinstance(raw_entry.get("storage"), dict)
        else None
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
            _coerce_finite_float(
                raw_entry["placeholder_value"],
                what=f"placeholder value for packaged dataset {actual_ref!r}",
            )
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
        storage=storage if isinstance(storage, Mapping) else None,
        coverage=_coerce_coverage(raw_entry.get("coverage")),
    )


@lru_cache(maxsize=None)
def _load_csv_columns(filename: str) -> dict[str, tuple[float | None, ...]]:
    """Load all value columns from one packaged dense-by-Z CSV table."""

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
                values[name][z] = (
                    _coerce_finite_float(
                        raw,
                        what=f"value in {filename!r} column {name!r} for Z={z}",
                    )
                    if raw
                    else None
                )
    return {name: tuple(vals) for name, vals in values.items()}


@lru_cache(maxsize=None)
def _load_radial_csv_zip(
    filename: str,
    member: str,
    radius_column: str,
    density_columns: tuple[tuple[int, str], ...],
) -> tuple[tuple[float, ...], tuple[tuple[float, ...] | None, ...]]:
    """Load shared-grid profiles from a single-member ZIP containing CSV."""

    try:
        archive_bytes = _read_package_data_bytes(filename)
        with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
            members = archive.infolist()
            if len(members) != 1:
                raise DatasetError(
                    f"radial ZIP archive {filename!r} must contain exactly one member"
                )
            member_info = members[0]
            if member_info.is_dir():
                raise DatasetError(
                    f"radial ZIP archive {filename!r} contains a directory entry"
                )
            unix_mode = (member_info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(unix_mode)
            if (
                member_info.create_system == 3
                and file_type not in (0, stat.S_IFREG)
            ):
                raise DatasetError(
                    f"radial ZIP archive {filename!r} member is not a regular file"
                )
            if member_info.filename != member:
                raise DatasetError(
                    f"radial ZIP archive {filename!r} does not contain the declared "
                    f"member {member!r}"
                )
            if member_info.flag_bits & 0x1:
                raise DatasetError(
                    f"radial ZIP archive {filename!r} contains an encrypted member"
                )
            csv_bytes = archive.read(member_info)
    except DatasetError:
        raise
    except (
        OSError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        zlib.error,
    ) as exc:
        raise DatasetError(f"invalid radial ZIP archive: {filename!r}") from exc

    try:
        csv_text = csv_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DatasetError(
            f"invalid UTF-8 CSV member {member!r} in radial ZIP {filename!r}"
        ) from exc

    radii: list[float] = []
    profiles: dict[int, list[float]] = {z: [] for z, _ in density_columns}
    expected_columns = (radius_column, *(name for _, name in density_columns))
    try:
        with io.StringIO(csv_text, newline="") as text_handle:
            reader = csv.DictReader(text_handle)
            if (
                reader.fieldnames is None
                or tuple(reader.fieldnames) != expected_columns
            ):
                raise DatasetError(
                    f"invalid radial CSV columns in {member!r} from {filename!r}"
                )
            for row_number, row in enumerate(reader, start=2):
                radii.append(
                    _coerce_finite_float(
                        row.get(radius_column),
                        what=(
                            f"radius in {filename!r} row {row_number} "
                            f"column {radius_column!r}"
                        ),
                    )
                )
                for z, column in density_columns:
                    profiles[z].append(
                        _coerce_finite_float(
                            row.get(column),
                            what=(
                                f"profile value in {filename!r} row {row_number} "
                                f"column {column!r}"
                            ),
                        )
                    )
    except DatasetError:
        raise
    except (csv.Error, ValueError) as exc:
        raise DatasetError(
            f"invalid radial CSV member {member!r} in {filename!r}"
        ) from exc

    n_z = max(elem.z for elem in iter_elements())
    profiles_by_z: list[tuple[float, ...] | None] = [None] * (n_z + 1)
    for z, values in profiles.items():
        if z <= 0 or z > n_z:
            raise DatasetError(f"invalid atomic number in {filename!r}: {z}")
        profiles_by_z[z] = tuple(values)
    return tuple(radii), tuple(profiles_by_z)


def _read_package_data_bytes(filename: str) -> bytes:
    """Read a packaged data resource without requiring a filesystem path."""

    path = resources.files("atomref.data").joinpath(filename)
    with path.open("rb") as handle:
        return handle.read()


def _radial_density_columns(info: DatasetInfo) -> tuple[tuple[int, str], ...]:
    """Return expected ``(Z, column)`` pairs from radial storage metadata."""

    if not isinstance(info.storage, Mapping) or info.coverage is None:
        raise DatasetError(f"invalid radial storage metadata for dataset: {info.ref!r}")
    pattern = info.storage.get("density_column_pattern")
    if not isinstance(pattern, str) or "{z" not in pattern:
        raise DatasetError(f"invalid radial storage metadata for dataset: {info.ref!r}")

    coverage = info.coverage
    if coverage.covered_z:
        covered_z = coverage.covered_z
    elif coverage.z_min is not None and coverage.z_max is not None:
        covered_z = tuple(range(coverage.z_min, coverage.z_max + 1))
    else:
        raise DatasetError(
            f"invalid radial coverage metadata for dataset: {info.ref!r}"
        )
    if len(covered_z) != coverage.n_values:
        raise DatasetError(
            f"invalid radial coverage metadata for dataset: {info.ref!r}"
        )

    try:
        return tuple((z, pattern.format(z=z)) for z in covered_z)
    except (KeyError, ValueError) as exc:
        raise DatasetError(
            f"invalid radial density-column pattern for dataset: {info.ref!r}"
        ) from exc


def _load_element_scalar_set(info: DatasetInfo) -> ElementScalarSet:
    """Load one dense-by-Z scalar CSV dataset."""

    if info.domain != "element":
        raise DatasetError(
            f"element scalar storage requires an element domain: {info.ref!r}"
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


def _load_element_radial_set(info: DatasetInfo) -> ElementRadialSet:
    """Load one shared-grid radial CSV from a single-member ZIP archive."""

    if info.domain != "element":
        raise DatasetError(
            f"element radial storage requires an element domain: {info.ref!r}"
        )
    if not isinstance(info.storage, Mapping):
        raise DatasetError(f"missing storage metadata for dataset: {info.ref!r}")
    filename = info.storage.get("filename")
    member = info.storage.get("member")
    radius_column = info.storage.get("radius_column")
    if (
        not isinstance(filename, str)
        or not isinstance(member, str)
        or not member
        or not isinstance(radius_column, str)
    ):
        raise DatasetError(f"invalid radial storage metadata for dataset: {info.ref!r}")

    density_columns = _radial_density_columns(info)
    radii, profiles_by_z = _load_radial_csv_zip(
        filename,
        member,
        radius_column,
        density_columns,
    )
    return ElementRadialSet(
        ref=info.ref,
        info=info,
        radii=radii,
        profiles_by_z=profiles_by_z,
    )


@lru_cache(maxsize=None)
def _load_builtin_set(ref: DatasetRef) -> BuiltinSet:
    """Load a canonical packaged dataset by its declared storage kind."""

    info = get_dataset_info(ref)
    if not isinstance(info.storage, Mapping):
        raise DatasetError(f"missing storage metadata for dataset: {info.ref!r}")
    storage_kind = info.storage.get("kind")
    if storage_kind == "element_scalar_csv":
        return _load_element_scalar_set(info)
    if storage_kind == "element_radial_csv_zip":
        return _load_element_radial_set(info)
    raise DatasetError(
        f"unknown storage kind {storage_kind!r} for dataset: {info.ref!r}"
    )


def get_builtin_set(ref: DatasetRef) -> BuiltinSet:
    """Load a scalar or radial packaged dataset through the shared registry.

    Args:
        ref: Quantity and packaged dataset identifier or alias.

    Returns:
        A cached immutable [ElementScalarSet][atomref.registry.ElementScalarSet]
        or [ElementRadialSet][atomref.registry.ElementRadialSet], chosen from the
        dataset's declared storage kind.

    Raises:
        DatasetError: If the reference is unknown, storage metadata is invalid,
            or the packaged payload fails validation.

    Examples:
        >>> loaded = get_builtin_set(
        ...     DatasetRef("covalent_radius", "cordero2008")
        ... )
        >>> isinstance(loaded, ElementScalarSet)
        True

    Notes:
        Scalar policies narrow this union internally. Radial profiles never
        participate in substitution or linear-transfer policy behavior.
    """

    canonical_ref = get_dataset_info(ref).ref
    return _load_builtin_set(canonical_ref)


def resolve_scalar_dataset_like(
    dataset: ScalarDatasetLike | ElementRadialSet,
) -> ElementScalarSet:
    """Resolve an internal scalar source and reject radial payloads."""

    if isinstance(dataset, ElementScalarSet):
        return dataset
    if isinstance(dataset, ElementRadialSet):
        raise DatasetError(
            f"dataset {dataset.ref!r} has a radial payload; scalar dataset required"
        )
    loaded = get_builtin_set(dataset)
    if not isinstance(loaded, ElementScalarSet):
        raise DatasetError(
            f"dataset {loaded.ref!r} has a radial payload; scalar dataset required"
        )
    return loaded


def _is_placeholder_value(info: DatasetInfo, value: float) -> bool:
    """Return ``True`` when ``value`` equals the dataset's placeholder value."""

    if info.placeholder_value is None:
        return False
    return abs(value - info.placeholder_value) < 1e-12
