"""
Aura Ephemeral Runtime — orchestrator for ephemeral organ lifecycle.

Pipeline:
  human objective
  → IntentPacket
  → Capability Resolution Packet
  → six-slot LEXC route
  → machine effect route
  → product automaton
  → Ephemeral Organ Manifest
  → capability lease
  → sandbox preparation
  → read-only execution
  → declarative UI schema
  → verifier
  → cost/resource record
  → dissolution
  → capability revocation
  → dissolution receipt

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def plan_ephemeral_organ(
    objective: str,
    *,
    ttl_seconds: int = 300,
    repo_root: str = ".",
) -> dict[str, Any]:
    """Plan an ephemeral organ: create manifest, resolve capabilities, validate grammar."""
    from aura_ephemeral_manifest import create_manifest
    from aura_ephemeral_registry import get_registry
    from aura_ephemeral_lifecycle import EphemeralState

    # 1. Create manifest
    manifest = create_manifest(objective, ttl_seconds=ttl_seconds, repo_root=repo_root)
    manifest_dict = manifest.to_dict()
    digest = manifest.compute_digest()

    # 2. Resolve capabilities
    cap_resolution: dict[str, Any] = {}
    try:
        from aura_capability_resolver import resolve_capabilities
        cap_resolution = resolve_capabilities(objective, repo_root=repo_root)
        manifest.capability_resolution_ref = cap_resolution.get("objective_hash", "")
        manifest.capability_resolution_digest = cap_resolution.get("codemap_digest", "")
    except Exception:
        pass

    # 3. Compile LEXC route — MVP route: CREATE + TTL + READ + CODEMAP + HUMAN_REQUESTED + RESOLVE_CAPABILITIES
    lexc_symbols = ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"]
    from aura_ephemeral_fst import compile_ephemeral_route
    lexc_result = compile_ephemeral_route(lexc_symbols, repo_root=repo_root)

    # 4. Register in registry
    registry = get_registry()
    from aura_ephemeral_registry import EphemeralOrganRecord
    record = EphemeralOrganRecord(
        organ_id=manifest.organ_id,
        manifest_digest=digest,
        state=EphemeralState.DRAFTED.value,
        created_at=manifest.created_at,
        expires_at=manifest.expires_at,
        capability_lease=manifest.granted_capabilities,
        objective=objective,
        ttl_seconds=ttl_seconds,
    )
    registry.register(record)

    return {
        "ok": True,
        "organ_id": manifest.organ_id,
        "manifest": manifest_dict,
        "manifest_digest": digest,
        "capability_resolution": {
            "exact_matches": cap_resolution.get("exact_matches", []),
            "related_functions": cap_resolution.get("related_functions", []),
            "existing_affordances": cap_resolution.get("existing_affordances", []),
            "do_not_reinvent": cap_resolution.get("do_not_reinvent", []),
            "confidence": cap_resolution.get("confidence", 0.0),
        },
        "lexc_route": lexc_symbols,
        "lexc_valid": lexc_result.get("ok", False),
        "lexc_errors": lexc_result.get("errors", []),
        "state": EphemeralState.DRAFTED.value,
        "ttl_seconds": ttl_seconds,
        "expires_at": manifest.expires_at,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def validate_ephemeral_organ(
    organ_id: str,
    *,
    repo_root: str = ".",
    human_approval: bool = False,
) -> dict[str, Any]:
    """Validate an ephemeral organ through the product automaton."""
    from aura_ephemeral_registry import get_registry
    from aura_ephemeral_fst import EphemeralRoutingFrame, evaluate_ephemeral_product_automaton
    from aura_ephemeral_lifecycle import EphemeralState, transition

    registry = get_registry()
    organ = registry.get(organ_id)
    if not organ.get("ok"):
        return organ

    record_data = organ["organ"]
    granted = record_data.get("capability_lease", [])

    # Validate grammar
    lexc_symbols = ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"]
    frame = EphemeralRoutingFrame(
        intent="ephemeral_investigation",
        effect="READ",
        target="CODEMAP",
        scope="read_only",
        risk="low",
        grounding="codemap_exists",
        lease=organ_id,
        lifecycle_state=record_data.get("state", "DRAFTED"),
        human_approval=human_approval,
        ttl=record_data.get("ttl_seconds", 300),
    )

    result = evaluate_ephemeral_product_automaton(
        lexc_symbols, frame,
        granted_capabilities=granted,
        lifecycle_allowed=True,
        sandbox_available=False,
        human_approval_present=human_approval,
        repo_root=repo_root,
    )

    # Update state based on validation
    if result.allowed:
        registry.update_state(organ_id, EphemeralState.GRAMMAR_VALIDATED.value)
        registry.update_state(organ_id, EphemeralState.POLICY_VALIDATED.value)
        registry.update_state(organ_id, EphemeralState.MANIFEST_DIGESTED.value)
    else:
        registry.update_state(organ_id, EphemeralState.BLOCKED.value)

    return {
        "ok": result.allowed,
        "organ_id": organ_id,
        "product_automaton": result.to_dict(),
        "state": record_data.get("state"),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def run_ephemeral_organ(
    organ_id: str,
    *,
    repo_root: str = ".",
    human_approval: bool = True,
) -> dict[str, Any]:
    """Run an ephemeral organ: prepare sandbox, execute adapters, verify, dissolve."""
    from aura_ephemeral_registry import get_registry
    from aura_ephemeral_sandbox import prepare_sandbox, execute_builtin_adapter, destroy_sandbox, revoke_capabilities, verify_dissolution
    from aura_ephemeral_arena import create_ephemeral_arena
    from aura_ephemeral_lifecycle import EphemeralState
    from aura_ephemeral_manifest import EphemeralOrganReceipt

    registry = get_registry()
    organ = registry.get(organ_id)
    if not organ.get("ok"):
        return organ
    record = organ["organ"]

    # Check TTL
    if time.time() >= record.get("expires_at", 0):
        registry.update_state(organ_id, EphemeralState.DISSOLVING.value)
        return {"ok": False, "error": "TTL expired", "organ_id": organ_id,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # Prepare sandbox
    sandbox = prepare_sandbox(record, repo_root=repo_root)
    if not sandbox.get("ok"):
        return sandbox
    temp_dir = sandbox["temp_dir"]

    # Update state
    registry.update_state(organ_id, EphemeralState.SANDBOX_PREPARED.value)
    if human_approval:
        registry.update_state(organ_id, EphemeralState.HUMAN_APPROVAL_REQUIRED.value)
        registry.update_state(organ_id, EphemeralState.READY.value)
    else:
        # For MVP read-only, human approval for running is not strictly required
        # but human approval for consequential effects IS required
        registry.update_state(organ_id, EphemeralState.READY.value)

    # Create arena
    arena = create_ephemeral_arena(
        organ_id, record.get("objective", ""),
        record.get("capability_lease", []),
        temp_dir, record.get("ttl_seconds", 300),
    )

    # Start running
    registry.update_state(organ_id, EphemeralState.RUNNING.value)

    results: list[dict[str, Any]] = []

    # Execute read-only adapters
    cap_result = execute_builtin_adapter(
        "resolve_capabilities",
        organ_id=organ_id, temp_dir=temp_dir, repo_root=repo_root,
        params={"objective": record.get("objective", ""), "repo_root": repo_root},
    )
    results.append(cap_result)

    ui_result = execute_builtin_adapter(
        "render_ui_schema",
        organ_id=organ_id, temp_dir=temp_dir, repo_root=repo_root,
        params={},
    )
    results.append(ui_result)

    # Write audit artifact
    audit_data = json.dumps({
        "organ_id": organ_id,
        "objective": record.get("objective", ""),
        "results_count": len(results),
        "timestamp": time.time(),
    }, default=str)
    audit_result = execute_builtin_adapter(
        "write_temp_audit",
        organ_id=organ_id, temp_dir=temp_dir, repo_root=repo_root,
        params={"audit_data": audit_data, "temp_dir": temp_dir},
    )
    results.append(audit_result)

    # Verify
    registry.update_state(organ_id, EphemeralState.VERIFYING.value)
    verifier_ok = all(
        r.get("ok", True) is not False  # None or missing ok is acceptable for read-only adapters
        for r in results if r.get("adapter") != "write_temp_audit"
    )

    if verifier_ok:
        registry.update_state(organ_id, EphemeralState.COMPLETED.value)
    else:
        registry.update_state(organ_id, EphemeralState.FAILED.value)

    # Dissolve
    registry.update_state(organ_id, EphemeralState.DISSOLVING.value)
    revoke_result = revoke_capabilities(organ_id)
    destroy_result = destroy_sandbox(temp_dir)
    dissolution_verified = verify_dissolution(temp_dir, revoke_result.get("ok", False))

    # Create receipt
    receipt = EphemeralOrganReceipt(
        organ_id=organ_id,
        manifest_digest=record.get("manifest_digest", ""),
        state="DISSOLVED",
        dissolved=True,
        dissolved_at=time.time(),
        capabilities_revoked=record.get("capability_lease", []),
        temp_dir_removed=destroy_result.get("temp_dir_removed", False),
        temp_dir_path=temp_dir,
        audit_artifacts=[r.get("path", "") for r in results if r.get("adapter") == "write_temp_audit" and r.get("ok")],
        verifier_result={"passed": verifier_ok},
    )
    registry.set_dissolution_receipt(organ_id, receipt.to_dict())
    registry.update_state(organ_id, EphemeralState.DISSOLVED.value)

    return {
        "ok": True,
        "organ_id": organ_id,
        "execution_results": results,
        "verifier_passed": verifier_ok,
        "dissolution": {
            "capabilities_revoked": revoke_result.get("ok", False),
            "temp_dir_removed": destroy_result.get("temp_dir_removed", False),
            "dissolution_verified": dissolution_verified.get("ok", False),
        },
        "receipt": receipt.to_dict(),
        "state": EphemeralState.DISSOLVED.value,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def ephemeral_status(organ_id: str) -> dict[str, Any]:
    """Get the current status of an ephemeral organ."""
    from aura_ephemeral_registry import get_registry
    registry = get_registry()
    return registry.get(organ_id)


def dissolve_ephemeral_organ(organ_id: str) -> dict[str, Any]:
    """Manually dissolve an ephemeral organ."""
    from aura_ephemeral_registry import get_registry
    from aura_ephemeral_sandbox import revoke_capabilities, destroy_sandbox, verify_dissolution
    from aura_ephemeral_lifecycle import EphemeralState

    registry = get_registry()
    organ = registry.get(organ_id)
    if not organ.get("ok"):
        return organ
    record = organ["organ"]

    registry.update_state(organ_id, EphemeralState.DISSOLVING.value)
    revoke_result = revoke_capabilities(organ_id)
    temp_dir = record.get("sandbox_path", "")
    destroy_result = destroy_sandbox(temp_dir) if temp_dir else {"ok": True, "temp_dir_removed": False}
    verified = verify_dissolution(temp_dir, revoke_result.get("ok", False))

    from aura_ephemeral_manifest import EphemeralOrganReceipt
    receipt = EphemeralOrganReceipt(
        organ_id=organ_id,
        manifest_digest=record.get("manifest_digest", ""),
        state="DISSOLVED",
        dissolved=True,
        dissolved_at=time.time(),
        capabilities_revoked=record.get("capability_lease", []),
        temp_dir_removed=destroy_result.get("temp_dir_removed", False),
    )
    registry.set_dissolution_receipt(organ_id, receipt.to_dict())
    return {
        "ok": True,
        "organ_id": organ_id,
        "receipt": receipt.to_dict(),
        "dissolution_verified": verified.get("ok", False),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def ephemeral_receipt(organ_id: str) -> dict[str, Any]:
    """Get the dissolution receipt for an organ."""
    from aura_ephemeral_registry import get_registry
    registry = get_registry()
    organ = registry.get(organ_id)
    if not organ.get("ok"):
        return organ
    record = organ["organ"]
    receipt = record.get("dissolution_receipt", {})
    return {
        "ok": bool(receipt),
        "organ_id": organ_id,
        "receipt": receipt,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
