"""Source-owned admission gate for Aura K27 ASTGE mmap use.

PR463 proves observed-generation checks around mapped operations but deliberately
cannot eliminate mutation between validation and an OS memory access.  This
module therefore does not claim to make mmap intrinsically safe.  It defines a
stricter *eligibility* boundary for the normal Aura path:

- the exact opened file identities/generation captured by PR463 must match one
  repository-owned immutability capability;
- the capability is bound to an explicit snapshot generation and manifest
  digest from the publication owner;
- publisher and independent verifier identities must be distinct;
- replacement-only publication, published-generation immutability and bounded
  mapping lifetime must all be exact booleans owned by the capability record;
- production starts with an empty capability registry and therefore fails
  closed to the existing Read+Seek baseline.

A capability pass means only MMAP_ELIGIBLE_UNDER_REGISTERED_CAPABILITY.  It does
not prove SIGBUS impossibility, concurrent hostile-mutation safety, physical
crash durability, native-engine safety, performance superiority or authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
from pathlib import Path
from typing import Iterable

import k27_astge_mmap_lifecycle as life

CAPABILITY_SCHEMA = "AuraK27ASTGEBackingFileImmutabilityCapabilityV1"
ADMISSION_SCHEMA = "AuraK27ASTGEMmapAdmissionReceiptV1"
REGISTRY_SCHEMA = "AuraK27ASTGEBackingFileImmutabilityRegistryV1"
REGISTRY_GENERATION = "AURA_K27_ASTGE_MMAP_IMMUTABILITY_HOLD_V1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _require_text(record: object, field: str, code: str) -> str:
    value = getattr(record, field, None)
    if not isinstance(value, str) or not value.strip():
        raise life.MmapLifecycleError(code)
    return value.strip()


def _require_sha256(record: object, field: str, code: str) -> str:
    value = _require_text(record, field, code)
    if len(value) != 64 or value.lower() != value:
        raise life.MmapLifecycleError(code)
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise life.MmapLifecycleError(code) from exc
    return value


def _require_exact_bool(record: object, field: str, code: str) -> bool:
    value = getattr(record, field, None)
    if type(value) is not bool:
        raise life.MmapLifecycleError(code)
    return value


@dataclass(frozen=True)
class BackingFileImmutabilityCapabilityV1:
    storage_root: str
    snapshot_generation: str
    manifest_digest: str
    nodes_generation_digest: str
    edges_generation_digest: str
    combined_generation_digest: str
    nodes_device: int
    nodes_inode: int
    edges_device: int
    edges_inode: int
    publisher_ref: str
    verifier_ref: str
    filesystem_semantics_ref: str
    external_mutation_disposition_ref: str
    replacement_only_publication: bool
    published_generation_files_immutable: bool
    mapped_lifetime_within_capability: bool
    capability_current: bool
    revoked: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = CAPABILITY_SCHEMA

    @property
    def capability_digest(self) -> str:
        return _digest("AURA_K27_ASTGE_BACKING_IMMUTABILITY_CAPABILITY_V1", asdict(self))


_CANONICAL_BACKING_IMMUTABILITY_CAPABILITIES: tuple[
    BackingFileImmutabilityCapabilityV1, ...
] = ()


@dataclass(frozen=True)
class BackingFileImmutabilityRegistryReceiptV1:
    registry_generation: str
    capability_digests: tuple[str, ...]
    active_capability_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = REGISTRY_SCHEMA

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_K27_ASTGE_BACKING_IMMUTABILITY_REGISTRY_V1", asdict(self))


@dataclass(frozen=True)
class MmapAdmissionReceiptV1:
    capability_digest: str
    registry_generation: str
    registry_digest: str
    snapshot_generation: str
    manifest_digest: str
    combined_file_generation_digest: str
    mmap_eligible_under_registered_capability: bool = True
    concurrent_mutation_race_proven_safe: bool = False
    sigbus_impossible_proven: bool = False
    hostile_external_mutation_proven_safe: bool = False
    physical_crash_durability_proven: bool = False
    native_engine_safety_proven: bool = False
    performance_superiority_proven: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = ADMISSION_SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_K27_ASTGE_MMAP_ADMISSION_V1", asdict(self))


def _validate_capability_shape(record: BackingFileImmutabilityCapabilityV1) -> None:
    if not isinstance(record, BackingFileImmutabilityCapabilityV1):
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_RECORD_REQUIRED")
    if record.schema != CAPABILITY_SCHEMA:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_SCHEMA_MISMATCH")

    for field, code in (
        ("storage_root", "MMAP_IMMUTABILITY_STORAGE_ROOT_REQUIRED"),
        ("snapshot_generation", "MMAP_IMMUTABILITY_SNAPSHOT_GENERATION_REQUIRED"),
        ("publisher_ref", "MMAP_IMMUTABILITY_PUBLISHER_REQUIRED"),
        ("verifier_ref", "MMAP_IMMUTABILITY_VERIFIER_REQUIRED"),
        ("filesystem_semantics_ref", "MMAP_IMMUTABILITY_FILESYSTEM_SEMANTICS_REQUIRED"),
        (
            "external_mutation_disposition_ref",
            "MMAP_IMMUTABILITY_EXTERNAL_MUTATION_DISPOSITION_REQUIRED",
        ),
    ):
        _require_text(record, field, code)

    for field, code in (
        ("manifest_digest", "MMAP_IMMUTABILITY_MANIFEST_DIGEST_REQUIRED"),
        ("nodes_generation_digest", "MMAP_IMMUTABILITY_NODES_GENERATION_DIGEST_REQUIRED"),
        ("edges_generation_digest", "MMAP_IMMUTABILITY_EDGES_GENERATION_DIGEST_REQUIRED"),
        ("combined_generation_digest", "MMAP_IMMUTABILITY_COMBINED_GENERATION_DIGEST_REQUIRED"),
    ):
        _require_sha256(record, field, code)

    for field, code in (
        ("replacement_only_publication", "MMAP_REPLACEMENT_ONLY_BOOL_REQUIRED"),
        ("published_generation_files_immutable", "MMAP_PUBLISHED_IMMUTABILITY_BOOL_REQUIRED"),
        ("mapped_lifetime_within_capability", "MMAP_LIFETIME_BOUND_BOOL_REQUIRED"),
        ("capability_current", "MMAP_CAPABILITY_CURRENT_BOOL_REQUIRED"),
        ("revoked", "MMAP_CAPABILITY_REVOKED_BOOL_REQUIRED"),
        ("authority", "MMAP_CAPABILITY_AUTHORITY_BOOL_REQUIRED"),
        ("external_effect", "MMAP_CAPABILITY_EXTERNAL_EFFECT_BOOL_REQUIRED"),
    ):
        _require_exact_bool(record, field, code)

    for field, code in (
        ("nodes_device", "MMAP_IMMUTABILITY_NODES_DEVICE_REQUIRED"),
        ("nodes_inode", "MMAP_IMMUTABILITY_NODES_INODE_REQUIRED"),
        ("edges_device", "MMAP_IMMUTABILITY_EDGES_DEVICE_REQUIRED"),
        ("edges_inode", "MMAP_IMMUTABILITY_EDGES_INODE_REQUIRED"),
    ):
        value = getattr(record, field, None)
        if type(value) is not int or value < 0:
            raise life.MmapLifecycleError(code)

    if record.publisher_ref.strip() == record.verifier_ref.strip():
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_INDEPENDENT_VERIFIER_REQUIRED")
    if record.authority is not False or record.external_effect is not False:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_EFFECT_AUTHORITY_FORBIDDEN")


def _registry_receipt_from_records(
    records: Iterable[BackingFileImmutabilityCapabilityV1],
) -> BackingFileImmutabilityRegistryReceiptV1:
    records = tuple(records)
    for record in records:
        _validate_capability_shape(record)
    ordered = tuple(sorted(records, key=lambda record: record.capability_digest))
    return BackingFileImmutabilityRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        capability_digests=tuple(record.capability_digest for record in ordered),
        active_capability_count=sum(
            1
            for record in ordered
            if record.capability_current is True
            and record.revoked is False
            and record.replacement_only_publication is True
            and record.published_generation_files_immutable is True
            and record.mapped_lifetime_within_capability is True
        ),
    )


def backing_immutability_capability_registry_receipt() -> BackingFileImmutabilityRegistryReceiptV1:
    return _registry_receipt_from_records(_CANONICAL_BACKING_IMMUTABILITY_CAPABILITIES)


def _observed_storage_root(reader: life.LifecycleGuardedMmapGraphReader) -> str:
    nodes_parent = str(Path(reader._nodes_generation.path).parent.resolve())
    edges_parent = str(Path(reader._edges_generation.path).parent.resolve())
    if nodes_parent != edges_parent:
        raise life.MmapLifecycleError("MMAP_STORAGE_ROOT_MISMATCH")
    return nodes_parent


def _binding_matches(
    record: BackingFileImmutabilityCapabilityV1,
    reader: life.LifecycleGuardedMmapGraphReader,
    snapshot_generation: str,
    manifest_digest: str,
) -> bool:
    nodes = reader._nodes_generation
    edges = reader._edges_generation
    observed = reader.validate_generation()
    return all(
        (
            record.storage_root == _observed_storage_root(reader),
            record.snapshot_generation == snapshot_generation,
            record.manifest_digest == manifest_digest,
            record.nodes_generation_digest == nodes.generation_digest,
            record.edges_generation_digest == edges.generation_digest,
            record.combined_generation_digest == observed.combined_generation_digest,
            record.nodes_device == nodes.device,
            record.nodes_inode == nodes.inode,
            record.edges_device == edges.device,
            record.edges_inode == edges.inode,
        )
    )


def _resolve_capability(
    *,
    reader: life.LifecycleGuardedMmapGraphReader,
    snapshot_generation: str,
    manifest_digest: str,
    records: tuple[BackingFileImmutabilityCapabilityV1, ...],
) -> tuple[BackingFileImmutabilityCapabilityV1, BackingFileImmutabilityRegistryReceiptV1]:
    if not isinstance(snapshot_generation, str) or not snapshot_generation.strip():
        raise life.MmapLifecycleError("MMAP_SNAPSHOT_GENERATION_REQUIRED")
    if not isinstance(manifest_digest, str) or len(manifest_digest) != 64:
        raise life.MmapLifecycleError("MMAP_MANIFEST_DIGEST_REQUIRED")
    try:
        bytes.fromhex(manifest_digest)
    except ValueError as exc:
        raise life.MmapLifecycleError("MMAP_MANIFEST_DIGEST_REQUIRED") from exc
    if manifest_digest.lower() != manifest_digest:
        raise life.MmapLifecycleError("MMAP_MANIFEST_DIGEST_REQUIRED")

    registry = _registry_receipt_from_records(records)
    matches = [
        record
        for record in records
        if _binding_matches(record, reader, snapshot_generation, manifest_digest)
    ]
    if not matches:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_REQUIRED")
    if len(matches) != 1:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_AMBIGUOUS")
    record = matches[0]
    if record.capability_current is not True:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_STALE")
    if record.revoked is not False:
        raise life.MmapLifecycleError("MMAP_IMMUTABILITY_CAPABILITY_REVOKED")
    if record.replacement_only_publication is not True:
        raise life.MmapLifecycleError("MMAP_REPLACEMENT_ONLY_PUBLICATION_REQUIRED")
    if record.published_generation_files_immutable is not True:
        raise life.MmapLifecycleError("MMAP_PUBLISHED_GENERATION_IMMUTABILITY_REQUIRED")
    if record.mapped_lifetime_within_capability is not True:
        raise life.MmapLifecycleError("MMAP_CAPABILITY_LIFETIME_BOUND_REQUIRED")
    return record, registry


class CapabilityAdmittedMmapGraphReader:
    def __init__(
        self,
        guard: life.LifecycleGuardedMmapGraphReader,
        capability: BackingFileImmutabilityCapabilityV1,
        receipt: MmapAdmissionReceiptV1,
    ):
        self._guard = guard
        self._capability = capability
        self.admission_receipt = receipt
        self._closed = False

    @property
    def node_count(self) -> int:
        return self._guard.node_count

    @property
    def block_count(self) -> int:
        return self._guard.block_count

    def validate_generation(self) -> life.MmapLifecycleValidationReceiptV1:
        return self._guard.validate_generation()

    def get_node(self, node_id: int):
        return self._guard.get_node(node_id)

    def query_affected_cone(self, root_node_id: int, max_depth: int):
        return self._guard.query_affected_cone(root_node_id, max_depth)

    def read_bounded_slice(self, role: str, start: int, length: int) -> bytes:
        return self._guard.read_bounded_slice(role, start, length)  # type: ignore[arg-type]

    def reopen(self):
        raise life.MmapLifecycleError("MMAP_EXPLICIT_READMISSION_REQUIRED")

    def close(self) -> None:
        if not self._closed:
            self._guard.close()
            self._closed = True

    def __enter__(self) -> "CapabilityAdmittedMmapGraphReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _open_with_records(
    *,
    nodes_path: str,
    edges_path: str,
    snapshot_generation: str,
    manifest_digest: str,
    records: tuple[BackingFileImmutabilityCapabilityV1, ...],
) -> CapabilityAdmittedMmapGraphReader:
    guard = life.LifecycleGuardedMmapGraphReader(nodes_path, edges_path)
    try:
        capability, registry = _resolve_capability(
            reader=guard,
            snapshot_generation=snapshot_generation,
            manifest_digest=manifest_digest,
            records=records,
        )
        observed = guard.validate_generation()
        receipt = MmapAdmissionReceiptV1(
            capability_digest=capability.capability_digest,
            registry_generation=registry.registry_generation,
            registry_digest=registry.registry_digest,
            snapshot_generation=snapshot_generation,
            manifest_digest=manifest_digest,
            combined_file_generation_digest=observed.combined_generation_digest,
        )
        return CapabilityAdmittedMmapGraphReader(guard, capability, receipt)
    except Exception:
        guard.close()
        raise


def open_admitted_mmap_graph_reader(
    *,
    nodes_path: str,
    edges_path: str,
    snapshot_generation: str,
    manifest_digest: str,
) -> CapabilityAdmittedMmapGraphReader:
    """Canonical fail-closed mmap entry point.

    Production is intentionally held while the source-owned capability registry
    is empty.  Callers cannot provide records, registries, trust booleans or an
    alternate resolver.
    """
    return _open_with_records(
        nodes_path=nodes_path,
        edges_path=edges_path,
        snapshot_generation=snapshot_generation,
        manifest_digest=manifest_digest,
        records=_CANONICAL_BACKING_IMMUTABILITY_CAPABILITIES,
    )


def mmap_admission_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(open_admitted_mmap_graph_reader).parameters)
