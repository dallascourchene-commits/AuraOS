"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f0-[Q-SYS:AURA_MCP_GATEWAY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIWAABAMIN (Transparency & Privacy / Aura-Safe Tool Surface)
DEPENDENCIES: dataclasses, hashlib, json, time, typing
FUNCTIONS: AuraMCPTool, AuraMCPToolResult, AuraMCPGateway, build_default_gateway
SYNOPSIS: Aura-safe MCP tool gateway. Exposes exactly nine read/proposal tools that
          delegate to existing Arena, sidecar, verifier, QDKT, ICM, and travel package
          surfaces. No tool mutates production. Every call is logged to QDKT. No raw
          sidecar dumps or raw private memory may leave the gateway.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
import json
import time
from typing import Any

AURA_MCP_GATEWAY_VERSION = "AURA_MCP_GATEWAY_V1"

# Hard denylist of effects no Aura-safe tool may produce.
FORBIDDEN_EFFECTS_DENYLIST = frozenset(
    {
        "mutate_production",
        "bypass_verifier",
        "bypass_shadow",
        "bypass_judge",
        "bypass_architect",
        "raw_sidecar_dump",
        "raw_private_memory_export",
        "book_without_approval",
        "invent_prices",
        "vector_only_price",
    }
)

# The exact nine Aura-safe tools required by the meta-harness spec.
AURA_SAFE_TOOLS = (
    "run_arena",
    "stage_action_capsule",
    "verify_sidecar_truth",
    "query_qdkt",
    "observe_retrieval_usefulness",
    "export_icm_workspace",
    "build_travel_package",
    "scan_social_luminance",
    "verify_fintech_ledger",
)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class AuraMCPTool:
    """Descriptor for one Aura-safe MCP tool."""

    tool_name: str
    description: str
    required_inputs: tuple[str, ...]
    forbidden_effects: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    handler: Callable[..., dict[str, Any]]
    domain: str = "generic"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "domain": self.domain,
            "required_inputs": list(self.required_inputs),
            "forbidden_effects": list(self.forbidden_effects),
            "allowed_effects": list(self.allowed_effects),
            "metadata": dict(self.metadata),
        }


@dataclass
class AuraMCPToolResult:
    """Result of one MCP tool invocation."""

    tool_name: str
    ok: bool
    result: dict[str, Any]
    error: str | None
    phase_hash: str
    ts: float
    aura_safe: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": AURA_MCP_GATEWAY_VERSION,
            "tool_name": self.tool_name,
            "ok": self.ok,
            "result": dict(self.result),
            "error": self.error,
            "phase_hash": self.phase_hash,
            "ts": self.ts,
            "aura_safe": self.aura_safe,
        }


def _assert_aura_safe(tool: AuraMCPTool) -> None:
    """Reject any tool whose *allowed* effects overlap the denylist.

    ``forbidden_effects`` is the tool's safety promise of what it will NOT do,
    so those are encouraged. ``allowed_effects`` is what the tool may actually
    produce, so those must never include a denied effect.
    """
    if tool.tool_name not in AURA_SAFE_TOOLS:
        raise ValueError(f"Tool '{tool.tool_name}' is not in the Aura-safe tool set")
    bad = set(tool.allowed_effects) & FORBIDDEN_EFFECTS_DENYLIST
    if bad:
        raise ValueError(f"Aura-unsafe tool '{tool.tool_name}' allows denied effects: {sorted(bad)}")


class AuraMCPGateway:
    """Aura-safe MCP tool gateway.

    Exposes exactly the nine Aura-safe tools. Every call is logged to QDKT
    (if a QDKT instance is provided). No tool may mutate production, bypass a
    verifier, or export raw sidecar/private memory.
    """

    def __init__(self, *, qdkt: Any = None, node_ref: Any = None) -> None:
        self.qdkt = qdkt
        self.node_ref = node_ref
        self._tools: dict[str, AuraMCPTool] = {}
        self._call_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: AuraMCPTool) -> None:
        _assert_aura_safe(tool)
        if tool.tool_name in self._tools:
            raise ValueError(f"Tool '{tool.tool_name}' is already registered")
        self._tools[tool.tool_name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def call(self, tool_name: str, arguments: dict[str, Any]) -> AuraMCPToolResult:
        ts = time.time()
        
        # Early type check: arguments must be a dict-like mapping
        if not isinstance(arguments, dict):
            result = AuraMCPToolResult(
                tool_name=tool_name,
                ok=False,
                result={},
                error=f"malformed arguments: expected dict, got {type(arguments).__name__}",
                phase_hash="",
                ts=ts,
                aura_safe=False,
            )
            self._record_call(result)
            return result
        
        tool = self._tools.get(tool_name)
        if tool is None:
            result = AuraMCPToolResult(
                tool_name=tool_name,
                ok=False,
                result={},
                error=f"unknown tool: {tool_name}",
                phase_hash="",
                ts=ts,
                aura_safe=False,
            )
            self._record_call(result)
            return result

        missing = [key for key in tool.required_inputs if key not in arguments]
        if missing:
            result = AuraMCPToolResult(
                tool_name=tool_name,
                ok=False,
                result={},
                error=f"missing required inputs: {missing}",
                phase_hash="",
                ts=ts,
                aura_safe=True,
            )
            self._record_call(result)
            return result

        try:
            payload = tool.handler(arguments, qdkt=self.qdkt, node_ref=self.node_ref)
            if not isinstance(payload, dict):
                raise ValueError("tool handler must return a dict")
            phase_hash = _hash_payload({"tool": tool_name, "result": payload, "ts": ts})
            result = AuraMCPToolResult(
                tool_name=tool_name,
                ok=True,
                result=payload,
                error=None,
                phase_hash=phase_hash,
                ts=ts,
                aura_safe=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = AuraMCPToolResult(
                tool_name=tool_name,
                ok=False,
                result={},
                error=str(exc)[:512],
                phase_hash="",
                ts=ts,
                aura_safe=True,
            )
            self._record_call(result, failure=True)
            return result

        self._record_call(result)
        return result

    # ------------------------------------------------------------------
    # QDKT logging
    # ------------------------------------------------------------------

    def _record_call(self, result: AuraMCPToolResult, *, failure: bool = False) -> None:
        row = result.to_dict()
        self._call_log.append(row)
        if self.qdkt is not None:
            try:
                self.qdkt.observe(
                    "mcp_tool_failure" if failure else "mcp_tool_call",
                    {
                        "tool_name": result.tool_name,
                        "ok": result.ok,
                        "error": result.error,
                        "phase_hash": result.phase_hash,
                    },
                    rationale=f"MCP tool {result.tool_name} {'failed' if failure else 'called'}",
                    concept=f"mcp:{result.tool_name}",
                    confidence=0.4 if failure else 0.8,
                )
            except Exception:
                pass

    def call_log(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._call_log[-limit:])


# ---------------------------------------------------------------------------
# Default Aura-safe tool handlers
# ---------------------------------------------------------------------------

def _handler_run_arena(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Delegate to a Liquid Planning Arena adapter to build an arena proposal."""
    from aura_liquid_planning_arena import ARENA_ADAPTERS  # lazy import

    domain = str(args.get("domain") or "code")
    objective = str(args.get("objective") or "")
    adapter_cls = ARENA_ADAPTERS.get(domain)
    if adapter_cls is None:
        raise ValueError(f"no Arena adapter for domain '{domain}'")
    adapter = adapter_cls()
    capsule = adapter.action_capsule_from_intent(
        objective=objective,
        capsule_id=str(args.get("capsule_id") or f"MCP-ARENA-{_hash_payload(args)[:8]}"),
        target=args.get("target") or {},
        constraints=args.get("constraints") or [],
    )
    return {
        "arena_domain": domain,
        "adapter_schema": adapter.schema(),
        "action_capsule": capsule.to_dict(),
        "status": "proposed",
        "invariant": "models propose, Arena stages, Shadow critiques, Judge decides, verifier proves, human approves",
    }


def _handler_stage_action_capsule(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Stage a proposed ActionCapsule into a shared queue reference (no production mutation)."""
    capsule = dict(args.get("capsule") or {})
    if not capsule:
        raise ValueError("stage_action_capsule requires a 'capsule' argument")
    
    # Validate capsule for denied effects and raw exports
    _validate_capsule_safety(capsule)
    
    # Return sanitized staged capsule without raw fields
    sanitized = dict(capsule)  # Make a copy
    raw_fields = {"raw_snapshot_bytes", "raw_sidecar_bytes", "raw_private_memory"}
    for field in raw_fields:
        sanitized.pop(field, None)
    
    staged = {
        "staged_capsule": sanitized,
        "status": "staged_proposal",
        "queue_ref": str(args.get("queue_ref") or "shared_action_queue"),
        "forbidden_actions": ["mutate_production", "bypass_verifier"],
        "requires_verifier_gate": True,
        "requires_human_approval": True,
    }
    return staged


def _validate_capsule_safety(capsule: dict[str, Any]) -> None:
    """Validate that a capsule doesn't include forbidden actions or raw exports."""
    # Check for raw export/mutation fields
    forbidden_fields = {"raw_snapshot_bytes", "raw_sidecar_bytes", "raw_private_memory"}
    capsule_keys = set(capsule.keys())
    if capsule_keys & forbidden_fields:
        raise ValueError(f"capsule contains forbidden raw fields: {capsule_keys & forbidden_fields}")
    
    # Check allowed_effects if present
    effects = capsule.get("allowed_effects", [])
    if isinstance(effects, (list, set)):
        bad = set(effects) & FORBIDDEN_EFFECTS_DENYLIST
        if bad:
            raise ValueError(f"capsule allows denied effects: {sorted(bad)}")


def _handler_verify_sidecar_truth(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Verify a sidecar-backed truth record (e.g. travel price) without dumping raw bytes."""
    domain = str(args.get("domain") or "travel")
    record = dict(args.get("record") or {})
    if not record:
        raise ValueError("verify_sidecar_truth requires a 'record' argument")
    if domain == "travel":
        from travel_price_verifier import TravelPriceVerifier  # lazy import

        verifier = TravelPriceVerifier()
        verification = verifier.verify_price(record)
        return verification.to_dict()
    # Generic verifier fallback: require provenance fields
    required = ("source_id", "snapshot_id", "observed_at", "freshness_status")
    blockers = [f"missing_{key}" for key in required if not record.get(key)]
    return {
        "version": "AURA_SIDECAR_TRUTH_VERIFIER_V1",
        "approved": not blockers,
        "blockers": blockers,
        "warnings": [],
        "domain": domain,
        "requires_live_recheck": True,
    }


def _handler_query_qdkt(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Query QDKT for a concept. Returns only safe concept references, never raw private memory."""
    if qdkt is None:
        raise ValueError("query_qdkt requires a QDKT instance")
    concept = str(args.get("concept") or "")
    if not concept:
        raise ValueError("query_qdkt requires a 'concept' argument")
    top_k = int(args.get("top_k") or 5)
    
    raw_result = qdkt.query(concept, top_k=top_k)
    
    # Redact and shape the result to expose only safe concept references
    # Filter out raw private memory and internal fields
    safe_response = {}
    if isinstance(raw_result, dict):
        # Only include approved fields
        approved_fields = {"concept", "results", "matches", "references", "confidence", "top_k", "domain"}
        for key in approved_fields:
            if key in raw_result:
                value = raw_result[key]
                # Recursively filter out forbidden fields from nested structures
                if isinstance(value, (list, dict)):
                    value = _redact_unsafe_response(value)
                safe_response[key] = value
    
    return safe_response


def _redact_unsafe_response(obj: Any) -> Any:
    """Recursively remove raw private memory and unsafe fields from query results."""
    forbidden_prefixes = {"raw_", "secret", "api_key", "password", "token", "private"}
    
    if isinstance(obj, dict):
        clean = {}
        for key, value in obj.items():
            # Skip keys that look like raw data or secrets
            if any(key.lower().startswith(p) for p in forbidden_prefixes):
                continue
            if any(p in key.lower() for p in forbidden_prefixes):
                continue
            clean[key] = _redact_unsafe_response(value)
        return clean
    elif isinstance(obj, list):
        return [_redact_unsafe_response(item) for item in obj]
    else:
        return obj


def _handler_observe_retrieval_usefulness(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Record a DREAM-lite retrieval usefulness row via QDKT."""
    if qdkt is None:
        raise ValueError("observe_retrieval_usefulness requires a QDKT instance")
    score_row = dict(args.get("score_row") or {})
    if not score_row:
        raise ValueError("observe_retrieval_usefulness requires a 'score_row' argument")
    event_id = qdkt.observe_retrieval_usefulness(score_row)
    return {"event_id": event_id, "status": "recorded"}


def _handler_export_icm_workspace(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Export an Arena transaction to an ICM workspace (audit layer only)."""
    from aura_icm_workspace import export_arena_transaction  # lazy import
    import os
    from pathlib import Path

    txn = dict(args.get("txn") or {})
    if not txn:
        raise ValueError("export_icm_workspace requires a 'txn' argument")
    
    # Validate and constrain workspace_root
    base_root = Path("Aura_Memory/icm_workspaces").resolve()
    provided_root = str(args.get("workspace_root") or "Aura_Memory/icm_workspaces")
    
    # Reject absolute paths
    if os.path.isabs(provided_root):
        raise ValueError("workspace_root must be relative; absolute paths are not allowed")
    
    # Resolve the requested path and ensure it's within the base
    try:
        resolved_root = (base_root.parent / provided_root).resolve()
        if not str(resolved_root).startswith(str(base_root)):
            raise ValueError(f"workspace_root must be within {base_root}; escaping the boundary is not allowed")
        workspace_root = str(resolved_root)
    except (OSError, ValueError) as e:
        raise ValueError(f"invalid workspace_root: {e}") from e
    
    ref = export_arena_transaction(
        txn,
        workspace_root,
        domain=str(args.get("domain") or txn.get("domain") or "generic"),
        arena_id=str(args.get("arena_id") or txn.get("arena_id") or "unknown"),
        arena_version=str(args.get("arena_version") or txn.get("arena_version") or "unknown"),
        stages=args.get("stages"),
        verifier_report=args.get("verifier_report"),
        qdkt=qdkt,
        metadata=args.get("metadata"),
    )
    return {
        "workspace_path": ref.workspace_path,
        "txn_id": ref.txn_id,
        "domain": ref.domain,
        "arena_id": ref.arena_id,
        "status": "exported_audit_layer_only",
    }


def _handler_build_travel_package(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Build a verified travel package candidate from a VSA pointer."""
    from travel_package_arena import TravelPackageArena  # lazy import
    from travel_price_sidecar import TravelPriceSidecar  # lazy import

    vsa_id = str(args.get("vsa_id") or "")
    if not vsa_id:
        raise ValueError("build_travel_package requires a 'vsa_id' argument")
    traveler_intent = dict(args.get("traveler_intent") or {})
    sidecar = TravelPriceSidecar()
    arena = TravelPackageArena(sidecar)
    candidate = arena.build_candidate_from_vsa_id(vsa_id, traveler_intent=traveler_intent) if hasattr(
        arena, "build_candidate_from_vsa_id"
    ) else arena.build_candidate_from_vsa_price(vsa_id, traveler_intent=traveler_intent)
    return candidate.to_dict()


def _handler_scan_social_luminance(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Scan social luminance signals and return ranked, redacted references.

    This is a proposal-only surface: it returns semantic references and
    verifier-gated signals, never raw private posts or raw sidecar dumps.
    """
    query = str(args.get("query") or "")
    candidates = list(args.get("candidates") or [])
    ranked = sorted(candidates, key=lambda item: float(item.get("luminance_score", 0.0)), reverse=True)
    return {
        "version": "AURA_SOCIAL_LUMINANCE_SCAN_V1",
        "query": query,
        "ranked_references": [
            {
                "candidate_id": str(item.get("candidate_id") or _hash_payload(item)[:8]),
                "luminance_score": float(item.get("luminance_score", 0.0)),
                "semantic_tags": list(item.get("semantic_tags", [])),
                "truth_boundary": "social truth remains in sidecar posts; VSA maps meaning",
                "requires_verifier_gate": True,
            }
            for item in ranked[: int(args.get("top_k") or 10)]
        ],
        "forbidden_actions": ["raw_private_post_export", "bypass_verifier"],
        "status": "proposed",
    }


def _handler_verify_fintech_ledger(args: dict[str, Any], *, qdkt: Any, node_ref: Any) -> dict[str, Any]:
    """Verify a fintech ledger entry for provenance, freshness, and balance integrity."""
    entry = dict(args.get("entry") or {})
    if not entry:
        raise ValueError("verify_fintech_ledger requires an 'entry' argument")
    required = ("entry_id", "account_id", "amount_minor", "currency", "observed_at", "source_id")
    blockers: list[str] = []
    for key in required:
        if entry.get(key) in (None, ""):
            blockers.append(f"missing_{key}")
    # Balance integrity check
    debits = sum(int(item.get("amount_minor", 0)) for item in entry.get("debits", []) or [])
    credits = sum(int(item.get("amount_minor", 0)) for item in entry.get("credits", []) or [])
    if entry.get("amount_minor") is not None and abs(int(entry["amount_minor"]) - (credits - debits)) > 0:
        blockers.append("balance_mismatch")
    return {
        "version": "AURA_FINTECH_LEDGER_VERIFIER_V1",
        "approved": not blockers,
        "blockers": blockers,
        "warnings": [],
        "entry_id": entry.get("entry_id"),
        "requires_human_approval": True,
        "forbidden_actions": ["raw_sidecar_dump", "bypass_verifier"],
    }


def build_default_gateway(*, qdkt: Any = None, node_ref: Any = None) -> AuraMCPGateway:
    """Build the canonical Aura MCP gateway with all nine Aura-safe tools."""
    gateway = AuraMCPGateway(qdkt=qdkt, node_ref=node_ref)
    gateway.register(
        AuraMCPTool(
            tool_name="run_arena",
            description="Build an Arena action capsule proposal for a domain intent.",
            required_inputs=("objective",),
            forbidden_effects=("mutate_production", "bypass_verifier", "bypass_shadow"),
            allowed_effects=("propose_capsule", "stage_in_arena"),
            handler=_handler_run_arena,
            domain="arena",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="stage_action_capsule",
            description="Stage a proposed ActionCapsule into the shared action queue (no production mutation).",
            required_inputs=("capsule",),
            forbidden_effects=("mutate_production", "bypass_verifier", "bypass_judge"),
            allowed_effects=("stage_proposal",),
            handler=_handler_stage_action_capsule,
            domain="arena",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="verify_sidecar_truth",
            description="Verify a sidecar-backed truth record without dumping raw bytes.",
            required_inputs=("record",),
            forbidden_effects=("raw_sidecar_dump", "bypass_verifier"),
            allowed_effects=("verify", "block_stale"),
            handler=_handler_verify_sidecar_truth,
            domain="sidecar",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="query_qdkt",
            description="Query QDKT for concept references (never raw private memory).",
            required_inputs=("concept",),
            forbidden_effects=("raw_private_memory_export",),
            allowed_effects=("query_references",),
            handler=_handler_query_qdkt,
            domain="qdkt",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="observe_retrieval_usefulness",
            description="Record a DREAM-lite retrieval usefulness row in QDKT.",
            required_inputs=("score_row",),
            forbidden_effects=("bypass_verifier",),
            allowed_effects=("record_usefulness",),
            handler=_handler_observe_retrieval_usefulness,
            domain="dream",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="export_icm_workspace",
            description="Export an Arena transaction to an ICM audit workspace.",
            required_inputs=("txn",),
            forbidden_effects=("raw_sidecar_dump", "raw_private_memory_export"),
            allowed_effects=("export_audit_layer",),
            handler=_handler_export_icm_workspace,
            domain="icm",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="build_travel_package",
            description="Build a verified travel package candidate from a VSA pointer.",
            required_inputs=("vsa_id", "traveler_intent"),
            forbidden_effects=("book_without_approval", "invent_prices", "vector_only_price"),
            allowed_effects=("propose_package", "verify_price"),
            handler=_handler_build_travel_package,
            domain="travel",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="scan_social_luminance",
            description="Scan social luminance signals and return ranked redacted references.",
            required_inputs=("query",),
            forbidden_effects=("raw_private_memory_export", "bypass_verifier"),
            allowed_effects=("rank_references",),
            handler=_handler_scan_social_luminance,
            domain="social",
        )
    )
    gateway.register(
        AuraMCPTool(
            tool_name="verify_fintech_ledger",
            description="Verify a fintech ledger entry for provenance, freshness, and balance integrity.",
            required_inputs=("entry",),
            forbidden_effects=("raw_sidecar_dump", "bypass_verifier"),
            allowed_effects=("verify", "block_invalid"),
            handler=_handler_verify_fintech_ledger,
            domain="fintech",
        )
    )
    return gateway


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura MCP Gateway — list Aura-safe tools")
    parser.add_argument("--list", action="store_true", help="list registered tools")
    args = parser.parse_args(argv)
    gateway = build_default_gateway()
    if args.list:
        print(json.dumps(gateway.list_tools(), indent=2, sort_keys=True))
    else:
        print(f"Aura MCP Gateway: {len(gateway.list_tools())} Aura-safe tools registered")
        for tool in gateway.list_tools():
            print(f"  - {tool['tool_name']}: {tool['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())