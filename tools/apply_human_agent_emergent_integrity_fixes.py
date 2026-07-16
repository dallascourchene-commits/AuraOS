#!/usr/bin/env python3
"""Apply the second-pass Human Agent emergent integrity repairs.

This temporary branch-maintenance helper is deterministic, idempotent, and fails closed
when an expected source shape is absent. It is removed after the repaired files pass CI.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"patch target not found in {path}: {old[:140]!r}")
    write(path, text.replace(old, new, 1))


def replace_method(path: str, name: str, replacement: str, next_name: str | None = None) -> None:
    text = read(path)
    if replacement.strip() in text:
        return
    if next_name:
        pattern = rf"^    def {re.escape(name)}\(.*?(?=^    def {re.escape(next_name)}\()"
    else:
        pattern = rf"^    def {re.escape(name)}\(.*?(?=^    # -+|^def )"
    updated, count = re.subn(pattern, replacement.rstrip() + "\n\n", text, count=1, flags=re.M | re.S)
    if count != 1:
        raise RuntimeError(f"method patch failed for {path}:{name}; matches={count}")
    write(path, updated)


def patch_workspace() -> None:
    path = "aura_emergent_refactor_workspace.py"

    replace_once(
        path,
        '''            _atomic_write_json(path, envelope)\n            summary = self._run_summary(envelope)\n            _append_jsonl(self.runs_index, summary)\n''',
        '''            _atomic_write_json(path, envelope)\n            self._reconciled_run_rows(repair=True)\n''',
    )

    text = read(path)
    marker = "    def list_runs(self, *, limit: int = 50) -> dict[str, Any]:\n"
    helpers = '''    def _research_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": payload.get("evidence_id"),
            "provider": payload.get("provider"),
            "query": payload.get("query"),
            "stored_at": payload.get("stored_at", 0.0),
            "result_count": len(payload.get("results", []) or []),
            "linked_finding_ids": list(payload.get("linked_finding_ids", []) or []),
            "digest": payload.get("digest", ""),
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
        }

    def _reconciled_run_rows(self, *, repair: bool = True) -> list[dict[str, Any]]:
        indexed = {
            str(row.get("run_id")): dict(row)
            for row in _read_jsonl(self.runs_index)
            if row.get("run_id")
        }
        authoritative: dict[str, dict[str, Any]] = {}
        for file_path in sorted(self.runs_dir.glob("EMR-*.json")):
            try:
                payload = _read_json(file_path)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            run_id = str(payload.get("run_id") or file_path.stem)
            authoritative[run_id] = {**indexed.get(run_id, {}), **self._run_summary(payload)}
        rows = sorted(
            authoritative.values(),
            key=lambda item: (float(item.get("stored_at", 0.0)), str(item.get("run_id", ""))),
            reverse=True,
        )
        if repair:
            _atomic_write_jsonl(self.runs_index, rows)
        return rows

    def _reconciled_research_rows(self, *, repair: bool = True) -> list[dict[str, Any]]:
        indexed = {
            str(row.get("evidence_id")): dict(row)
            for row in _read_jsonl(self.research_index)
            if row.get("evidence_id")
        }
        authoritative: dict[str, dict[str, Any]] = {}
        for file_path in sorted(self.research_dir.glob("ERE-*.json")):
            try:
                payload = _read_json(file_path)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            evidence_id = str(payload.get("evidence_id") or file_path.stem)
            authoritative[evidence_id] = {
                **indexed.get(evidence_id, {}),
                **self._research_summary(payload),
            }
        rows = sorted(
            authoritative.values(),
            key=lambda item: (float(item.get("stored_at", 0.0)), str(item.get("evidence_id", ""))),
            reverse=True,
        )
        if repair:
            _atomic_write_jsonl(self.research_index, rows)
        return rows

'''
    if helpers.strip() not in text:
        if marker not in text:
            raise RuntimeError("list_runs insertion marker missing")
        write(path, text.replace(marker, helpers + marker, 1))

    replace_method(
        path,
        "list_runs",
        '''    def list_runs(self, *, limit: int = 50) -> dict[str, Any]:
        rows = self._reconciled_run_rows(repair=True)
        bounded = rows[: max(1, min(int(limit), 500))]
        return {
            "ok": True,
            "version": WORKSPACE_VERSION,
            "runs": bounded,
            "count": len(bounded),
            "total": len(rows),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }''',
        "get_run",
    )

    replace_method(
        path,
        "_research_evidence_ids_for_findings",
        '''    def _research_evidence_ids_for_findings(
        self,
        finding_ids: Sequence[str],
        *,
        limit: int = 100,
    ) -> list[str]:
        needles = {str(item) for item in finding_ids if str(item).strip()}
        if not needles:
            return []
        rows = [
            row
            for row in self._reconciled_research_rows(repair=True)
            if needles & {str(item) for item in row.get("linked_finding_ids", []) if item}
        ]
        return _unique(
            str(row.get("evidence_id") or "")
            for row in rows[: max(1, min(int(limit), 500))]
            if row.get("evidence_id")
        )''',
        "build_refactor_packet",
    )

    replace_method(
        path,
        "build_refactor_packet",
        '''    def build_refactor_packet(
        self,
        objective: str,
        *,
        finding_ids: Sequence[str] = (),
        research_evidence_ids: Sequence[str] = (),
        max_findings: int = 8,
        persist: bool = True,
    ) -> dict[str, Any]:
        objective_text = str(objective or "").strip()
        if not objective_text:
            raise ValueError("objective is required")

        requested_finding_ids = _unique(str(item) for item in finding_ids if str(item).strip())
        selected: list[dict[str, Any]] = []
        unresolved_finding_ids: list[str] = []
        if requested_finding_ids:
            for finding_id in requested_finding_ids:
                finding_result = self.get_finding(finding_id)
                if finding_result.get("ok"):
                    selected.append(dict(finding_result["finding"]))
                else:
                    unresolved_finding_ids.append(finding_id)
            if unresolved_finding_ids:
                return {
                    "ok": False,
                    "error": "unresolved_finding_ids",
                    "requested_finding_ids": requested_finding_ids,
                    "missing_finding_ids": unresolved_finding_ids,
                    "persisted": False,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                }
        else:
            selected = list(self.search_findings(objective_text, limit=max_findings).get("findings", []))

        if not selected:
            return {
                "ok": False,
                "error": "no_relevant_emergent_findings",
                "objective": objective_text,
                "persisted": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        target_files = _unique(
            value
            for finding in selected
            for value in (
                (finding.get("source") or {}).get("file"),
                (finding.get("target") or {}).get("file"),
            )
            if value
        )
        target_symbols = _unique(
            value
            for finding in selected
            for value in (
                (finding.get("source") or {}).get("symbol"),
                (finding.get("target") or {}).get("symbol"),
            )
            if value
        )
        required_tests = _unique(
            test for finding in selected for test in list(finding.get("required_tests") or []) if test
        )
        missing_wires = _unique(
            str(finding.get("missing_wire") or "") for finding in selected if finding.get("missing_wire")
        )
        research_gaps: list[dict[str, Any]] = []
        acceptance_criteria: list[str] = []
        for finding in selected:
            ability = str(finding.get("emergent_ability") or "").strip()
            status = str(finding.get("status") or "").upper()
            evidence_count = int(finding.get("evidence_count") or 0)
            tests = list(finding.get("required_tests") or [])
            if ability:
                acceptance_criteria.append(f"Preserve or measurably improve: {ability}")
            if status == "NEEDS_GROUNDING" or evidence_count == 0:
                research_gaps.append(
                    {
                        "finding_id": finding.get("finding_id"),
                        "gap": "ground architecture and research evidence before implementation",
                        "suggested_queries": _suggested_queries(objective_text, ability, missing_wires),
                    }
                )
            if not tests:
                research_gaps.append(
                    {
                        "finding_id": finding.get("finding_id"),
                        "gap": "define deterministic acceptance test",
                        "suggested_queries": [],
                    }
                )

        selected_finding_ids = [
            str(item.get("finding_id") or "") for item in selected if item.get("finding_id")
        ]
        requested_research_ids = _unique(
            str(item) for item in research_evidence_ids if str(item).strip()
        )
        auto_research_ids = self._research_evidence_ids_for_findings(selected_finding_ids)
        linked_research_ids = _unique([*requested_research_ids, *auto_research_ids])
        linked_research: list[dict[str, Any]] = []
        unresolved_research_ids: list[str] = []
        for evidence_id in linked_research_ids:
            item = self.get_research_evidence(evidence_id)
            if item.get("ok"):
                linked_research.append(item)
            else:
                unresolved_research_ids.append(evidence_id)
        if unresolved_research_ids:
            return {
                "ok": False,
                "error": "unresolved_research_evidence_ids",
                "requested_research_evidence_ids": requested_research_ids,
                "missing_research_evidence_ids": unresolved_research_ids,
                "persisted": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        research_evidence = [
            dict(item.get("evidence") or {}) for item in linked_research if item.get("evidence")
        ]
        evidence_ids_by_finding: dict[str, list[str]] = {}
        for evidence in research_evidence:
            evidence_id = str(evidence.get("evidence_id") or "")
            for finding_id in evidence.get("linked_finding_ids", []) or []:
                if evidence_id:
                    evidence_ids_by_finding.setdefault(str(finding_id), []).append(evidence_id)
        for gap in research_gaps:
            finding_id = str(gap.get("finding_id") or "")
            linked_ids = _unique(evidence_ids_by_finding.get(finding_id, []))
            gap["linked_research_evidence_ids"] = linked_ids
            gap["status"] = (
                "EVIDENCE_FOUND_REQUIRES_LOCAL_VERIFICATION" if linked_ids else "OPEN"
            )

        stable_payload = {
            "workspace_version": WORKSPACE_VERSION,
            "objective": objective_text,
            "selected_findings": selected,
            "selected_finding_ids": selected_finding_ids,
            "target_files": target_files,
            "target_symbols": target_symbols,
            "missing_wires": missing_wires,
            "required_tests": required_tests,
            "acceptance_criteria": _unique(acceptance_criteria),
            "research_gaps": research_gaps,
            "research_evidence_ids": linked_research_ids,
            "research_evidence": research_evidence,
            "external_evidence_is_patch_authority": False,
            "local_verification_required": True,
            "human_approval_required": True,
            "truth_class": "EMERGENT_REFACTOR_EVIDENCE_PACKET",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        digest = hashlib.sha256(_canonical_json(stable_payload)).hexdigest()
        packet_id = f"ERP-{digest[:20]}"
        path = self.packets_dir / f"{packet_id}.json"
        created = False
        if persist and path.exists():
            existing = _read_json(path)
            if isinstance(existing, dict):
                payload = existing
            else:
                payload = {**stable_payload, "packet_id": packet_id, "digest": digest, "created_at": time.time()}
                _atomic_write_json(path, payload)
                created = True
        else:
            payload = {**stable_payload, "packet_id": packet_id, "digest": digest}
            if persist:
                payload["created_at"] = time.time()
                _atomic_write_json(path, payload)
                created = True
        return {"ok": True, "packet": payload, "created": created, "persisted": bool(persist)}''',
        "store_research_evidence",
    )

    replace_method(
        path,
        "store_research_evidence",
        '''    def store_research_evidence(
        self,
        *,
        provider: str,
        query: str,
        results: Sequence[dict[str, Any]],
        linked_finding_ids: Sequence[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        requested_links = _unique(str(item) for item in linked_finding_ids if str(item).strip())
        missing_links = [item for item in requested_links if not self.get_finding(item).get("ok")]
        if missing_links:
            return {
                "ok": False,
                "error": "unresolved_linked_finding_ids",
                "missing_finding_ids": missing_links,
                "created": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        stable_payload = {
            "workspace_version": WORKSPACE_VERSION,
            "provider": str(provider or "unknown").lower(),
            "query": str(query or ""),
            "linked_finding_ids": requested_links,
            "metadata": dict(metadata or {}),
            "results": [dict(item) for item in results if isinstance(item, dict)],
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "external_evidence_is_patch_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        digest = hashlib.sha256(_canonical_json(stable_payload)).hexdigest()
        evidence_id = f"ERE-{digest[:20]}"
        path = self.research_dir / f"{evidence_id}.json"
        created = False
        if path.exists():
            existing = _read_json(path)
            payload = existing if isinstance(existing, dict) else {}
        else:
            payload = {
                **stable_payload,
                "evidence_id": evidence_id,
                "digest": digest,
                "stored_at": time.time(),
            }
            _atomic_write_json(path, payload)
            created = True
        self._reconciled_research_rows(repair=True)
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "created": created,
            "stored_at": payload.get("stored_at", 0.0),
            "result_count": len(payload.get("results", []) or []),
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }''',
        "list_research_evidence",
    )

    replace_method(
        path,
        "list_research_evidence",
        '''    def list_research_evidence(self, *, limit: int = 50) -> dict[str, Any]:
        rows = self._reconciled_research_rows(repair=True)
        bounded = rows[: max(1, min(int(limit), 500))]
        return {
            "ok": True,
            "evidence": bounded,
            "count": len(bounded),
            "total": len(rows),
            "truth_class": TRUTH_EXTERNAL_EVIDENCE,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }''',
        "get_research_evidence",
    )

    text = read(path)
    old = '''def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str) + "\\n")


'''
    new = old + '''def _atomic_write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    content = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\\n"
        for row in rows
    )
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, path)


'''
    if "def _atomic_write_jsonl" not in text:
        if old not in text:
            raise RuntimeError("JSONL helper insertion target missing")
        write(path, text.replace(old, new, 1))


def patch_server() -> None:
    path = "aura_human_agent_arena_server.py"
    replace_once(path, "import argparse\n", "import argparse\nimport hashlib\n")
    replace_once(path, "from pathlib import Path\n", "from pathlib import Path\nimport time\n")

    text = read(path)
    pattern = r"^def _attach_emergent_refactor_context\(.*?(?=^def _handle_emergent_and_research_api\()"
    replacement = '''def _commit_emergent_packet(state: HumanAgentArenaServerState, packet: dict[str, Any]) -> None:
    workflow_evidence = state.workflow.evidence
    workflow_evidence["emergent_refactor_packet"] = packet
    workflow_evidence["emergent_findings"] = list(packet.get("selected_findings") or [])
    workflow_evidence["research_gaps"] = list(packet.get("research_gaps") or [])
    workflow_evidence["external_research_evidence"] = list(packet.get("research_evidence") or [])
    existing_tests = list(workflow_evidence.get("test_targets") or [])
    workflow_evidence["test_targets"] = _unique(
        [*existing_tests, *list(packet.get("required_tests") or [])]
    )[:16]


def _attach_emergent_refactor_context(
    state: HumanAgentArenaServerState,
    objective: str,
    *,
    finding_ids: Iterable[str] = (),
    research_evidence_ids: Iterable[str] = (),
    persist: bool = True,
    commit: bool = True,
) -> dict[str, Any]:
    objective_text = str(objective or "").strip()
    if not objective_text:
        return {"ok": False, "error": "objective_required_for_emergent_context"}
    emergent_store = getattr(state, "emergent_store", None)
    if emergent_store is None:
        return {
            "ok": False,
            "status": "UNAVAILABLE",
            "error": "emergent_workspace_unavailable",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    packet_result = emergent_store.build_refactor_packet(
        objective_text,
        finding_ids=list(finding_ids),
        research_evidence_ids=list(research_evidence_ids),
        max_findings=8,
        persist=persist,
    )
    packet = dict(packet_result.get("packet") or {})
    if packet_result.get("ok") and packet and commit:
        _commit_emergent_packet(state, packet)
    return packet_result


def _prepare_payload_with_emergent_context(
    state: HumanAgentArenaServerState,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    objective = str(state.workflow.state.objective or payload.get("objective") or "").strip()
    result = _attach_emergent_refactor_context(
        state,
        objective,
        finding_ids=list(payload.get("finding_ids") or []),
        research_evidence_ids=list(payload.get("research_evidence_ids") or []),
        persist=False,
        commit=False,
    ) if objective else {"ok": False, "error": "objective_not_set"}
    packet = dict(result.get("packet") or {})
    merged = dict(payload)
    merged["acceptance_criteria"] = _unique(
        [
            *list(payload.get("acceptance_criteria") or []),
            *list(packet.get("acceptance_criteria") or []),
            *[
                f"Close or explicitly defer research gap: {item.get('gap')}"
                for item in packet.get("research_gaps", [])
                if item.get("gap")
            ],
        ]
    )
    merged["emergent_refactor_packet_id"] = packet.get("packet_id", "")
    return merged, result


def _record_special_tool_run(
    state: HumanAgentArenaServerState,
    *,
    tool_id: str,
    objective: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    ok: bool,
) -> dict[str, Any]:
    started_at = time.time()
    seed = json.dumps(
        {"tool_id": tool_id, "objective": objective, "inputs": inputs, "started_at": started_at},
        sort_keys=True,
        default=str,
    )
    run_id = f"TOOL-{hashlib.blake2b(seed.encode(), digest_size=8).hexdigest()}"
    record = {
        "run_id": run_id,
        "tool_id": tool_id,
        "objective": objective,
        "status": "COMPLETED" if ok else "FAILED",
        "started_at": started_at,
        "completed_at": time.time(),
        "inputs": dict(inputs),
        "outputs": dict(outputs),
        "denial": {},
        "sandbox_receipt": {},
        "dissolution_receipt": {},
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    state.workflow.tools.runs[run_id] = record
    return record


'''
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.M | re.S)
    if count != 1:
        raise RuntimeError(f"server context block patch failed: {count}")
    write(path, updated)

    text = read(path)
    action_pattern = r'''    if method == "POST" and route == "/api/human-agent/workflow/action":.*?(?=    if method == "POST" and route == "/api/human-agent/workflow/command":)'''
    action_replacement = '''    if method == "POST" and route == "/api/human-agent/workflow/action":
        action_id = str(body.get("action_id") or "")
        if not action_id:
            return _error("action_id is required")
        action_payload = dict(body.get("payload") or {})
        preview_context: dict[str, Any] = {}
        if action_id == "prepare_capsule":
            action_payload, preview_context = _prepare_payload_with_emergent_context(state, action_payload)
        result = state.workflow.execute_guarded(action_id, action_payload)
        emergent_context: dict[str, Any] = {}
        if result.get("ok"):
            objective = str(state.workflow.state.objective or action_payload.get("objective") or "")
            if objective and action_id in {"set_objective", "ground_context", "prepare_capsule"}:
                emergent_context = _attach_emergent_refactor_context(
                    state,
                    objective,
                    finding_ids=list(action_payload.get("finding_ids") or []),
                    research_evidence_ids=list(action_payload.get("research_evidence_ids") or []),
                    persist=True,
                    commit=True,
                )
        elif preview_context:
            result["emergent_context_preview"] = preview_context
        if emergent_context:
            result["emergent_context"] = emergent_context
            result["workflow"] = state.workflow.get_state()
        return (200 if result.get("ok") else 409), result

'''
    updated, count = re.subn(action_pattern, action_replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"workflow action patch failed: {count}")
    write(path, updated)

    text = read(path)
    command_pattern = r'''    if method == "POST" and route == "/api/human-agent/workflow/command":.*?(?=    if method == "GET" and route == "/api/coding-workbench/state":)'''
    command_replacement = '''    if method == "POST" and route == "/api/human-agent/workflow/command":
        command = str(body.get("command") or "")
        if not command.strip():
            return _error("command is required")
        command_payload = dict(body.get("payload") or {})
        preview_context: dict[str, Any] = {}
        if state.workflow.state.objective:
            command_payload, preview_context = _prepare_payload_with_emergent_context(state, command_payload)
        result = state.workflow.ingest_command(command, command_payload)
        objective = str(state.workflow.state.objective or "")
        if result.get("ok") and objective:
            emergent_context = _attach_emergent_refactor_context(
                state,
                objective,
                finding_ids=list(command_payload.get("finding_ids") or []),
                research_evidence_ids=list(command_payload.get("research_evidence_ids") or []),
                persist=True,
                commit=True,
            )
            result["emergent_context"] = emergent_context
            result["workflow"] = state.workflow.get_state()
        elif preview_context:
            result["emergent_context_preview"] = preview_context
        return (200 if result.get("ok") else 409), result

'''
    updated, count = re.subn(command_pattern, command_replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"workflow command patch failed: {count}")
    write(path, updated)

    text = read(path)
    tools_pattern = r'''    if method == "POST" and route == "/api/human-agent/tools/run":.*?(?=    if method == "GET" and route.startswith\("/api/human-agent/tool-runs/"\):)'''
    tools_replacement = '''    if method == "POST" and route == "/api/human-agent/tools/run":
        tool_id = str(body.get("tool_id") or "")
        if not tool_id:
            return _error("tool_id is required")
        inputs = dict(body.get("inputs") or {})
        objective = str(body.get("objective") or state.workflow.state.objective)
        if tool_id == "emergent_refactor_workspace":
            outputs = _attach_emergent_refactor_context(
                state,
                objective,
                finding_ids=list(inputs.get("finding_ids") or []),
                research_evidence_ids=list(inputs.get("research_evidence_ids") or []),
                persist=True,
                commit=True,
            )
            record = _record_special_tool_run(
                state,
                tool_id=tool_id,
                objective=objective,
                inputs=inputs,
                outputs=outputs,
                ok=bool(outputs.get("ok")),
            )
            return (200 if outputs.get("ok") else 409), record
        if tool_id == "research_forager":
            status, outputs = dispatch_api_request(
                state,
                "POST",
                "/api/human-agent/research/search",
                {
                    "provider": inputs.get("provider"),
                    "query": inputs.get("query") or objective,
                    "limit": inputs.get("limit", 8),
                    "include_sidecars": inputs.get("include_sidecars", False),
                    "sidecar_limit": inputs.get("sidecar_limit", 2),
                    "finding_ids": inputs.get("finding_ids", []),
                },
            )
            record = _record_special_tool_run(
                state,
                tool_id=tool_id,
                objective=objective,
                inputs=inputs,
                outputs=outputs,
                ok=200 <= status < 300 and bool(outputs.get("ok")),
            )
            return status, record
        result = state.workflow.tools.execute(
            tool_id,
            objective=objective,
            inputs=inputs,
        )
        return (200 if result.get("status") != "DENIED" else 409), result

'''
    updated, count = re.subn(tools_pattern, tools_replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"special tools patch failed: {count}")
    write(path, updated)

    replace_once(
        path,
        '''        stored = state.emergent_store.store_research_evidence(
            provider=provider,
            query=search_query,
            results=list(result.get("results") or []),
            linked_finding_ids=list(body.get("finding_ids") or []),
            metadata={
                "metadata_truth": result.get("metadata_truth"),
                "sidecar_truth": result.get("sidecar_truth"),
                "count": result.get("count", 0),
            },
        )
        result["stored_evidence"] = stored
        return 200, result
''',
        '''        stored = state.emergent_store.store_research_evidence(
            provider=provider,
            query=search_query,
            results=list(result.get("results") or []),
            linked_finding_ids=list(body.get("finding_ids") or []),
            metadata={
                "metadata_truth": result.get("metadata_truth"),
                "sidecar_truth": result.get("sidecar_truth"),
                "count": result.get("count", 0),
            },
        )
        result["stored_evidence"] = stored
        if not stored.get("ok"):
            result["ok"] = False
            result["error"] = stored.get("error", "research_evidence_store_failed")
            return 409, result
        return 200, result
''',
    )


def patch_ui() -> None:
    path = "aura_human_agent_arena/emergent.js"
    text = read(path)
    if "function safeHttpUrl" not in text:
        marker = "  let findings = [];\n"
        helper = '''  function safeHttpUrl(value) {
    try {
      const parsed = new URL(String(value || ''), window.location.href);
      return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '';
    } catch (_error) {
      return '';
    }
  }

'''
        if marker not in text:
            raise RuntimeError("UI helper marker missing")
        text = text.replace(marker, helper + marker, 1)
        write(path, text)

    text = read(path)
    pattern = r"  async function inspectFinding\(findingId\) \{.*?\n  \}\n\n  async function compileRefactorPacket"
    replacement = '''  async function inspectFinding(findingId) {
    const host = $('emergent-finding-detail');
    if (host) host.innerHTML = '<p class="placeholder">Loading complete stored finding…</p>';
    try {
      const result = await api(`/api/human-agent/emergent/findings/${encodeURIComponent(findingId)}`);
      if (!host) return;
      if (!result.ok) {
        host.textContent = result.error || 'Finding unavailable.';
        setStatus(`Finding unavailable: ${result.error || 'unknown error'}`, 'error');
        return;
      }
      const finding = result.finding || {};
      const raw = result.raw || {};
      const queryInput = $('research-query');
      if (queryInput && !queryInput.value) {
        queryInput.value = `${finding.emergent_ability || ''} ${finding.missing_wire || ''}`.trim();
      }
      host.innerHTML = `
        <div class="detail-head"><strong>${escape(finding.emergent_ability)}</strong><span>${escape(finding.status)}</span></div>
        <p><b>Missing wire:</b> ${escape(finding.missing_wire)}</p>
        <p><b>Required tests:</b> ${(finding.required_tests || []).map(escape).join(' · ') || 'not yet defined'}</p>
        <p><b>Patch authority:</b> exact local source spans and hashes only</p>
        <details><summary>Complete stored object</summary><pre>${escape(JSON.stringify(raw, null, 2))}</pre></details>`;
    } catch (error) {
      if (host) host.innerHTML = `<p class="placeholder">${escape(error.message || 'Finding request failed.')}</p>`;
      setStatus(`Finding request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  async function compileRefactorPacket'''
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"inspectFinding patch failed: {count}")
    write(path, updated)

    text = read(path)
    pattern = r"  async function compileRefactorPacket\(\) \{.*?\n  \}\n\n  async function runResearchSearch"
    replacement = '''  async function compileRefactorPacket() {
    const objective = $('workflow-objective')?.value?.trim() || $('emergent-query')?.value?.trim() || '';
    if (!objective) {
      setStatus('Set the active refactor objective first.', 'warn');
      return;
    }
    const host = $('emergent-packet');
    setStatus('Compiling emergent findings into refactor evidence…');
    try {
      const result = await api('/api/human-agent/emergent/refactor-packet', {
        objective,
        finding_ids: [...selectedFindingIds],
        research_evidence_ids: [...selectedResearchEvidenceIds],
      });
      if (host) {
        const packet = result.packet || {};
        host.innerHTML = result.ok ? `
          <div class="detail-head"><strong>Refactor packet ${escape(packet.packet_id)}</strong><span>${(packet.selected_findings || []).length} findings</span></div>
          <p><b>Targets:</b> ${(packet.target_files || []).map(escape).join(' · ') || 'none'}</p>
          <p><b>Tests:</b> ${(packet.required_tests || []).map(escape).join(' · ') || 'must be defined'}</p>
          <p><b>Research gaps:</b> ${(packet.research_gaps || []).length}</p>
          <details open><summary>Acceptance criteria</summary><ul>${(packet.acceptance_criteria || []).map(item => `<li>${escape(item)}</li>`).join('')}</ul></details>
          <details><summary>Complete packet</summary><pre>${escape(JSON.stringify(packet, null, 2))}</pre></details>`
          : `<p class="placeholder">${escape(result.error || 'Packet creation failed.')}</p>`;
      }
      setStatus(result.ok ? 'Refactor evidence attached to the active Human Agent workflow.' : 'Packet creation failed.', result.ok ? 'ok' : 'error');
    } catch (error) {
      if (host) host.innerHTML = `<p class="placeholder">${escape(error.message || 'Packet request failed.')}</p>`;
      setStatus(`Packet request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  async function runResearchSearch'''
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"compileRefactorPacket patch failed: {count}")
    write(path, updated)

    text = read(path)
    pattern = r"  async function runResearchSearch\(\) \{.*?\n  \}\n\n  function renderResearchResults"
    replacement = '''  async function runResearchSearch() {
    const provider = $('research-provider')?.value || 'arxiv';
    const query = $('research-query')?.value?.trim() || $('emergent-query')?.value?.trim() || '';
    if (!query) {
      setStatus('Enter a research query.', 'warn');
      return;
    }
    const includeSidecars = Boolean($('research-sidecars')?.checked);
    setStatus(`Searching ${provider} through the bounded research bridge…`);
    try {
      const result = await api('/api/human-agent/research/search', {
        provider,
        query,
        limit: 8,
        include_sidecars: includeSidecars,
        sidecar_limit: 2,
        finding_ids: [...selectedFindingIds],
      });
      const storedEvidenceId = result.stored_evidence?.evidence_id;
      if (storedEvidenceId) selectedResearchEvidenceIds.add(storedEvidenceId);
      renderResearchResults(result);
      setStatus(result.ok
        ? `${result.count || 0} ${provider} results stored as external evidence.`
        : `Research failed: ${result.error || 'unknown error'}`,
        result.ok ? 'ok' : 'error');
      await loadResearchEvidence();
    } catch (error) {
      renderResearchResults({ ok: false, error: error.message || 'Research request failed.' });
      setStatus(`Research request failed: ${error.message || 'unknown error'}`, 'error');
    }
  }

  function renderResearchResults'''
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"runResearchSearch patch failed: {count}")
    write(path, updated)

    replace_once(
        path,
        '''      const url = isArxiv ? item.entry_url : item.html_url;\n''',
        '''      const rawUrl = isArxiv ? item.entry_url : item.html_url;\n      const url = safeHttpUrl(rawUrl);\n''',
    )


def patch_navigator() -> None:
    path = "aura_codebase_navigator.py"
    replace_once(
        path,
        '''TEXT_SUFFIXES = frozenset({"", ".c", ".cpp", ".css", ".html", ".json", ".lexc", ".md", ".py", ".rs", ".sh", ".tex", ".toml", ".txt", ".yml", ".yaml"})''',
        '''TEXT_SUFFIXES = frozenset({"", ".c", ".cpp", ".css", ".html", ".js", ".json", ".lexc", ".md", ".py", ".rs", ".sh", ".tex", ".toml", ".txt", ".yml", ".yaml"})''',
    )
    replace_once(
        path,
        '''    if suffix in {".html", ".css"}:\n        return "interface_surface"\n''',
        '''    if suffix in {".html", ".css", ".js"}:\n        return "interface_surface"\n''',
    )


def patch_benchmark_scope() -> None:
    path = ".github/workflows/architect-real-refactor-trial.yml"
    text = read(path)
    needle = '''              "aura_human_agent_arena_server.py",\n              "tests/test_aura_emergent_refactor_workspace.py",\n'''
    replacement = '''              "aura_human_agent_arena_server.py",\n              "aura_codebase_navigator.py",\n              "tests/test_aura_codemap_verify.py",\n              "tests/test_aura_emergent_refactor_workspace.py",\n'''
    if replacement not in text:
        if needle not in text:
            raise RuntimeError("benchmark scope insertion target missing")
        write(path, text.replace(needle, replacement, 1))


def patch_tests() -> None:
    path = "tests/test_aura_codemap_verify.py"
    text = read(path)
    if "from aura_codebase_navigator import _scan_file" not in text:
        marker = "from aura_codemap_verify import (\n"
        if marker not in text:
            raise RuntimeError("codemap test import marker missing")
        text = text.replace(marker, "from aura_codebase_navigator import _scan_file\n" + marker, 1)
    marker = "def test_javascript_interface_surface_has_real_text_metadata"
    if marker not in text:
        text += '''\n\ndef test_javascript_interface_surface_has_real_text_metadata(tmp_path: Path):\n    source = tmp_path / "ui.js"\n    source.write_text("const answer = 42;\\nfunction render() { return answer; }\\n", encoding="utf-8")\n    card = _scan_file(tmp_path, source)\n    assert card["role"] == "interface_surface"\n    assert card["lines"] >= 2\n    assert card["tokens_est"] > 0\n    assert card["binary"] is False\n'''
    write(path, text)

    path = "tests/test_aura_emergent_refactor_workspace.py"
    text = read(path)
    marker = "def test_second_pass_integrity_contracts"
    if marker not in text:
        text += r'''


def test_second_pass_integrity_contracts(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    first = store.store_report(sample_report(), source="first")
    changed = sample_report()
    changed["suite_version"] = "TEST_EMERGENT_SUITE_V2"
    second = store.store_report(changed, source="second")

    # Authoritative files survive stale/malformed indexes and repair them without duplicates.
    first_row = store.list_runs(limit=10)["runs"][0]
    store.runs_index.write_text(json.dumps(first_row) + "\n{malformed\n", encoding="utf-8")
    runs = store.list_runs(limit=10)
    assert runs["total"] == 2
    assert {item["run_id"] for item in runs["runs"]} == {first["run_id"], second["run_id"]}
    assert len(store.runs_index.read_text(encoding="utf-8").splitlines()) == 2

    finding = store.search_findings("Human Agent Arena research", limit=1)["findings"][0]
    evidence_a = store.store_research_evidence(
        provider="arxiv",
        query="arena verification",
        results=[{"arxiv_id": "2601.00001", "title": "Arena verification"}],
        linked_finding_ids=[finding["finding_id"]],
    )
    evidence_b = store.store_research_evidence(
        provider="github",
        query="arena verification",
        results=[{"full_name": "example/arena"}],
        linked_finding_ids=[finding["finding_id"]],
    )
    first_evidence_row = store.list_research_evidence(limit=10)["evidence"][0]
    store.research_index.write_text(json.dumps(first_evidence_row) + "\nnot-json\n", encoding="utf-8")
    evidence_rows = store.list_research_evidence(limit=10)
    assert evidence_rows["total"] == 2
    assert {item["evidence_id"] for item in evidence_rows["evidence"]} == {
        evidence_a["evidence_id"], evidence_b["evidence_id"]
    }

    # Content IDs are stable and explicit unresolved selections fail closed.
    packet_a = store.build_refactor_packet(
        "Refactor the Human Agent Arena", finding_ids=[finding["finding_id"]]
    )
    packet_b = store.build_refactor_packet(
        "Refactor the Human Agent Arena", finding_ids=[finding["finding_id"]]
    )
    assert packet_a["packet"]["packet_id"] == packet_b["packet"]["packet_id"]
    assert packet_b["created"] is False
    evidence_repeat = store.store_research_evidence(
        provider="arxiv",
        query="arena verification",
        results=[{"arxiv_id": "2601.00001", "title": "Arena verification"}],
        linked_finding_ids=[finding["finding_id"]],
    )
    assert evidence_repeat["evidence_id"] == evidence_a["evidence_id"]
    assert evidence_repeat["created"] is False
    missing_findings = store.build_refactor_packet(
        "Refactor", finding_ids=["EMF-" + "0" * 20]
    )
    assert missing_findings["ok"] is False
    assert missing_findings["error"] == "unresolved_finding_ids"
    missing_evidence = store.build_refactor_packet(
        "Refactor", finding_ids=[finding["finding_id"]], research_evidence_ids=["ERE-" + "0" * 20]
    )
    assert missing_evidence["ok"] is False
    assert missing_evidence["error"] == "unresolved_research_evidence_ids"


def test_denied_wfst_action_does_not_commit_emergent_evidence(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    state.emergent_store.store_report(sample_report(), source="test")
    before = json.loads(json.dumps(state.workflow.evidence, default=str))
    status, result = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/workflow/action",
        {
            "action_id": "prepare_capsule",
            "payload": {"objective": "Refactor the Human Agent Arena"},
        },
    )
    assert status == 409
    assert result["ok"] is False
    assert state.workflow.evidence == before


def test_special_tool_runs_are_registered_and_retrievable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    state.emergent_store.store_report(sample_report(), source="test")
    finding = state.emergent_store.search_findings("Human Agent Arena research", limit=1)["findings"][0]

    status, run = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/tools/run",
        {
            "tool_id": "emergent_refactor_workspace",
            "objective": "Refactor the Human Agent Arena",
            "inputs": {"finding_ids": [finding["finding_id"]]},
        },
    )
    assert status == 200
    assert run["run_id"].startswith("TOOL-")
    status, loaded = dispatch_api_request(
        state, "GET", f"/api/human-agent/tool-runs/{run['run_id']}"
    )
    assert status == 200
    assert loaded["run"]["tool_id"] == "emergent_refactor_workspace"

    monkeypatch.setattr(
        state.research_bridge,
        "search",
        lambda *args, **kwargs: {
            "ok": True,
            "provider": "github",
            "query": "arena",
            "count": 1,
            "results": [{"full_name": "example/arena"}],
            "metadata_truth": GITHUB_METADATA_TRUTH,
            "sidecar_truth": SIDECAR_TRUTH,
        },
    )
    status, research_run = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/tools/run",
        {
            "tool_id": "research_forager",
            "objective": "Refactor the Human Agent Arena",
            "inputs": {"provider": "github", "query": "arena", "finding_ids": [finding["finding_id"]]},
        },
    )
    assert status == 200
    status, loaded_research = dispatch_api_request(
        state, "GET", f"/api/human-agent/tool-runs/{research_run['run_id']}"
    )
    assert status == 200
    assert loaded_research["run"]["outputs"]["stored_evidence"]["ok"] is True


def test_emergent_ui_has_error_boundaries_and_safe_urls():
    script = (Path(__file__).resolve().parents[1] / "aura_human_agent_arena" / "emergent.js").read_text(encoding="utf-8")
    assert "function safeHttpUrl" in script
    assert script.count("catch (error)") >= 4
    assert "const url = safeHttpUrl(rawUrl);" in script
'''
    write(path, text)


def main() -> int:
    patch_workspace()
    patch_server()
    patch_ui()
    patch_navigator()
    patch_benchmark_scope()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
