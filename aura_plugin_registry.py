"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:AURA_PLUGIN_REGISTRY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Installable Organs)
DEPENDENCIES: dataclasses, hashlib, json, time, typing
FUNCTIONS: AuraPluginManifest, AuraPluginRegistry, build_default_registry
SYNOPSIS: Packages Aura domains as installable organs with explicit permission
          manifests. Each organ declares its Arena adapter, sidecar tables,
          verifier gates, and boundary invariant. Permissions that would bypass
          a verifier or export raw private memory are denied. Install/uninstall
          events are recorded in QDKT.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import time
from typing import Any

AURA_PLUGIN_REGISTRY_VERSION = "AURA_PLUGIN_REGISTRY_V1"

# Permissions no organ may hold.
DENIED_PERMISSIONS = frozenset(
    {
        "raw_private_memory_export",
        "raw_sidecar_dump",
        "bypass_verifier",
        "bypass_shadow",
        "bypass_judge",
        "bypass_architect",
        "mutate_production_without_arena",
    }
)

# The eleven organs required by the meta-harness spec.
AURA_ORGANS = (
    "core",
    "qdkt",
    "dream",
    "travel",
    "social",
    "fintech",
    "civic",
    "code",
    "icm",
    "graph",
    "federation",
)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


@dataclass(frozen=True)
class AuraPluginManifest:
    """Manifest describing one installable Aura organ."""

    organ_id: str
    domain: str
    entry_module: str
    description: str
    required_permissions: tuple[str, ...]
    provided_tools: tuple[str, ...]
    sidecar_tables: tuple[str, ...]
    verifier_gates: tuple[str, ...]
    boundary_invariant: str
    arena_adapter: str = ""
    risk_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "organ_id": self.organ_id,
            "domain": self.domain,
            "entry_module": self.entry_module,
            "description": self.description,
            "required_permissions": list(self.required_permissions),
            "provided_tools": list(self.provided_tools),
            "sidecar_tables": list(self.sidecar_tables),
            "verifier_gates": list(self.verifier_gates),
            "boundary_invariant": self.boundary_invariant,
            "arena_adapter": self.arena_adapter,
            "risk_score": float(self.risk_score),
            "metadata": dict(self.metadata),
        }

    def permission_risk(self) -> float:
        """Return a [0,1] risk score for this organ's permission set."""
        denied_hits = len(set(self.required_permissions) & DENIED_PERMISSIONS)
        if denied_hits:
            return 1.0
        # Heuristic: more permissions and sidecar tables => higher risk.
        base = min(1.0, len(self.required_permissions) / 12.0)
        sidecar_risk = min(0.3, len(self.sidecar_tables) / 10.0)
        # Clamp the result to [0.0, 1.0] to ensure it stays in the documented range
        return round(max(0.0, min(1.0, base + sidecar_risk + float(self.risk_score))), 4)


class AuraPluginRegistry:
    """Registry of installable Aura organs.

    Each organ is registered with a manifest. ``install`` records the organ
    as active and emits a QDKT observation. ``uninstall`` removes it and
    records the event. No organ may hold a denied permission.
    """

    def __init__(self, *, qdkt: Any = None) -> None:
        self.qdkt = qdkt
        self._manifests: dict[str, AuraPluginManifest] = {}
        self._installed: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, manifest: AuraPluginManifest) -> None:
        if manifest.organ_id not in AURA_ORGANS:
            raise ValueError(f"unknown organ '{manifest.organ_id}' (not in AURA_ORGANS)")
        denied = set(manifest.required_permissions) & DENIED_PERMISSIONS
        if denied:
            raise ValueError(f"organ '{manifest.organ_id}' requests denied permissions: {sorted(denied)}")
        if manifest.organ_id in self._manifests:
            raise ValueError(f"organ '{manifest.organ_id}' is already registered")
        self._manifests[manifest.organ_id] = manifest

    def list_organs(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._manifests.values()]

    def get_manifest(self, organ_id: str) -> AuraPluginManifest | None:
        return self._manifests.get(organ_id)

    # ------------------------------------------------------------------
    # Install / uninstall
    # ------------------------------------------------------------------

    def install(self, organ_id: str, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
        manifest = self._manifests.get(organ_id)
        if manifest is None:
            raise ValueError(f"cannot install unknown organ '{organ_id}'")
        if organ_id in self._installed:
            raise ValueError(f"organ '{organ_id}' is already installed")
        # Store internal record with full config
        internal_record = {
            "organ_id": organ_id,
            "installed_at": time.time(),
            "config": dict(config or {}),
            "manifest": manifest.to_dict(),
            "status": "installed",
        }
        self._installed[organ_id] = internal_record
        self._observe("plugin_install", organ_id, manifest, confidence=0.8)
        # Return defensive copy without exposing raw config
        return self._sanitize_record(internal_record)
    
    def _sanitize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return a safe copy of a record without exposing sensitive config fields."""
        return {
            "organ_id": record.get("organ_id"),
            "installed_at": record.get("installed_at"),
            "manifest": dict(record.get("manifest", {})),  # Defensive copy
            "status": record.get("status"),
        }

    def uninstall(self, organ_id: str, *, reason: str = "") -> dict[str, Any]:
        if organ_id not in self._installed:
            raise ValueError(f"organ '{organ_id}' is not installed")
        record = self._installed.pop(organ_id)
        record["status"] = "uninstalled"
        record["uninstalled_at"] = time.time()
        record["reason"] = reason
        self._observe("plugin_uninstall", organ_id, self._manifests.get(organ_id), confidence=0.6)
        # Return defensive copy without exposing raw config
        return self._sanitize_record(record)

    def is_installed(self, organ_id: str) -> bool:
        return organ_id in self._installed

    def installed_organs(self) -> list[dict[str, Any]]:
        return [self._sanitize_record(record) for record in self._installed.values()]

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def permission_audit(self) -> dict[str, Any]:
        """Audit all registered organs for permission risk."""
        per_organ = []
        max_risk = 0.0
        for organ_id, manifest in self._manifests.items():
            risk = manifest.permission_risk()
            max_risk = max(max_risk, risk)
            denied = sorted(set(manifest.required_permissions) & DENIED_PERMISSIONS)
            per_organ.append(
                {
                    "organ_id": organ_id,
                    "risk_score": risk,
                    "denied_permissions_requested": denied,
                    "installed": organ_id in self._installed,
                }
            )
        return {
            "version": AURA_PLUGIN_REGISTRY_VERSION,
            "max_permission_risk": round(max_risk, 4),
            "organs": per_organ,
            "denied_permissions_policy": sorted(DENIED_PERMISSIONS),
            "ts": time.time(),
        }

    # ------------------------------------------------------------------
    # QDKT
    # ------------------------------------------------------------------

    def _observe(self, event_type: str, organ_id: str, manifest: AuraPluginManifest | None, *, confidence: float) -> None:
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                event_type,
                {
                    "organ_id": organ_id,
                    "domain": manifest.domain if manifest else "unknown",
                    "risk_score": manifest.permission_risk() if manifest else 1.0,
                },
                rationale=f"plugin {event_type}: {organ_id}",
                concept=f"plugin:{organ_id}",
                confidence=confidence,
            )
        except Exception:
            pass

    def record_reliability(self, organ_id: str, *, success: bool, latency_ms: float = 0.0) -> None:
        """Record an organ reliability observation in QDKT."""
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                "plugin_reliability",
                {
                    "organ_id": organ_id,
                    "success": bool(success),
                    "latency_ms": float(latency_ms),
                },
                rationale=f"organ {organ_id} reliability sample",
                concept=f"plugin_reliability:{organ_id}",
                confidence=0.8 if success else 0.4,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Default organ manifests
# ---------------------------------------------------------------------------

def build_default_registry(*, qdkt: Any = None) -> AuraPluginRegistry:
    """Build the canonical registry with all eleven Aura organs."""
    registry = AuraPluginRegistry(qdkt=qdkt)

    registry.register(
        AuraPluginManifest(
            organ_id="core",
            domain="core",
            entry_module="aura_substrate",
            description="LLM-free deterministic substrate: intent compression, context selection, guardrails.",
            required_permissions=("read_codemap", "read_guardrails"),
            provided_tools=(),
            sidecar_tables=(),
            verifier_gates=("ast_parse",),
            boundary_invariant="substrate never invokes a model; egress is the single external point",
            arena_adapter="",
            risk_score=0.05,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="qdkt",
            domain="qdkt",
            entry_module="aura_qdkt",
            description="Unified knowledge tracing hub: observe, query, crystallize.",
            required_permissions=("read_knowledge_index", "write_knowledge_index", "read_crystal_cache"),
            provided_tools=("query_qdkt", "observe_retrieval_usefulness"),
            sidecar_tables=("qdkt_knowledge_index", "qdkt_crystal_cache", "qdkt_retrieval_usefulness"),
            verifier_gates=("concept_hash",),
            boundary_invariant="QDKT remembers; it never mutates production or bypasses verifiers",
            arena_adapter="",
            risk_score=0.15,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="dream",
            domain="dream",
            entry_module="aura_dream_retrieval",
            description="DREAM-lite retrieval usefulness reranker.",
            required_permissions=("read_candidates", "write_dream_ledger"),
            provided_tools=("observe_retrieval_usefulness",),
            sidecar_tables=("qdkt_retrieval_usefulness",),
            verifier_gates=("verifier_result",),
            boundary_invariant="DREAM ranks usefulness; sidecar/file/provenance truth is never overwritten",
            arena_adapter="",
            risk_score=0.12,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="travel",
            domain="travel",
            entry_module="travel_package_arena",
            description="Sidecar-aware travel package arena with VSA pointer resolution and price verifier.",
            required_permissions=("read_sidecar", "read_vsa_pointers", "verify_prices"),
            provided_tools=("build_travel_package", "verify_sidecar_truth"),
            sidecar_tables=("resorts", "price_observations", "vsa_entity_pointers", "raw_snapshots"),
            verifier_gates=("price_freshness", "booking_payment", "legal_travel"),
            boundary_invariant="VSA maps meaning; sidecar stores exact truth; verifier blocks stale/vector-only prices",
            arena_adapter="TravelArenaAdapter",
            risk_score=0.35,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="social",
            domain="social",
            entry_module="aura_mcp_gateway",
            description="Social luminance scanner returning redacted semantic references.",
            required_permissions=("read_social_signals", "rank_references"),
            provided_tools=("scan_social_luminance",),
            sidecar_tables=("social_posts",),
            verifier_gates=("post_provenance",),
            boundary_invariant="social truth remains in sidecar posts; VSA maps meaning; no raw private post export",
            arena_adapter="",
            risk_score=0.30,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="fintech",
            domain="fintech",
            entry_module="aura_mcp_gateway",
            description="Fintech ledger verifier for provenance, freshness, and balance integrity.",
            required_permissions=("read_ledger", "verify_balances"),
            provided_tools=("verify_fintech_ledger",),
            sidecar_tables=("ledger_entries",),
            verifier_gates=("balance_integrity", "provenance"),
            boundary_invariant="ledger truth remains in sidecar; verifier blocks invalid entries; human approval required",
            arena_adapter="",
            risk_score=0.40,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="civic",
            domain="civic",
            entry_module="aura_liquid_planning_arena",
            description="Civic intervention planning arena.",
            required_permissions=("read_civic_data", "propose_interventions"),
            provided_tools=("run_arena",),
            sidecar_tables=("neighborhoods", "services", "funding"),
            verifier_gates=("legal_constraint", "funding_constraint", "governance"),
            boundary_invariant="civic arena proposes interventions; it cannot claim legal approval or allocate funding",
            arena_adapter="CivicArenaAdapter",
            risk_score=0.25,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="code",
            domain="code",
            entry_module="aura_architect_loop",
            description="Code refactor arena: plan, ground, shadow, verify, hotswap, rollback, ledger.",
            required_permissions=("read_codemap", "read_files", "stage_patches", "verify_tests"),
            provided_tools=("run_arena", "stage_action_capsule"),
            sidecar_tables=(),
            verifier_gates=("ast_parse", "test_run", "boundary_contract", "shadow_report"),
            boundary_invariant="Architect loop: plan->ground->shadow->verify->judge->hotswap; no direct production mutation",
            arena_adapter="CodeArenaAdapter",
            risk_score=0.45,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="icm",
            domain="icm",
            entry_module="aura_icm_workspace",
            description="ICM audit/edit/review workspace control surface.",
            required_permissions=("read_arena", "write_audit_workspace"),
            provided_tools=("export_icm_workspace",),
            sidecar_tables=(),
            verifier_gates=("verifier_report",),
            boundary_invariant="ICM stores references and audit artifacts; exact truth remains in sidecars",
            arena_adapter="",
            risk_score=0.10,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="graph",
            domain="graph",
            entry_module="aura_understand_graph_bridge",
            description="Knowledge graph bridge for topology and concept linking.",
            required_permissions=("read_graph", "read_topology"),
            provided_tools=(),
            sidecar_tables=("graph_nodes", "graph_edges"),
            verifier_gates=("topology_resonance",),
            boundary_invariant="graph maps meaning; sidecar stores exact truth; no raw graph dump export",
            arena_adapter="",
            risk_score=0.18,
        )
    )
    registry.register(
        AuraPluginManifest(
            organ_id="federation",
            domain="federation",
            entry_module="aura_federation",
            description="Sovereignty-first federation of redacted signed capsules.",
            required_permissions=("sign_capsules", "verify_remote_capsules", "record_trust"),
            provided_tools=(),
            sidecar_tables=("federation_trust",),
            verifier_gates=("local_verifier", "signature_check"),
            boundary_invariant="redacted signed capsules only; no raw private memory; remote results pass local verifier",
            arena_adapter="",
            risk_score=0.50,
        )
    )
    return registry


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura Plugin Registry — list installable organs")
    parser.add_argument("--list", action="store_true", help="list registered organs")
    parser.add_argument("--audit", action="store_true", help="print permission audit")
    args = parser.parse_args(argv)
    registry = build_default_registry()
    if args.audit:
        print(json.dumps(registry.permission_audit(), indent=2, sort_keys=True))
    elif args.list:
        print(json.dumps(registry.list_organs(), indent=2, sort_keys=True))
    else:
        print(f"Aura Plugin Registry: {len(registry.list_organs())} organs registered")
        for organ in registry.list_organs():
            print(f"  - {organ['organ_id']}: {organ['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())