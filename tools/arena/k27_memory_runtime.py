from __future__ import annotations

"""Source-bound K27 Memory City adapter for the existing AuraOS arena plane.

This adapter does not make a K27 coordinate authoritative.  It verifies one
sealed registry snapshot, exposes review/projection reads, and forwards exact
revision+epoch CAS mutations only when explicitly opened writable.  External
source currentness and consequence/effect authority remain owned elsewhere.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import os

try:  # package import
    from .k27_memory import FrameAddress, K27Path, MemoryConflict, MemoryStore, StaleMemory
    from .k27_memory.persistent_memory import canonical
except ImportError:  # direct tools/arena import in existing harnesses
    from k27_memory import FrameAddress, K27Path, MemoryConflict, MemoryStore, StaleMemory
    from k27_memory.persistent_memory import canonical

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
SPATIAL_ROUTE_BLOB = "f8786e59a7e9a14c14dafa587f948eafe9496ad6"
SPATIAL_SEAM_MODULE_BLOB = "7356518021122491bd68e8a2f5e57433e0c833ad"
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
    authority_minted: bool = False
    gate10: bool = False

class K27MemoryRuntime:
    """Read-mostly adapter over one exact Memory City registry snapshot."""

    def __init__(self, registry_path: str | Path, *, writable: bool = False):
        self.path = Path(registry_path)
        if not self.path.is_file():
            raise RuntimeBindingError("registry file missing")
        self.writable = bool(writable)
        self._seal = self._verify_seal()

    @classmethod
    def from_environment(cls, *, writable: bool = False, env: Mapping[str, str] | None = None):
        source = os.environ if env is None else env
        path = source.get("AURA_K27_MEMORY_REGISTRY_PATH")
        if not path:
            raise RuntimeBindingError("AURA_K27_MEMORY_REGISTRY_PATH is required")
        return cls(path, writable=writable)

    @staticmethod
    def _coordinate_record(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "object_id": record["object_id"],
            "revision_id": record["revision_id"],
            "payload_sha256": record["payload_sha256"],
            "address": record["address"],
            "epoch": record["epoch"],
        }

    def _verify_seal(self) -> RegistrySeal:
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

    @property
    def seal(self) -> RegistrySeal:
        return self._seal

    def read(self, object_id: str) -> tuple[RuntimeMemoryBinding, dict[str, Any]]:
        with MemoryStore(self.path) as store:
            record = store.get(object_id)
        if record is None:
            raise KeyError(object_id)
        a = record["address"]
        binding = RuntimeMemoryBinding(
            object_id=record["object_id"], revision_id=record["revision_id"], epoch=record["epoch"],
            frame_id=a["frame_id"], frame_generation=a["frame_generation"], path=tuple(a["path"]),
            payload_sha256=record["payload_sha256"], state=record["state"],
            local_registry_current=(record["state"] == "fresh" and a["frame_generation"] == GENERATION),
        )
        return binding, record

    def under(self, prefix: Sequence[int] = ()) -> list[RuntimeMemoryBinding]:
        p = tuple(prefix)
        K27Path(p)
        with MemoryStore(self.path) as store:
            rows = store.under(FRAME, GENERATION, p)
        return [self._binding_from_record(r) for r in rows]

    @staticmethod
    def _binding_from_record(record: Mapping[str, Any]) -> RuntimeMemoryBinding:
        a = record["address"]
        return RuntimeMemoryBinding(
            object_id=record["object_id"], revision_id=record["revision_id"], epoch=record["epoch"],
            frame_id=a["frame_id"], frame_generation=a["frame_generation"], path=tuple(a["path"]),
            payload_sha256=record["payload_sha256"], state=record["state"],
            local_registry_current=(record["state"] == "fresh" and a["frame_generation"] == GENERATION),
        )

    def invalidation_cone(self, object_id: str) -> dict[str, Any]:
        """Read-only dependency closure.  No stale marks are written."""
        with MemoryStore(self.path) as store:
            root = store.get(object_id)
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
                    seen.add(key); pending.append(key)
                    affected.append({"object_id": key, "path_key": row["path"]})
        return {
            "root_object_id": object_id,
            "root_path": root["address"]["path"],
            "affected": affected,
            "bounded": True,
            "mutation_performed": False,
            "authority_minted": False,
        }

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
                    "object_id": b.object_id, "k27_path": list(b.path), "revision_id": b.revision_id,
                    "epoch": b.epoch, "canonical_ref": b.canonical_ref,
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
            "review_only": True,
            "execution_authority": False,
            "gate10": False,
        }


    def spatial_seam_binding_receipt(self, spatial_manifest: Mapping[str, Any]) -> dict[str, Any]:
        """Validate PR #859's declaration-only Spatial seam against this store.

        This is a structural use-site binding only. It does not authenticate the
        upstream source owner, mint currentness, or convert a projection into
        truth/effect authority.
        """
        transitions = spatial_manifest.get("transitions")
        if not isinstance(transitions, list):
            raise RuntimeBindingError("spatial transitions missing")
        matches = [t for t in transitions if isinstance(t, Mapping) and t.get("transition_id") == SPATIAL_TRANSITION]
        if len(matches) != 1:
            raise RuntimeBindingError("expected exactly one Spatial COMPILE_SCENE transition")
        binding = matches[0].get("memory_city_binding")
        if not isinstance(binding, Mapping):
            raise RuntimeBindingError("Memory City Spatial seam missing")
        if binding.get("binding_schema") != SPATIAL_SEAM_SCHEMA:
            raise RuntimeBindingError("Spatial seam schema mismatch")
        if binding.get("provenance_archive_sha256") != PROVENANCE_ARCHIVE_SHA256:
            raise RuntimeBindingError("Spatial seam provenance root mismatch")
        if binding.get("scene_schema") != SCENE_SCHEMA:
            raise RuntimeBindingError("Spatial scene schema mismatch")
        read_apis = binding.get("read_apis")
        if not isinstance(read_apis, Mapping) or set(read_apis) != set(READ_APIS):
            raise RuntimeBindingError("Spatial seam read API set mismatch")
        if any(read_apis.get(name) != "REVIEW_ONLY" for name in READ_APIS):
            raise RuntimeBindingError("Spatial seam widened a read API")
        for key in ("projection_only", "strict_hold_unknown"):
            if binding.get(key) is not True:
                raise RuntimeBindingError(f"Spatial seam {key} must be true")
        for key in ("renderer_authority", "execution_authority", "effect_authority", "gate10"):
            if binding.get(key) is not False:
                raise RuntimeBindingError(f"Spatial seam {key} must remain false")
        authority = spatial_manifest.get("authority")
        if not isinstance(authority, Mapping):
            raise RuntimeBindingError("spatial authority block missing")
        if authority.get("execution_authority") is not False or authority.get("automatic_merge") is not False:
            raise RuntimeBindingError("Spatial arena authority ceiling widened")
        return {
            "schema": "AURA-K27-MEMORY-SPATIAL-RUNTIME-BINDING-RECEIPT-v1",
            "spatial_transition": SPATIAL_TRANSITION,
            "spatial_seam_schema": SPATIAL_SEAM_SCHEMA,
            "spatial_seam_parent_sha": SPATIAL_SEAM_PARENT_SHA,
            "spatial_route_blob": SPATIAL_ROUTE_BLOB,
            "spatial_seam_module_blob": SPATIAL_SEAM_MODULE_BLOB,
            "registry_sha256": self.seal.database_sha256,
            "semantic_registry_root": self.seal.semantic_registry_root,
            "records": self.seal.records,
            "read_apis": list(READ_APIS),
            "projection_only": True,
            "review_only": True,
            "truth_authority": False,
            "execution_authority": False,
            "effect_authority": False,
            "authority_minted": False,
            "gate10": False,
        }

    def consequence_source_exit(self, object_id: str, *, external_currentness_confirmed: bool = False):
        """Build the existing consequence-kernel SourceExit without minting currentness.

        `external_currentness_confirmed` must come from the upstream owner.  K27
        local registry consistency never turns it true by itself.
        """
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
            current=bool(binding.local_registry_current and external_currentness_confirmed),
        )

    def publish_cas(self, object_id: str, payload: Mapping[str, Any], *, source_url: str,
                    source_version: str, expected_revision: str, expected_epoch: int,
                    dependencies: Mapping[str, str] | None = None) -> dict[str, Any]:
        if not self.writable:
            raise PermissionError("runtime registry opened read-only")
        binding, _ = self.read(object_id)
        address = FrameAddress(binding.frame_id, binding.frame_generation, binding.path, object_id)
        with MemoryStore(self.path) as store:
            result = store.publish(
                object_id, dict(payload), address,
                source_url=source_url, source_version=source_version,
                expected_revision=expected_revision, expected_epoch=expected_epoch,
                dependencies=None if dependencies is None else dict(dependencies),
            )
        return {
            **result,
            "target_k27": list(binding.path),
            "invalidation_cone": self.invalidation_cone(object_id),
            "authority_minted": False,
            "gate10": False,
        }
