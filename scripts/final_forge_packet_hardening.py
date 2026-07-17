from __future__ import annotations

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
        '''        self._runs: dict[str, dict[str, Any]] = {}
        self._run_counter = 0
''',
        '''        self._runs: dict[str, dict[str, Any]] = {}
''',
    )
    replace_once(
        "aura_forge.py",
        '''        if not repo_digest.get("ok"):
''',
        '''        if not isinstance(repo_digest, Mapping):
            return self._error("repository_digest_invalid", stage="GROUND")
        if not repo_digest.get("ok"):
''',
    )
    replace_once(
        "aura_forge.py",
        '''        if not prepared.get("ok"):
''',
        '''        if not isinstance(prepared, Mapping):
            return self._error("arena_prepare_invalid", stage="PLAN")
        if not prepared.get("ok"):
''',
    )
    replace_once(
        "aura_forge.py",
        '''            if not micro.get("ok"):
''',
        '''            if not isinstance(micro, Mapping):
                return self._error(
                    "task_micro_context_invalid",
                    stage="GROUND",
                    details={"task_id": task_id},
                )
            if not micro.get("ok"):
''',
    )
    replace_once(
        "aura_forge.py",
        '''        if not opened.get("session_created"):
''',
        '''        if not isinstance(opened, Mapping):
            state["status"] = "BLOCKED_SESSION_INVALID"
            return self._error("controlled_session_open_invalid", stage="ACT")
        if not opened.get("session_created"):
''',
    )
    replace_once(
        "aura_forge.py",
        '''        state["last_result"] = dict(result)
''',
        '''        if not isinstance(result, Mapping):
            state["status"] = "BLOCKED_SUBMIT_INVALID"
            return self._error("controlled_session_submit_invalid", stage="ACT")
        state["last_result"] = dict(result)
''',
    )
    replace_once(
        "aura_forge.py",
        '''            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])
        review_packet = (
''',
        '''            if not isinstance(current, Mapping):
                return self._error("controlled_session_status_invalid", stage="STATUS")
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])
        review_packet = (
''',
    )
    replace_once(
        "aura_forge.py",
        '''            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])

        last_result = dict(state.get("last_result") or {})
''',
        '''            if not isinstance(current, Mapping):
                return self._error("controlled_session_review_invalid", stage="DECIDE")
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])

        last_result = dict(state.get("last_result") or {})
''',
    )
    replace_once(
        "aura_forge.py",
        '''        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
''',
        '''        if not isinstance(result, Mapping):
            return self._error("controlled_session_export_invalid", stage="EXPORT")
        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
''',
    )
    replace_once(
        "aura_forge.py",
        '''def validate_forge_contract(value: Mapping[str, Any]) -> list[str]:
    """Return structural contract errors without granting execution authority."""
    required = {
''',
        '''def validate_forge_contract(value: Mapping[str, Any]) -> list[str]:
    """Return structural contract errors without granting execution authority."""
    if not isinstance(value, Mapping):
        return ["contract_must_be_object"]
    required = {
''',
    )
    replace_once(
        "aura_forge.py",
        '''    required_gates = list(value.get("required_gates") or [])
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
''',
        '''    gates_value = value.get("required_gates")
    if not isinstance(gates_value, (list, tuple)):
        errors.append("required_gates_must_be_array")
    elif not gates_value:
        errors.append("required_gates_must_not_be_empty")
    else:
        unsupported = sorted(set(gates_value) - SUPPORTED_REQUIRED_GATES)
        if unsupported:
            errors.append(f"unsupported_required_gates:{','.join(unsupported)}")

    capsules_value = value.get("act_capsules")
    if not isinstance(capsules_value, (list, tuple)):
        errors.append("act_capsules_must_be_array")
    elif not capsules_value:
        errors.append("act_capsules_must_not_be_empty")

    evidence_value = value.get("task_evidence")
    if not isinstance(evidence_value, (list, tuple)):
        errors.append("task_evidence_must_be_array")
    elif not evidence_value:
        errors.append("task_evidence_must_not_be_empty")

    expected_lifecycle = ["FRAME", "GROUND", "PLAN", "ACT", "PROVE", "DECIDE", "DISSOLVE"]
    lifecycle_value = value.get("lifecycle")
    if not isinstance(lifecycle_value, (list, tuple)) or list(lifecycle_value) != expected_lifecycle:
        errors.append("invalid_lifecycle")
''',
    )


def patch_tests() -> None:
    replace_once(
        "tests/test_aura_forge.py",
        '''def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
        '''def test_contract_validator_never_raises_on_malformed_arrays(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["required_gates"] = 7
    contract["act_capsules"] = {"bad": "shape"}
    contract["task_evidence"] = None
    contract["lifecycle"] = 42

    errors = validate_forge_contract(contract)

    assert "required_gates_must_be_array" in errors
    assert "act_capsules_must_be_array" in errors
    assert "task_evidence_must_be_array" in errors
    assert "invalid_lifecycle" in errors
    assert validate_forge_contract([]) == ["contract_must_be_object"]  # type: ignore[arg-type]


def test_invalid_bridge_packet_fails_closed(tmp_path: Path) -> None:
    runtime, bridge, _manager = build_runtime(tmp_path)
    bridge.aura_repo_digest = lambda **_kwargs: None  # type: ignore[method-assign]

    result = runtime.prepare(request())

    assert result["ok"] is False
    assert result["error"] == "repository_digest_invalid"


def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
    )


def main() -> None:
    patch_source()
    patch_tests()


if __name__ == "__main__":
    main()
