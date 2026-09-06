from __future__ import annotations

"""Source-bound K27 Memory City adapter for the existing AuraOS arena plane.

This adapter does not make a K27 coordinate authoritative. It binds every read
to one exact local registry state, exposes review/projection reads, and forwards
revision+epoch+store-root CAS mutations only when explicitly opened writable.
A successful write consumes that runtime instance; continuing requires an exact
state-root rebind. External source currentness and consequence/effect authority
remain owned elsewhere.
"""

from dataclasses import asdict, dataclass
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import os

try:  # package import
    from .k27_memory import FrameAddress, K27Path, MemoryConflict, MemoryStore, StaleMemory
    from .k27_memory.persistent_memory import canonical
    from .k27_memory_city_spatial_seam.k27_memory_city_spatial_seam import (
        SeamDisposition, validate_spatial_seam,
    )
except ImportError:  # direct tools/arena import in existing harnesses
    from k27_memory import FrameAddress, K27Path, MemoryConflict, MemoryStore, StaleMemory
    from k27_memory.persistent_memory import canonical
    from k27_memory_city_spatial_seam.k27_memory_city_spatial_seam import (
        SeamDisposition, validate_spatial_seam,
    )

SCHEMA = "AURA-K27-MEMORY-RUNTIME-BINDING-v1"
SCENE_SCHEMA = "AURA-XR-SCENE-v1"
FRAME = "aura-memory-city-research"
GENERATION = "20260906-v1"
REGISTRY_SHA256 = "246dbded0a33eaede035b829bfcae9f8ee50d769f5c28f1a955a16073131d86f"
SEMANTIC_REGISTRY_ROOT = "7e0095415ffb6450aeb39f1faba782f27a1fb628e481fe7d1975aa5a649cf1c1"
PROVENANCE_ARCHIVE_SHA256 = "042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319"
EXPECTED_RECORDS = 1115
READ_APIS = (
    "CITY_K27_CONTEXT", "CITY_SCENE_SHELL", "CITY_ROUTE", "CITY_WHY",
    "CITY_ACTIVE_DOMAINS", "CITY_INVALIDATION_CONE",
)
SPATIAL_SEAM_SCHEMA = "AURA-K27-SPATIAL-SEAM-v1"
SPATIAL_SEAM_PARENT_SHA = "dedcb8d16ada00bb44ce71271175945a4b0a0fac"
SPATIAL_ROUTE_BLOB = "f8786e721813af7c81fca94eaeda08ec0b9598f3"
SPATIAL_SEAM_SOURCE_BLOB = "c439b0e1e438299cd8a914aade89034342065dd3"
SPATIAL_SEAM_MODULE_BLOB = "8983170b71dd962facb4eb586c002bd63948f2f8"
SPATIAL_TRANSITION = "SPATIAL.GROUND.COMPILE_SCENE"


class RuntimeBindingError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeMemoryBinding:
    object_id: str
    revision_id: str
    epoch: int
    frame_id: str
    frame_generation: str
    path: tuple[int, ...]
    payload_sha256: str
    state: str
    local_registry_current: bool
    upstream_currentness_asserted: bool = False
    truth_authority: bool = False
    planning_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    @property
    def k27(self) -> K27Path:
        return K27Path(self.path)

    @property
    def canonical_ref(self) -> str:
        return f"aura://memory-city/{self.object_id}#K27:/" + "/".join(f"{d:02d}" for d in self.path)


@dataclass(frozen=True)
class RegistrySeal:
    database_sha256: str
    semantic_registry_root: str
    records: int
    frame: str
    generation: str
    sqlite_integrity: str
    seal_scope: str = "canonical_seed"
    authority_minted: bool = False
    gate10: bool = False


class K27MemoryRuntime:
    """Adapter over one exact registry state with fail-closed mutation detection."""

    def __init__(self, registry_path: str | Path, *, writable: bool = False,
                 expected_working_state_root: str | None = None):
        self.path = Path(registry_path)
        if not self.path.is_file():
            raise RuntimeBindingError("registry file missing")
        self.writable = bool(writable)
        self._consumed = False
        if expected_working_state_root is None:
            self._seal = self._verify_seed_seal()
            with MemoryStore(self.path) as store:
                self._state_root = store.state_root()
        else:
            if not isinstance(expected_working_state_root, str) or len(expected_working_state_root) != 64:
                raise RuntimeBindingError("expected working state root must be one SHA-256 hex digest")
            self._seal = self._verify_working_seal(expected_working_state_root)
            self._state_root = expected_working_state_root

    @classmethod
    def from_environment(cls, *, writable: bool = False, env: Mapping[str, str] | None = None):
        source = os.environ if env is None else env
        path = source.get("AURA_K27_MEMORY_REGISTRY_PATH")
        if not path:
            raise RuntimeBindingError("AURA_K27_MEMORY_REGISTRY_PATH is required")
        return cls(path, writable=writable)

    @classmethod
    def from_working_registry(cls, registry_path: str | Path, *, expected_state_root: str,
                              writable: bool = False):
        """Rebind a mutated local registry only to an exact previously observed state root.

        This proves local state identity only. It does not authenticate an upstream
        owner, mint currentness, or preserve a previous runtime's authority.
        """
        return cls(registry_path, writable=writable,
                   expected_working_state_root=expected_state_root)

    @staticmethod
    def _coordinate_record(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "object_id": record["object_id"],
            "revision_id": record["revision_id"],
            "payload_sha256": record["payload_sha256"],
            "address": record["address"],
            "epoch": record["epoch"],
        }

    @staticmethod
    def _git_blob_sha1(data: bytes) -> str:
        return sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

    def _verify_seed_seal(self) -> RegistrySeal:
        raw_sha = sha256(self.path.read_bytes()).hexdigest()
        if raw_sha != REGISTRY_SHA256:
            raise RuntimeBindingError("registry byte SHA-256 mismatch")
        with MemoryStore(self.path) as store:
            integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
            rows = store.under(FRAME, GENERATION)
            if integrity != "ok":
                raise RuntimeBindingError("SQLite integrity check failed")
            if len(rows) != EXPECTED_RECORDS:
                raise RuntimeBindingError("registry row count mismatch")
            coords = [self._coordinate_record(r) for r in rows]
            semantic = sha256(canonical(sorted(coords, key=lambda x: x["object_id"])).encode()).hexdigest()
        if semantic != SEMANTIC_REGISTRY_ROOT:
            raise RuntimeBindingError("registry semantic root mismatch")
        return RegistrySeal(raw_sha, semantic, len(rows), FRAME, GENERATION, integrity)

    def _verify_working_seal(self, expected_state_root: str) -> RegistrySeal:
        raw_sha = sha256(self.path.read_bytes()).hexdigest()
        with MemoryStore(self.path) as store:
            integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
            records = store.db.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
            state_root = store.state_root()
        if integrity != "ok":
            raise RuntimeBindingError("SQLite integrity check failed while rebinding working registry")
        if state_root != expected_state_root:
            raise RuntimeBindingError("working registry state was superseded before rebind")
        return RegistrySeal(raw_sha, state_root, records, FRAME, GENERATION, integrity,
                            seal_scope="working_registry_state")

    def _assert_active(self) -> None:
        if self._consumed:
            raise RuntimeBindingError("runtime consumed by committed write; reopen against the committed state root")

    def _assert_registry_unchanged(self) -> None:
        self._assert_active()
        if sha256(self.path.read_bytes()).hexdigest() != self._seal.database_sha256:
            raise RuntimeBindingError("registry changed outside the bound runtime state")

    def _read_snapshot(self, operation: Callable[[MemoryStore], Any]) -> Any:
        self._assert_registry_unchanged()
        with MemoryStore(self.path) as store:
            store.db.execute("BEGIN")
            try:
                if store.state_root() != self._state_root:
                    raise RuntimeBindingError("registry state root changed before read")
                result = operation(store)
                if store.state_root() != self._state_root:
                    raise RuntimeBindingError("registry state changed during read")
                store.db.execute("COMMIT")
            except BaseException:
                store.db.execute("ROLLBACK")
                raise
        self._assert_registry_unchanged()
        return result

    @property
    def seal(self) -> RegistrySeal:
        self._assert_registry_unchanged()
        return self._seal

    @property
    def consumed(self) -> bool:
        return self._consumed

    @staticmethod
    def _binding_from_record(record: Mapping[str, Any]) -> RuntimeMemoryBinding:
        a = record["address"]
        return RuntimeMemoryBinding(
            object_id=record["object_id"], revision_id=record["revision_id"], epoch=record["epoch"],
            frame_id=a["frame_id"], frame_generation=a["frame_generation"], path=tuple(a["path"]),
            payload_sha256=record["payload_sha256"], state=record["state"],
            local_registry_current=(record["state"] == "fresh" and a["frame_generation"] == GENERATION),
        )

    def _read_record(self, object_id: str, *, allow_stale: bool = False):
        def op(store: MemoryStore):
            return store.get(object_id, allow_stale=allow_stale)
        record = self._read_snapshot(op)
        if record is None:
            raise KeyError(object_id)
        return self._binding_from_record(record), record

    def read(self, object_id: str) -> tuple[RuntimeMemoryBinding, dict[str, Any]]:
        return self._read_record(object_id)

    def under(self, prefix: Sequence[int] = ()) -> list[RuntimeMemoryBinding]:
        p = tuple(prefix)
        K27Path(p)
        rows = self._read_snapshot(lambda store: store.under(FRAME, GENERATION, p))
        return [self._binding_from_record(r) for r in rows]

    def invalidation_cone(self, object_id: str) -> dict[str, Any]:
        """One-snapshot dependency closure; no stale marks are written."""
        def op(store: MemoryStore):
            root = store.get(object_id, allow_stale=True)
            if root is None:
                raise KeyError(object_id)
            pending, seen, affected = [object_id], {object_id}, []
            while pending:
                parent = pending.pop()
                rows = store.db.execute(
                    """SELECT o.object_id,o.path FROM dependencies d JOIN objects o
                    ON o.current_rev=d.revision_id WHERE d.source_object=? ORDER BY o.object_id""",
                    (parent,),
                ).fetchall()
                for row in rows:
                    key = row["object_id"]
                    if key in seen:
                        continue
                    seen.add(key)
                    pending.append(key)
                    affected.append({"object_id": key, "path_key": row["path"]})
            return {
                "root_object_id": object_id,
                "root_path": root["address"]["path"],
                "affected": affected,
                "bounded": True,
                "mutation_performed": False,
                "authority_minted": False,
            }
        return self._read_snapshot(op)

    def scene_shell(self, prefix: Sequence[int] = (2,), *, limit: int = 64) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 1024:
            raise ValueError("limit must be 1..1024")
        bindings = self.under(prefix)[:limit]
        return {
            "schema": SCENE_SCHEMA,
            "source_schema": SCHEMA,
            "frame": FRAME,
            "generation": GENERATION,
            "prefix": list(prefix),
            "entities": [
                {
                    "object_id": b.object_id,
                    "k27_path": list(b.path),
                    "revision_id": b.revision_id,
                    "epoch": b.epoch,
                    "canonical_ref": b.canonical_ref,
                }
                for b in bindings
            ],
            "review_only": True,
            "projection_only": True,
            "execution_authority": False,
            "truth_authority": False,
            "gate10": False,
        }

    def route_projection(self, object_id: str) -> dict[str, Any]:
        binding, record = self.read(object_id)
        if not object_id.startswith("MCXR-"):
            raise ValueError("CITY_ROUTE requires a research-route object")
        return {
            "schema": "AURA-K27-ROUTE-PROJECTION-v1",
            "binding": asdict(binding),
            "payload": record["payload"],
            "dependencies": record["dependencies"],
            "dependency_epochs": record.get("dependency_epochs"),
            "review_only": True,
            "execution_authority": False,
            "gate10": False,
        }

    def spatial_seam_binding_receipt(self, route_bytes: bytes,
                                     provenance_manifest: Mapping[str, Any]) -> dict[str, Any]:
        """Bind exactly the canonical route bytes to the canonical seam validator."""
        if self.seal.seal_scope != "canonical_seed":
            raise RuntimeBindingError("Spatial seam receipt requires the exact sealed seed registry")
        if not isinstance(route_bytes, bytes):
            raise RuntimeBindingError("Spatial route must be supplied as exact bytes")
        route_blob = self._git_blob_sha1(route_bytes)
        if route_blob != SPATIAL_ROUTE_BLOB:
            raise RuntimeBindingError("Spatial route Git blob mismatch")
        structural = validate_spatial_seam(route_bytes, provenance_manifest)
        if structural.disposition is not SeamDisposition.READY_FOR_INDEPENDENT_REVIEW:
            raise RuntimeBindingError("Spatial seam failed canonical structural validation: " + ",".join(structural.reasons))
        return {
            "schema": "AURA-K27-MEMORY-SPATIAL-RUNTIME-BINDING-RECEIPT-v2",
            "spatial_transition": SPATIAL_TRANSITION,
            "spatial_seam_schema": SPATIAL_SEAM_SCHEMA,
            "spatial_seam_parent_sha": SPATIAL_SEAM_PARENT_SHA,
            "spatial_route_blob": route_blob,
            "spatial_seam_source_blob": SPATIAL_SEAM_SOURCE_BLOB,
            "spatial_seam_module_blob": SPATIAL_SEAM_MODULE_BLOB,
            "registry_sha256": self.seal.database_sha256,
            "semantic_registry_root": self.seal.semantic_registry_root,
            "records": self.seal.records,
            "read_apis": list(structural.read_apis),
            "route_structural_receipt_root": structural.receipt_root,
            "provider_bytes_bound": False,
            "projection_only": True,
            "review_only": True,
            "truth_authority": False,
            "execution_authority": False,
            "effect_authority": False,
            "authority_minted": False,
            "gate10": False,
        }

    def consequence_source_exit(self, object_id: str):
        """Return a non-current source projection; this adapter cannot authenticate owner currentness."""
        binding, _ = self.read(object_id)
        try:
            from .consequence_admission_kernel import SourceExit
        except ImportError:
            from consequence_admission_kernel import SourceExit
        return SourceExit(
            source_id=binding.object_id,
            owner_ref="AURAOS:K27_MEMORY_RUNTIME:LOCAL_REGISTRY_PROJECTION",
            generation=f"{binding.frame_generation}:epoch:{binding.epoch}",
            semantic_root=binding.revision_id,
            current=False,
        )

    def publish_cas(self, object_id: str, payload: Mapping[str, Any], *, source_url: str,
                    source_version: str, expected_revision: str, expected_epoch: int,
                    dependencies: Mapping[str, str] | None = None,
                    dependency_epochs: Mapping[str, int] | None = None) -> dict[str, Any]:
        if not self.writable:
            raise PermissionError("runtime registry opened read-only")
        self._assert_registry_unchanged()
        binding, _ = self._read_record(object_id, allow_stale=True)
        address = FrameAddress(binding.frame_id, binding.frame_generation, binding.path, object_id)
        with MemoryStore(self.path) as store:
            result = store.publish(
                object_id,
                dict(payload),
                address,
                source_url=source_url,
                source_version=source_version,
                expected_revision=expected_revision,
                expected_epoch=expected_epoch,
                dependencies=None if dependencies is None else dict(dependencies),
                dependency_epochs=None if dependency_epochs is None else dict(dependency_epochs),
                expected_store_root=self._state_root,
            )
        # `store_state_root` was computed while BEGIN IMMEDIATE still protected
        # the exact committed transition. Do not reopen/refresh after COMMIT:
        # another writer may legitimately supersede it before any filesystem read.
        # Instead consume this runtime and require an exact-root successor rebind.
        committed_root = result["store_state_root"]
        self._consumed = True
        return {
            **result,
            "commit_status": "COMMITTED_REOPEN_REQUIRED",
            "committed_store_state_root": committed_root,
            "target_k27": list(binding.path),
            "invalidation_cone": {
                "root_object_id": object_id,
                "root_path": list(binding.path),
                "affected_objects": list(result.get("invalidated", [])),
                "snapshot_scope": "write_transaction",
                "bounded": True,
                "mutation_performed": True,
                "authority_minted": False,
            },
            "runtime_consumed": True,
            "reopen_required": True,
            "truth_authority": False,
            "effect_authority": False,
            "authority_minted": False,
            "gate10": False,
        }
