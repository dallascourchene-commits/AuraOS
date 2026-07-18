from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing integration marker: {label}")
    return text.replace(old, new, 1)


def patch_bridge() -> None:
    path = Path("aura_agent_arena_persistence_bridge.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from aura_agent_arena_bridge import AuraAgentArenaBridge\n",
        "from aura_agent_arena_bridge import AuraAgentArenaBridge\n"
        "from aura_agent_arena_errors import make_error_packet\n",
        "bridge error import",
    )
    text = replace_once(
        text,
        "from aura_coding_waboose import CodingWaboose\n",
        "from aura_coding_waboose import CodingWaboose\n"
        "from aura_emergent_evidence_spine import AuraEmergentEvidenceSpine\n",
        "emergent spine import",
    )
    text = replace_once(
        text,
        "AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION = \"AURA_AGENT_ARENA_PERSISTENCE_BRIDGE_V1\"\n\n\nclass PersistentAuraAgentArenaBridge",
        '''AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION = "AURA_AGENT_ARENA_PERSISTENCE_BRIDGE_V1"


def _unique_strings(*groups: list[str] | None) -> list[str]:
    result: list[str] = []
    for group in groups:
        for value in group or []:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
    return result


def _primary_emergent_target(
    packet: Mapping[str, Any],
    *,
    target_file: str | None,
    target_symbol: str | None,
) -> tuple[str | None, str | None]:
    selected = list(
        dict(packet.get("atomic_inventory") or {}).get("selected_atomic_functions")
        or []
    )
    final_file = target_file
    final_symbol = target_symbol
    if final_file and not final_symbol:
        match = next(
            (
                item
                for item in selected
                if isinstance(item, Mapping) and item.get("file_path") == final_file
            ),
            None,
        )
        if isinstance(match, Mapping):
            final_symbol = str(match.get("symbol") or "") or None
    if final_symbol and not final_file:
        match = next(
            (
                item
                for item in selected
                if isinstance(item, Mapping) and item.get("symbol") == final_symbol
            ),
            None,
        )
        if isinstance(match, Mapping):
            final_file = str(match.get("file_path") or "") or None
    bridge_projection = dict(
        dict(packet.get("projections") or {}).get("agent_bridge") or {}
    )
    final_file = final_file or str(bridge_projection.get("target_file") or "") or None
    final_symbol = final_symbol or str(bridge_projection.get("target_symbol") or "") or None
    return final_file, final_symbol


class PersistentAuraAgentArenaBridge''',
        "bridge helpers",
    )
    text = replace_once(
        text,
        "        self.coding_waboose = CodingWaboose(self.repo_root)\n",
        "        self.coding_waboose = CodingWaboose(self.repo_root)\n"
        "        self.emergent_spine = AuraEmergentEvidenceSpine(self.repo_root)\n",
        "bridge runtime initialization",
    )
    marker = "    def aura_checkpoint_session(\n"
    methods = '''    def aura_atomic_function_inventory(
        self,
        *,
        query: str = "",
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        limit: int | None = None,
        include_source: bool = False,
    ) -> dict[str, Any]:
        return self.emergent_spine.atomic_inventory(
            query=query,
            target_files=target_files or [],
            target_symbols=target_symbols or [],
            limit=limit,
            include_source=include_source,
        )

    def aura_emergent_evidence(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.emergent_spine.run(request)

    def aura_prepare_arena(
        self,
        *,
        objective: str,
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
        use_emergent_evidence: bool = False,
        emergent_radius: int = 1,
        emergent_max_atomic_nodes: int = 48,
        emergent_include_source: bool = False,
        emergent_include_research_plan: bool = True,
    ) -> dict[str, Any]:
        if not use_emergent_evidence:
            return super().aura_prepare_arena(
                objective=objective,
                target_file=target_file,
                target_symbol=target_symbol,
                acceptance_criteria=acceptance_criteria,
                risk_map=risk_map,
                constraints=constraints,
            )

        packet = self.emergent_spine.run(
            {
                "objective": objective,
                "target_files": [target_file] if target_file else [],
                "target_symbols": [target_symbol] if target_symbol else [],
                "target_arena": "coding_arena",
                "radius": emergent_radius,
                "max_atomic_nodes": emergent_max_atomic_nodes,
                "include_source": emergent_include_source,
                "include_research_plan": emergent_include_research_plan,
            }
        )
        if not packet.get("ok"):
            return make_error_packet(
                "missing_grounding",
                "Emergent evidence preparation failed closed.",
                repair_hint=str(packet.get("error") or "Resolve the emergent evidence request."),
            )
        if not packet.get("grounding_ok"):
            return make_error_packet(
                "missing_grounding",
                "Emergent evidence is affinity-only or has no exact atomic closure.",
                repair_hint="Provide an exact target file/symbol or repair CODEMAP/topology grounding.",
            )
        projection = dict(
            dict(packet.get("projections") or {}).get("coding_arena") or {}
        )
        final_file, final_symbol = _primary_emergent_target(
            packet,
            target_file=target_file,
            target_symbol=target_symbol,
        )
        result = super().aura_prepare_arena(
            objective=objective,
            target_file=final_file,
            target_symbol=final_symbol,
            acceptance_criteria=_unique_strings(
                acceptance_criteria,
                list(projection.get("acceptance_criteria") or []),
            ),
            risk_map=_unique_strings(
                risk_map,
                list(projection.get("risk_map") or []),
            ),
            constraints=_unique_strings(
                constraints,
                list(projection.get("constraints") or []),
            ),
        )
        if not result.get("ok"):
            return result
        atomic = dict(packet.get("atomic_inventory") or {})
        summary = {
            "version": packet.get("version", ""),
            "packet_id": packet.get("packet_id", ""),
            "packet_digest": packet.get("packet_digest", ""),
            "status": packet.get("status", ""),
            "grounding_ok": bool(packet.get("grounding_ok")),
            "atomic_inventory_digest": atomic.get("inventory_digest", ""),
            "atomic_inventory_total": int(atomic.get("total_count") or 0),
            "selected_atomic_count": int(atomic.get("selected_count") or 0),
            "tests": list(packet.get("tests") or []),
            "waboose_focus_directives": list(
                packet.get("waboose_focus_directives") or []
            ),
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": packet.get(
                "patch_authority", "exact_source_spans_and_hashes_only"
            ),
            "vsa_patch_authority": False,
        }
        result["emergent_evidence"] = summary
        phase_hash = str(result.get("plan_phase_hash") or "")
        session = self._get_session(phase_hash) if phase_hash else None
        if session is not None:
            session["emergent_evidence"] = packet
        return result

'''
    text = replace_once(text, marker, methods + marker, "emergent bridge methods")

    list_marker = '''            {
                "name": "aura_waboose_prepare",
'''
    tool_entries = '''            {
                "name": "aura_atomic_function_inventory",
                "description": "List the complete or bounded exact atomic callable inventory.",
                "required_inputs": [],
            },
            {
                "name": "aura_emergent_evidence",
                "description": "Build a Connectome-guided exact atomic dependency and source-slice packet.",
                "required_inputs": ["objective"],
            },
'''
    text = replace_once(text, list_marker, tool_entries + list_marker, "bridge tool catalog")
    path.write_text(text, encoding="utf-8")


def patch_mcp() -> None:
    path = Path("aura_agent_arena_mcp.py")
    text = path.read_text(encoding="utf-8")
    old_prepare_props = '''                "constraints": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective"],
'''
    new_prepare_props = '''                "constraints": {"type": "array", "items": {"type": "string"}},
                "use_emergent_evidence": {"type": "boolean", "default": False},
                "emergent_radius": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1},
                "emergent_max_atomic_nodes": {"type": "integer", "minimum": 1, "maximum": 200, "default": 48},
                "emergent_include_source": {"type": "boolean", "default": False},
                "emergent_include_research_plan": {"type": "boolean", "default": True},
            },
            "required": ["objective"],
'''
    text = replace_once(
        text,
        old_prepare_props,
        new_prepare_props,
        "prepare emergent schema",
    )

    waboose_definition = '''    {
        "name": "aura_waboose_prepare",
'''
    definitions = '''    {
        "name": "aura_atomic_function_inventory",
        "description": "Enumerate exact atomic functions, methods, async functions, and nested functions with spans and hashes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": ""},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "include_source": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "aura_emergent_evidence",
        "description": "Resolve the Capability Connectome, exact atomic dependency closure, source slices, emergent audit, and research gaps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "target_files": {"type": "array", "items": {"type": "string"}},
                "target_symbols": {"type": "array", "items": {"type": "string"}},
                "target_arena": {"type": "string", "enum": ["coding_arena", "coding_waboose", "human_agent", "agent_bridge", "research"], "default": "agent_bridge"},
                "radius": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1},
                "max_atomic_nodes": {"type": "integer", "minimum": 1, "maximum": 200, "default": 48},
                "max_source_lines": {"type": "integer", "minimum": 8, "maximum": 300, "default": 120},
                "include_source": {"type": "boolean", "default": True},
                "include_future": {"type": "boolean", "default": True},
                "include_research_plan": {"type": "boolean", "default": True},
                "include_offline_research": {"type": "boolean", "default": True},
            },
            "required": ["objective"],
        },
    },
'''
    text = replace_once(
        text,
        waboose_definition,
        definitions + waboose_definition,
        "emergent MCP definitions",
    )

    old_prepare_call = '''        constraints=args.get("constraints"),
    )
'''
    new_prepare_call = '''        constraints=args.get("constraints"),
        use_emergent_evidence=bool(args.get("use_emergent_evidence", False)),
        emergent_radius=int(args.get("emergent_radius", 1)),
        emergent_max_atomic_nodes=int(args.get("emergent_max_atomic_nodes", 48)),
        emergent_include_source=bool(args.get("emergent_include_source", False)),
        emergent_include_research_plan=bool(
            args.get("emergent_include_research_plan", True)
        ),
    )
'''
    text = replace_once(
        text,
        old_prepare_call,
        new_prepare_call,
        "prepare MCP handler",
    )

    waboose_handler = '''@_register_tool("aura_waboose_prepare")
'''
    handlers = '''@_register_tool("aura_atomic_function_inventory")
def _handle_atomic_function_inventory(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    limit = args.get("limit")
    return bridge.aura_atomic_function_inventory(
        query=str(args.get("query", "")),
        target_files=list(args.get("target_files", []) or []),
        target_symbols=list(args.get("target_symbols", []) or []),
        limit=int(limit) if limit is not None else None,
        include_source=bool(args.get("include_source", False)),
    )


@_register_tool("aura_emergent_evidence")
def _handle_emergent_evidence(
    bridge: AuraAgentArenaBridge,
    args: dict[str, Any],
) -> dict[str, Any]:
    request = {
        "objective": str(args.get("objective", "")),
        "target_files": list(args.get("target_files", []) or []),
        "target_symbols": list(args.get("target_symbols", []) or []),
        "target_arena": str(args.get("target_arena", "agent_bridge")),
        "radius": int(args.get("radius", 1)),
        "max_atomic_nodes": int(args.get("max_atomic_nodes", 48)),
        "max_source_lines": int(args.get("max_source_lines", 120)),
        "include_source": bool(args.get("include_source", True)),
        "include_future": bool(args.get("include_future", True)),
        "include_research_plan": bool(args.get("include_research_plan", True)),
        "include_offline_research": bool(
            args.get("include_offline_research", True)
        ),
    }
    return bridge.aura_emergent_evidence(request)


'''
    text = replace_once(
        text,
        waboose_handler,
        handlers + waboose_handler,
        "emergent MCP handlers",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_bridge()
    patch_mcp()


if __name__ == "__main__":
    main()
