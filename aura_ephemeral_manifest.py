"""
Aura Ephemeral Organ Manifest — deterministic, digestible manifest dataclasses.

The manifest is the authoritative specification for a temporary organ.
It must be deterministic and digestible. No API keys or unrestricted prompts.

Dependencies: stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MANIFEST_VERSION = "AURA_EPHEMERAL_ORGAN_V1"


@dataclass
class EphemeralCapabilityRequest:
    capability: str
    requested: bool = True
    granted: bool = False
    denied_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EphemeralResourceBudget:
    wall_time_ms: int = 30000
    memory_mb: int = 256
    output_bytes: int = 1_000_000
    tool_calls: int = 20
    model_calls: int = 0
    cost_usd: float = 0.0
    network_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EphemeralComponentRef:
    component_id: str
    kind: str  # builtin_adapter | wasm_component
    content_digest: str
    source: str
    allowed_imports: list[str] = field(default_factory=list)
    allowed_exports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EphemeralUIManifest:
    component_types: list[str] = field(default_factory=list)
    schema: dict[str, Any] = field(default_factory=dict)
    executable: bool = False  # Must always be False for MVP — declarative JSON only

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EphemeralOrganManifest:
    manifest_version: str = MANIFEST_VERSION
    organ_id: str = ""
    objective: str = ""
    objective_hash: str = ""
    creator: str = "human"
    created_at: float = 0.0
    ttl_seconds: int = 300
    expires_at: float = 0.0

    intent_packet: dict[str, Any] = field(default_factory=dict)
    lexc_route: list[str] = field(default_factory=list)
    machine_route: dict[str, Any] = field(default_factory=dict)
    capability_resolution_ref: str = ""
    capability_resolution_digest: str = ""

    requested_capabilities: list[dict[str, Any]] = field(default_factory=list)
    granted_capabilities: list[str] = field(default_factory=list)
    denied_capabilities: list[dict[str, Any]] = field(default_factory=list)
    boundary_contracts: list[dict[str, Any]] = field(default_factory=list)
    arena_lease: dict[str, Any] = field(default_factory=dict)

    components: list[dict[str, Any]] = field(default_factory=list)
    resource_budget: dict[str, Any] = field(default_factory=dict)
    data_policy: dict[str, Any] = field(default_factory=dict)
    ui_manifest: dict[str, Any] = field(default_factory=dict)

    verifier_requirements: dict[str, Any] = field(default_factory=dict)
    human_approval_policy: str = "required_for_consequential"
    dissolution_policy: str = "mandatory"
    crystallization_policy: str = "proposal_only"
    phase_hash: str = ""
    signature_or_digest: str = ""

    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compute_digest(self) -> str:
        """Compute deterministic blake2b digest of the manifest (excluding volatile fields)."""
        d = self.to_dict()
        # Exclude volatile fields that change per creation
        for key in ("created_at", "expires_at", "phase_hash", "signature_or_digest"):
            d.pop(key, None)
        payload = json.dumps(d, sort_keys=True, default=str)
        return hashlib.blake2b(payload.encode(), digest_size=16).hexdigest()

    def verify_digest(self, expected: str) -> bool:
        return self.compute_digest() == expected


@dataclass
class EphemeralOrganReceipt:
    receipt_version: str = "AURA_EPHEMERAL_RECEIPT_V1"
    organ_id: str = ""
    manifest_digest: str = ""
    state: str = ""
    dissolved: bool = False
    dissolved_at: float = 0.0
    capabilities_revoked: list[str] = field(default_factory=list)
    temp_dir_removed: bool = False
    temp_dir_path: str = ""
    audit_artifacts: list[str] = field(default_factory=list)
    cost_record: dict[str, Any] = field(default_factory=dict)
    verifier_result: dict[str, Any] = field(default_factory=dict)
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_manifest(
    objective: str,
    *,
    organ_id: str = "",
    ttl_seconds: int = 300,
    creator: str = "human",
    requested_capabilities: list[str] | None = None,
    repo_root: str = ".",
) -> EphemeralOrganManifest:
    """Create an EphemeralOrganManifest with defaults for the MVP read-only organ."""
    now = time.time()
    obj_hash = hashlib.blake2b(objective.encode(), digest_size=12).hexdigest()
    organ_id = organ_id or f"EORG-{obj_hash[:12]}"

    # MVP: only read-only capabilities are allowed
    mvp_allowed = {
        "resolve_capabilities", "search_code", "inspect_symbol", "read_slice",
        "rank_regions", "build_change_graph", "show_tests", "show_docs",
        "render_ui_schema", "write_temp_audit", "emit_telemetry", "dissolve",
    }
    mvp_forbidden = {
        "external_network", "package_install", "shell", "arbitrary_subprocess",
        "host_write_outside_temp", "production_mutation", "secret_access",
        "raw_private_memory", "commit", "push", "pr", "booking_payment",
        "permanent_plugin_install", "automatic_crystallization",
    }

    cap_requests: list[dict[str, Any]] = []
    granted: list[str] = []
    denied: list[dict[str, Any]] = []
    for cap in (requested_capabilities or list(mvp_allowed)):
        if cap in mvp_allowed:
            cap_requests.append({"capability": cap, "requested": True, "granted": True, "denied_reason": ""})
            granted.append(cap)
        elif cap in mvp_forbidden:
            cap_requests.append({"capability": cap, "requested": True, "granted": False, "denied_reason": "forbidden_in_mvp"})
            denied.append({"capability": cap, "reason": "forbidden_in_mvp"})
        else:
            cap_requests.append({"capability": cap, "requested": True, "granted": False, "denied_reason": "unknown_capability"})
            denied.append({"capability": cap, "reason": "unknown_capability"})

    manifest = EphemeralOrganManifest(
        organ_id=organ_id,
        objective=objective,
        objective_hash=obj_hash,
        creator=creator,
        created_at=now,
        ttl_seconds=ttl_seconds,
        expires_at=now + ttl_seconds,
        requested_capabilities=cap_requests,
        granted_capabilities=granted,
        denied_capabilities=denied,
        resource_budget=asdict(EphemeralResourceBudget(network_calls=0)),
        data_policy={
            "readable_paths": [".aura/CODEMAP.json", ".aura/CODEMAP.md", ".aura/MODULE_MANIFEST.json"],
            "writable_temp_paths": [],  # Set during sandbox preparation
            "forbidden_paths": [".env", ".git/credentials", "*/secrets*", "*/.key"],
            "private_memory_export": False,
            "raw_sidecar_dump": False,
            "secrets_access": False,
        },
        ui_manifest=asdict(EphemeralUIManifest(
            component_types=[
                "objective_header", "existing_capability_cards", "exact_function_table",
                "relationship_graph", "tests_and_docs_panel", "safety_constraints",
                "missing_capability_panel", "cost_telemetry", "lifecycle_status", "dissolve_control",
            ],
            schema={},
            executable=False,
        )),
        verifier_requirements={
            "must_pass": ["no_production_mutation", "no_secret_access", "no_network_access"],
            "quality_gate": "advisory_for_read_only",
        },
        patch_authority=PATCH_AUTHORITY,
        vsa_patch_authority=VSA_PATCH_AUTHORITY,
    )
    manifest.phase_hash = manifest.compute_digest()
    return manifest
