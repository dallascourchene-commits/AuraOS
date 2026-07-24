from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "aura_agent_arena_bridge.py",
    '''            "stage_results": [],
            "hotswap_capsule": None,
        }
''',
    '''            "stage_results": [],
            "hotswap_capsule": None,
            "unified_execution_bindings": {},
        }
''',
)

replace_once(
    "aura_agent_arena_bridge.py",
    '''    # ------------------------------------------------------------------
    # Tool 3: aura_get_micro_context
    # ------------------------------------------------------------------
''',
    '''    # ------------------------------------------------------------------
    # Unified manufactured-memory / continuity compilation
    # ------------------------------------------------------------------

    def aura_compile_unified_execution(
        self,
        *,
        plan_phase_hash: str,
        task_id: str,
        contract: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Compile and retain one exact-owner model-relative execution binding."""
        try:
            from aura_unified_memory_continuity_toolchain import (
                compile_bridge_execution_binding,
                compile_continuity_owner_projections,
            )

            binding = compile_bridge_execution_binding(
                self,
                plan_phase_hash=plan_phase_hash,
                task_id=task_id,
                contract=contract,
            )
            session = self._require_session(plan_phase_hash)
            session.setdefault("unified_execution_bindings", {})[str(task_id)] = binding
            result = binding.to_dict()
            result["owner_projections"] = compile_continuity_owner_projections(binding)
            result.update(
                {
                    "ok": True,
                    "bridge_version": BRIDGE_VERSION,
                    "production_mutation": False,
                    "human_review_required": True,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                }
            )
            return result
        except (ArenaBridgeError, TypeError, ValueError) as exc:
            return make_error_packet(
                "unified_memory_continuity_compile_failed",
                str(exc),
                repair_hint="Refresh exact Bridge evidence and recompile the bounded contract.",
            )

    def aura_unified_continuity_projection(
        self,
        *,
        plan_phase_hash: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Return current-owner projections for one retained binding without writes."""
        try:
            from aura_unified_memory_continuity_toolchain import compile_continuity_owner_projections

            session = self._require_session(plan_phase_hash)
            binding = dict(session.get("unified_execution_bindings") or {}).get(str(task_id))
            if binding is None:
                raise ValueError("unified execution binding is not retained for this task")
            return {
                "ok": True,
                **compile_continuity_owner_projections(binding),
                "production_mutation": False,
                "human_review_required": True,
            }
        except (ArenaBridgeError, TypeError, ValueError) as exc:
            return make_error_packet(
                "unified_memory_continuity_projection_failed",
                str(exc),
                repair_hint="Compile the unified execution binding before requesting projections.",
            )

    # ------------------------------------------------------------------
    # Tool 3: aura_get_micro_context
    # ------------------------------------------------------------------
''',
)

replace_once(
    "aura_arena_persistence_adapters.py",
    '''        verification_summary = {
            "present": verification is not None,
            "ok": bool(getattr(verification, "ok", False)) if verification is not None else False,
            "stage": str(getattr(verification, "stage", "") or "") if verification is not None else "",
            "hotswap_ready": bool(getattr(verification, "hotswap_ready", False)) if verification is not None else False,
            "failure_count": len(list(getattr(verification, "failures", []) or [])) if verification is not None else 0,
        }
        state = {
''',
    '''        verification_summary = {
            "present": verification is not None,
            "ok": bool(getattr(verification, "ok", False)) if verification is not None else False,
            "stage": str(getattr(verification, "stage", "") or "") if verification is not None else "",
            "hotswap_ready": bool(getattr(verification, "hotswap_ready", False)) if verification is not None else False,
            "failure_count": len(list(getattr(verification, "failures", []) or [])) if verification is not None else 0,
        }
        unified_bindings = []
        for task_id, binding in dict(session.get("unified_execution_bindings") or {}).items():
            to_dict = getattr(binding, "to_dict", None)
            payload = to_dict() if callable(to_dict) else dict(binding or {})
            records = dict(payload.get("records") or {})
            unified_bindings.append(
                {
                    "task_id": str(task_id),
                    "binding_id": str(payload.get("binding_id") or ""),
                    "binding_digest": str(payload.get("binding_digest") or ""),
                    "intent_digest": str(dict(records.get("intent_packet") or {}).get("intent_digest") or ""),
                    "model_execution_packet_digest": str(
                        dict(records.get("model_execution_packet") or {}).get("packet_digest") or ""
                    ),
                    "raw_payload_retained": False,
                    "automatic_promotion": False,
                }
            )
        state = {
''',
)
replace_once(
    "aura_arena_persistence_adapters.py",
    '''            "verification": verification_summary,
            "hotswap_capsule_present": bool(session.get("hotswap_capsule")),
''',
    '''            "verification": verification_summary,
            "unified_execution_bindings": unified_bindings,
            "hotswap_capsule_present": bool(session.get("hotswap_capsule")),
''',
)
replace_once(
    "aura_arena_persistence_adapters.py",
    '''                "affected_files",
                "verification",
            ),
''',
    '''                "affected_files",
                "verification",
                "unified_execution_bindings",
            ),
''',
)

replace_once(
    "aura_architect_council_v3.py",
    '''    lanes = ["scope", "tests"]

    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
''',
    '''    lanes = ["scope", "tests"]
    unified = candidate.get("unified_memory_continuity") or plan.get("unified_memory_continuity") or {}
    if not isinstance(unified, dict):
        unified = {}
    disagreement_refs = list(unified.get("disagreement_refs") or [])
    verification_depth = int(unified.get("required_verification_depth") or 1)
    continuity_requirements = list(unified.get("continuity_requirements") or [])
    if disagreement_refs or verification_depth > 1:
        lanes.append("continuity")
    if unified.get("p0_required") is True or continuity_requirements:
        lanes.append("rollback")

    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
''',
)
replace_once(
    "aura_architect_council_v3.py",
    '''    reasons = ["scope_and_tests_are_universal"]
    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
''',
    '''    reasons = ["scope_and_tests_are_universal"]
    unified = candidate.get("unified_memory_continuity") or plan.get("unified_memory_continuity") or {}
    if isinstance(unified, dict):
        if list(unified.get("disagreement_refs") or []) or int(unified.get("required_verification_depth") or 1) > 1:
            reasons.append("cross_model_disagreement_requires_deeper_verification")
        if unified.get("p0_required") is True or list(unified.get("continuity_requirements") or []):
            reasons.append("prediction_and_continuity_require_rollback_review")
    if profile.dependency_edge_count > 0 or profile.sequential_depth_estimate >= 3:
''',
)

replace_once(
    "aura_forge.py",
    '''        contract = self._compile_contract(request, repo_digest, prepared, act_capsules, task_evidence)
''',
    '''        unified_config = request.metadata.get("unified_memory_continuity")
        if unified_config is not None:
            if not isinstance(unified_config, Mapping):
                return self._error("unified_memory_continuity_metadata_invalid", stage="GROUND")
            compile_binding = getattr(self.bridge, "aura_compile_unified_execution", None)
            if not callable(compile_binding):
                return self._error("unified_memory_continuity_bridge_unavailable", stage="GROUND")
            for capsule in act_capsules:
                task_id = str(capsule.get("task_id") or "")
                result = compile_binding(
                    plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
                    task_id=task_id,
                    contract=dict(unified_config),
                )
                if not isinstance(result, Mapping) or result.get("ok") is not True:
                    return self._error(
                        "unified_memory_continuity_compile_failed",
                        stage="GROUND",
                        details={"task_id": task_id, "result": result},
                    )
                records = dict(result.get("records") or {})
                summary = {
                    "binding_id": result.get("binding_id"),
                    "binding_digest": result.get("binding_digest"),
                    "intent_digest": dict(records.get("intent_packet") or {}).get("intent_digest"),
                    "model_execution_packet_digest": dict(
                        records.get("model_execution_packet") or {}
                    ).get("packet_digest"),
                    "required_verification_depth": dict(records.get("council") or {}).get(
                        "required_verification_depth"
                    ),
                    "p0_required": True,
                    "human_review_required": True,
                }
                matching = next(
                    (item for item in task_evidence if str(item.get("task_id") or "") == task_id),
                    None,
                )
                if matching is not None:
                    matching["unified_memory_continuity"] = _sanitize(summary)

        contract = self._compile_contract(request, repo_digest, prepared, act_capsules, task_evidence)
''',
)

replace_once(
    "aura_agent_arena_mcp.py",
    '''    {
        "name": "aura_get_micro_context",
''',
    '''    {
        "name": "aura_compile_unified_execution",
        "description": "Compile one exact prepared Act Capsule into a model-relative execution packet and reference-only continuity-owner projections.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_phase_hash": {"type": "string"},
                "task_id": {"type": "string"},
                "contract": {"type": "object"},
            },
            "required": ["plan_phase_hash", "task_id", "contract"],
        },
    },
    {
        "name": "aura_get_micro_context",
''',
)
replace_once(
    "aura_agent_arena_mcp.py",
    '''@_register_tool("aura_get_micro_context")
def _handle_get_micro_context(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
''',
    '''@_register_tool("aura_compile_unified_execution")
def _handle_compile_unified_execution(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    contract = args.get("contract")
    if not isinstance(contract, Mapping):
        raise MCPArgumentError("contract must be an object")
    return bridge.aura_compile_unified_execution(
        plan_phase_hash=_bounded_text_arg(args, "plan_phase_hash", maximum=256, required=True),
        task_id=_bounded_text_arg(args, "task_id", maximum=256, required=True),
        contract=dict(contract),
    )


@_register_tool("aura_get_micro_context")
def _handle_get_micro_context(bridge: AuraAgentArenaBridge, args: dict[str, Any]) -> dict[str, Any]:
''',
)

replace_once(
    "tests/test_aura_unified_memory_continuity.py",
    '''def test_module_avoids_dynamic_namespace_injection() -> None:
    with open("aura_unified_memory_continuity.py", encoding="utf-8") as source_file:
        source = source_file.read()
''',
    '''def test_module_avoids_dynamic_namespace_injection() -> None:
    source_path = Path(__file__).resolve().parents[1] / "aura_unified_memory_continuity.py"
    source = source_path.read_text(encoding="utf-8")
''',
)

print("Applied unified manufactured-memory continuity toolchain patches.")
