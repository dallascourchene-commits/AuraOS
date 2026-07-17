from __future__ import annotations

import json
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"missing fragment in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_source() -> None:
    replace_once(
        "aura_forge.py",
        "import subprocess\nfrom typing import Any, Callable, Mapping, Sequence\n",
        "import subprocess\nimport uuid\nfrom typing import Any, Callable, Mapping, Sequence\n",
    )
    replace_once(
        "aura_forge.py",
        '''        gates = _clean_strings(raw.get("required_gates") or DEFAULT_REQUIRED_GATES)
        if not gates:
            raise ValueError("required_gates must not be empty")
''',
        '''        if "required_gates" in raw:
            gates = _clean_strings(raw.get("required_gates"))
        else:
            gates = DEFAULT_REQUIRED_GATES
        if not gates:
            raise ValueError("required_gates must not be empty")
''',
    )
    replace_once(
        "aura_forge.py",
        '''        self._runs: dict[str, dict[str, Any]] = {}
        self._run_counter = 0
''',
        '''        self._runs: dict[str, dict[str, Any]] = {}
''',
    )
    replace_once(
        "aura_forge.py",
        '''        repo_digest = self.bridge.aura_repo_digest(include_hubs=False, max_lines=80)
        if not repo_digest.get("ok"):
''',
        '''        try:
            repo_digest = self.bridge.aura_repo_digest(include_hubs=False, max_lines=80)
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "repository_digest_error",
                stage="GROUND",
                details={"exception_type": type(exc).__name__},
            )
        if not repo_digest.get("ok"):
''',
    )
    replace_once(
        "aura_forge.py",
        '''        prepared = self.bridge.aura_prepare_arena(
            objective=request.objective,
            target_file=request.target_file,
            target_symbol=request.target_symbol,
            acceptance_criteria=list(request.acceptance_criteria),
            risk_map=list(request.risk_map),
            constraints=list(dict.fromkeys(all_constraints)),
        )
''',
        '''        try:
            prepared = self.bridge.aura_prepare_arena(
                objective=request.objective,
                target_file=request.target_file,
                target_symbol=request.target_symbol,
                acceptance_criteria=list(request.acceptance_criteria),
                risk_map=list(request.risk_map),
                constraints=list(dict.fromkeys(all_constraints)),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "arena_prepare_error",
                stage="PLAN",
                details={"exception_type": type(exc).__name__},
            )
''',
    )
    replace_once(
        "aura_forge.py",
        '''            micro = self.bridge.aura_get_micro_context(
                plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
                task_id=task_id,
                depth=1,
                format="both",
                max_tokens_est=min(800, request.max_context_tokens),
            )
''',
        '''            try:
                micro = self.bridge.aura_get_micro_context(
                    plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
                    task_id=task_id,
                    depth=1,
                    format="both",
                    max_tokens_est=min(800, request.max_context_tokens),
                )
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "task_micro_context_error",
                    stage="GROUND",
                    details={"task_id": task_id, "exception_type": type(exc).__name__},
                )
''',
    )
    replace_once(
        "aura_forge.py",
        '''        self._run_counter += 1
        run_id = f"FORGE-{contract.contract_id[:16]}-{self._run_counter:04d}"
''',
        '''        run_id = f"FORGE-{contract.contract_id[:16]}-{uuid.uuid4().hex[:12]}"
''',
    )
    replace_once(
        "aura_forge.py",
        '''        manager = self._session_manager_factory(request, self.bridge, self.repo_root)
        opened = manager.open_prepared_session(
            prepared_arena=state["prepared"],
            objective=request.objective,
            provider=request.provider,
            model=request.model,
            run_id=run_id,
            metadata={
                **dict(request.metadata),
                "forge_version": FORGE_VERSION,
                "forge_contract_id": state["contract"].contract_id,
            },
        )
''',
        '''        try:
            manager = self._session_manager_factory(request, self.bridge, self.repo_root)
            opened = manager.open_prepared_session(
                prepared_arena=state["prepared"],
                objective=request.objective,
                provider=request.provider,
                model=request.model,
                run_id=run_id,
                metadata={
                    **dict(request.metadata),
                    "forge_version": FORGE_VERSION,
                    "forge_contract_id": state["contract"].contract_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            state["status"] = "BLOCKED_SESSION_EXCEPTION"
            return self._error(
                "controlled_session_open_error",
                stage="ACT",
                details={"exception_type": type(exc).__name__},
            )
''',
    )
    replace_once(
        "aura_forge.py",
        '''        result = manager.submit_response(
            session_id=state["session_id"],
            turn_id=str(turn_id),
            response=str(response or ""),
            provider_usage=_sanitize(dict(provider_usage or {})),
        )
''',
        '''        try:
            result = manager.submit_response(
                session_id=state["session_id"],
                turn_id=str(turn_id),
                response=str(response or ""),
                provider_usage=_sanitize(dict(provider_usage or {})),
            )
        except Exception as exc:  # noqa: BLE001
            state["status"] = "BLOCKED_SUBMIT_EXCEPTION"
            return self._error(
                "controlled_session_submit_error",
                stage="ACT",
                details={"exception_type": type(exc).__name__},
            )
''',
    )
    replace_once(
        "aura_forge.py",
        '''        if manager is not None:
            current = manager.get_session(state["session_id"])
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])
''',
        '''        if manager is not None:
            try:
                current = manager.get_session(state["session_id"])
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "controlled_session_status_error",
                    stage="STATUS",
                    details={"exception_type": type(exc).__name__},
                )
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])
''',
    )
    replace_once(
        "aura_forge.py",
        '''        if manager is not None:
            current = manager.get_session(state["session_id"])
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])

        last_result = dict(state.get("last_result") or {})
''',
        '''        if manager is not None:
            try:
                current = manager.get_session(state["session_id"])
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "controlled_session_review_error",
                    stage="DECIDE",
                    details={"exception_type": type(exc).__name__},
                )
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])

        last_result = dict(state.get("last_result") or {})
''',
    )
    replace_once(
        "aura_forge.py",
        '''        result = manager.export_session(state["session_id"], output_path)
''',
        '''        try:
            result = manager.export_session(state["session_id"], output_path)
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "controlled_session_export_error",
                stage="EXPORT",
                details={"exception_type": type(exc).__name__},
            )
''',
    )
    start = '''def validate_forge_contract(value: Mapping[str, Any]) -> list[str]:
    """Return structural contract errors without granting execution authority."""
'''
    end = '''

__all__ = [
'''
    target = Path("aura_forge.py")
    text = target.read_text(encoding="utf-8")
    left = text.index(start)
    right = text.index(end, left)
    replacement = '''def validate_forge_contract(value: Mapping[str, Any]) -> list[str]:
    """Return structural contract errors without granting execution authority."""
    required = {
        "version", "contract_id", "request_digest", "objective", "objective_digest",
        "repository", "plan_phase_hash", "act_capsules", "task_evidence",
        "required_gates", "allowed_files", "worker_contract", "authority", "lifecycle",
    }
    errors = [f"missing:{name}" for name in sorted(required - set(value))]
    if value.get("version") != FORGE_CONTRACT_VERSION:
        errors.append("unsupported_version")
    for name in ("contract_id", "request_digest", "objective", "objective_digest", "plan_phase_hash"):
        if not str(value.get(name) or "").strip():
            errors.append(f"{name}_must_not_be_empty")
    if not isinstance(value.get("repository"), Mapping):
        errors.append("repository_must_be_object")
    if not isinstance(value.get("worker_contract"), Mapping):
        errors.append("worker_contract_must_be_object")

    authority = value.get("authority")
    expected_authority = {
        "planning_proposes": True,
        "verification_proves": True,
        "human_authorizes": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
    }
    if isinstance(authority, Mapping):
        for name, expected in expected_authority.items():
            if authority.get(name) != expected:
                errors.append(f"invalid_authority:{name}")
    else:
        errors.append("authority_must_be_object")

    required_gates = list(value.get("required_gates") or [])
    if not required_gates:
        errors.append("required_gates_must_not_be_empty")
    else:
        unsupported = sorted(set(required_gates) - SUPPORTED_REQUIRED_GATES)
        if unsupported:
            errors.append(f"unsupported_required_gates:{','.join(unsupported)}")
    if not list(value.get("act_capsules") or []):
        errors.append("act_capsules_must_not_be_empty")
    if not list(value.get("task_evidence") or []):
        errors.append("task_evidence_must_not_be_empty")

    expected_lifecycle = ["FRAME", "GROUND", "PLAN", "ACT", "PROVE", "DECIDE", "DISSOLVE"]
    if list(value.get("lifecycle") or []) != expected_lifecycle:
        errors.append("invalid_lifecycle")

    allowed_files = value.get("allowed_files")
    if not isinstance(allowed_files, list):
        errors.append("allowed_files_must_be_array")
    else:
        for item in allowed_files:
            try:
                _safe_repo_path(item, field_name="allowed_file")
            except ValueError:
                errors.append(f"invalid_allowed_file:{item}")
    return errors
'''
    target.write_text(text[:left] + replacement + text[right:], encoding="utf-8")


def patch_tests() -> None:
    replace_once(
        "tests/test_aura_forge.py",
        '''    first = runtime_a.prepare(request())
    second = runtime_b.prepare(request())

    assert first["contract"]["contract_id"] == second["contract"]["contract_id"]
    assert first["run_id"].endswith("-0001")
    assert second["run_id"].endswith("-0001")
''',
        '''    first = runtime_a.prepare(request())
    second = runtime_b.prepare(request())
    third = runtime_a.prepare(request())

    assert first["contract"]["contract_id"] == second["contract"]["contract_id"]
    assert first["contract"]["contract_id"] == third["contract"]["contract_id"]
    assert first["run_id"] != second["run_id"]
    assert first["run_id"] != third["run_id"]
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''    metadata = runtime.prepare({"objective": "x", "metadata": ["not", "an", "object"]})

    assert criteria["ok"] is False
''',
        '''    metadata = runtime.prepare({"objective": "x", "metadata": ["not", "an", "object"]})
    empty_gates = runtime.prepare({"objective": "x", "required_gates": []})

    assert criteria["ok"] is False
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''    assert metadata["error"] == "metadata must be an object"
''',
        '''    assert metadata["error"] == "metadata must be an object"
    assert empty_gates["ok"] is False
    assert empty_gates["error"] == "required_gates must not be empty"
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
        '''def test_contract_validator_rejects_authority_and_lifecycle_tampering(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["authority"]["automatic_push"] = True
    contract["lifecycle"] = ["FRAME", "ACT"]
    contract["allowed_files"] = ["../escape.py"]

    errors = validate_forge_contract(contract)

    assert "invalid_authority:automatic_push" in errors
    assert "invalid_lifecycle" in errors
    assert "invalid_allowed_file:../escape.py" in errors


def test_bridge_exceptions_fail_closed(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)

    def explode(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("secret backend detail")

    bridge.aura_repo_digest = explode  # type: ignore[method-assign]
    result = runtime.prepare(request())

    assert result["ok"] is False
    assert result["error"] == "repository_digest_error"
    assert result["details"] == {"exception_type": "RuntimeError"}


def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
    )


def patch_schema() -> None:
    target = Path("schemas/aura_forge_arena_evidence_contract.schema.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    authority = payload["properties"]["authority"]
    required = set(authority.get("required", []))
    required.update({"planning_proposes", "verification_proves", "human_authorizes"})
    authority["required"] = sorted(required)
    authority["properties"].update({
        "planning_proposes": {"const": True},
        "verification_proves": {"const": True},
        "human_authorizes": {"const": True},
    })
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    patch_source()
    patch_tests()
    patch_schema()


if __name__ == "__main__":
    main()
