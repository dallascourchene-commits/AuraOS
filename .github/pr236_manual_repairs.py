from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str, *, applied_marker: str = "") -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if applied_marker and applied_marker in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one match in {path}, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_compass() -> None:
    old = '''def _semantic_obligations(
    payload: Mapping[str, Any],
    bilateral: BilateralPlanningContract,
) -> dict[str, Any]:
    """Project only obligations grounded in the exact Atlas payload."""
    text = json.dumps(payload, sort_keys=True, default=str).lower()

    def matched(values: Sequence[str]) -> list[str]:
        return [
            value
            for value in values
            if value.lower() in text
            or any(
                len(token) >= 5 and token in text
                for token in re.findall(r"[a-z0-9_./-]+", value.lower())
            )
        ]

    obligation = {
        "positive_requirements": matched(bilateral.positive_requirements),
        "negative_requirements_at_risk": matched(bilateral.negative_requirements),
        "guardrail_ids": matched(
            (
                *bilateral.hard_guardrail_ids,
                *bilateral.human_guardrail_ids,
                *bilateral.editable_guardrail_ids,
            )
        ),
        "required_verifiers": matched(bilateral.required_verifiers),
        "repository_head": bilateral.repository_head,
        "allowed_path_set_digest": bilateral.allowed_path_set_digest,
    }
    grounded_keys = (
        "positive_requirements",
        "negative_requirements_at_risk",
        "guardrail_ids",
        "required_verifiers",
    )
    return obligation if any(obligation[key] for key in grounded_keys) else {}
'''
    new = '''_STRUCTURED_ATLAS_REFERENCE_KEYS = frozenset(
    {
        "participant_refs",
        "participant_ref",
        "participant_id",
        "canonical_ref",
        "evidence_refs",
        "evidence_ref",
        "file_path",
        "file",
        "path",
        "qualified_symbol",
        "symbol",
    }
)


def _structured_atlas_references(payload: Mapping[str, Any]) -> set[str]:
    """Collect only explicitly typed Atlas references, never prose tokens."""
    references: set[str] = set()

    def add(raw: Any) -> None:
        value = str(raw or "").replace("\\\\", "/").strip().lower()
        if not value:
            return
        references.add(value)
        for prefix in ("file:", "path:", "symbol:", "participant:", "participant_id:"):
            if value.startswith(prefix):
                references.add(value[len(prefix):].strip())
        for separator in ("::", "#", "@"):
            if separator in value:
                references.update(part.strip() for part in value.split(separator) if part.strip())

    def visit(value: Any, *, typed: bool = False) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                key_is_typed = str(key).lower() in _STRUCTURED_ATLAS_REFERENCE_KEYS
                visit(item, typed=typed or key_is_typed)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item, typed=typed)
        elif typed and isinstance(value, (str, int)):
            add(value)

    visit(payload)
    return references


def _reference_targets_path(reference: str, path: str) -> bool:
    reference = reference.replace("\\\\", "/").strip().lower()
    path = path.replace("\\\\", "/").strip().lower().lstrip("./")
    if not reference or not path:
        return False
    candidates = {reference}
    for prefix in ("file:", "path:", "participant:", "participant_id:"):
        if reference.startswith(prefix):
            candidates.add(reference[len(prefix):].strip())
    return any(
        candidate == path
        or candidate.endswith("/" + path)
        or candidate.startswith(path + "#")
        or candidate.startswith(path + "::")
        or candidate.startswith(path + ":")
        or ("/" + path + "#") in candidate
        or ("/" + path + "::") in candidate
        for candidate in candidates
    )


def _semantic_obligations(
    payload: Mapping[str, Any],
    bilateral: BilateralPlanningContract,
) -> dict[str, Any]:
    """Project obligations only from structured Atlas scope references.

    Free-form notes, risks, effects, and other prose are intentionally ignored
    so coincidental words can never become semantic evidence.
    """
    references = _structured_atlas_references(payload)
    scope_grounded = any(
        _reference_targets_path(reference, allowed_path)
        for reference in references
        for allowed_path in bilateral.allowed_paths
    )
    if not scope_grounded:
        return {}
    return {
        "positive_requirements": list(bilateral.positive_requirements),
        "negative_requirements_at_risk": list(bilateral.negative_requirements),
        "guardrail_ids": list(
            dict.fromkeys(
                (
                    *bilateral.hard_guardrail_ids,
                    *bilateral.human_guardrail_ids,
                    *bilateral.editable_guardrail_ids,
                )
            )
        ),
        "required_verifiers": list(bilateral.required_verifiers),
        "repository_head": bilateral.repository_head,
        "allowed_path_set_digest": bilateral.allowed_path_set_digest,
    }
'''
    replace_once(
        "aura_coding_relationship_compass.py",
        old,
        new,
        applied_marker="_STRUCTURED_ATLAS_REFERENCE_KEYS",
    )


def patch_external_context() -> None:
    replace_once(
        "aura_external_llm_session.py",
        "def _diff_touched_files(diff: str) -> list[str]:\n",
        '''def _bounded_text(value: Any, max_tokens: int) -> str:
    """Bound text under the same deterministic token proxy used by turns."""
    text = str(value or "")
    max_chars = max(0, int(max_tokens)) * 4
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""
    marker = f"[TRUNCATED digest={_digest(text)} tokens={_token_estimate(text)}]\\n"
    if len(marker) >= max_chars:
        return marker[:max_chars]
    return marker + text[: max_chars - len(marker)]


def _diff_touched_files(diff: str) -> list[str]:
''',
        applied_marker="def _bounded_text(",
    )

    old = '''        compressed_context = str(micro.get("compressed_context", ""))
        bilateral_micro_context = dict(
            micro.get("bilateral_micro_context") or {}
        )
        if bilateral_micro_context:
            compressed_context += (
                "\\n\\n[BILATERAL_MICRO_CONTEXT]\\n"
                + json.dumps(
                    bilateral_micro_context,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )

        bounded_failure = _bounded_payload(
            failure_packet,
            max(96, session.max_context_tokens // 3),
        )
        fixed_context_tokens = _token_estimate(
            json.dumps(
                {
                    "compressed_context": compressed_context,
                    "failure_packet": bounded_failure,
                    "act_capsule": task,
                },
                default=str,
            )
        ) + 96
'''
    new = '''        compressed_context = str(micro.get("compressed_context", ""))
        bilateral_micro_context = dict(
            micro.get("bilateral_micro_context") or {}
        )
        bounded_failure = _bounded_payload(
            failure_packet,
            max(96, session.max_context_tokens // 3),
        )
        fixed_without_compressed_context = _token_estimate(
            json.dumps(
                {
                    "failure_packet": bounded_failure,
                    "act_capsule": task,
                },
                default=str,
            )
        ) + 96
        compressed_context_budget = max(
            0,
            session.max_context_tokens - fixed_without_compressed_context,
        )
        if bilateral_micro_context:
            compressed_context += (
                "\\n\\n[BILATERAL_MICRO_CONTEXT]\\n"
                + json.dumps(
                    bilateral_micro_context,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
        compressed_context = _bounded_text(
            compressed_context,
            compressed_context_budget,
        )
        fixed_context_tokens = _token_estimate(
            json.dumps(
                {
                    "compressed_context": compressed_context,
                    "failure_packet": bounded_failure,
                    "act_capsule": task,
                },
                default=str,
            )
        ) + 96
        if fixed_context_tokens > session.max_context_tokens:
            return None
'''
    replace_once(
        "aura_external_llm_session.py",
        old,
        new,
        applied_marker="fixed_without_compressed_context",
    )

    old_payload = '''        context_payload = {
            "compressed_context": compressed_context,
            "source_slices": source_slices,
            "test_slices": test_slices,
            "failure_packet": bounded_failure,
            "act_capsule": task,
        }
        turn_index = len(session.turns) + 1
'''
    new_payload = '''        context_payload = {
            "compressed_context": compressed_context,
            "source_slices": source_slices,
            "test_slices": test_slices,
            "failure_packet": bounded_failure,
            "act_capsule": task,
        }
        context_token_estimate = _token_estimate(
            json.dumps(context_payload, default=str)
        )
        while context_token_estimate > session.max_context_tokens and test_slices:
            test_slices.pop()
            context_payload["test_slices"] = test_slices
            context_token_estimate = _token_estimate(
                json.dumps(context_payload, default=str)
            )
        while context_token_estimate > session.max_context_tokens and source_slices:
            source_slices.pop()
            context_payload["source_slices"] = source_slices
            context_token_estimate = _token_estimate(
                json.dumps(context_payload, default=str)
            )
        if context_token_estimate > session.max_context_tokens:
            overflow = context_token_estimate - session.max_context_tokens
            compressed_context = _bounded_text(
                compressed_context,
                max(0, _token_estimate(compressed_context) - overflow - 8),
            )
            context_payload["compressed_context"] = compressed_context
            context_token_estimate = _token_estimate(
                json.dumps(context_payload, default=str)
            )
        if context_token_estimate > session.max_context_tokens:
            return None
        turn_index = len(session.turns) + 1
'''
    replace_once(
        "aura_external_llm_session.py",
        old_payload,
        new_payload,
        applied_marker="while context_token_estimate > session.max_context_tokens",
    )
    replace_once(
        "aura_external_llm_session.py",
        "            context_token_estimate=_token_estimate(json.dumps(context_payload, default=str)),\n",
        "            context_token_estimate=context_token_estimate,\n",
    )


def patch_connector() -> None:
    target = Path("aura_arena_architect_connector.py")
    text = target.read_text(encoding="utf-8")
    if "import subprocess\n" not in text:
        text = text.replace("from pathlib import Path\n", "from pathlib import Path\nimport subprocess\n", 1)
    marker = '"error": "repository_identity_unavailable"'
    if marker not in text:
        old = '''            identity = _repository_identity(self.repo_root)
            _trusted_bilateral_handoff = _mint_trusted_bilateral_handoff(
'''
        new = '''            try:
                identity = _repository_identity(self.repo_root)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                return {
                    "ok": False,
                    "error": "repository_identity_unavailable",
                    "error_category": "mcp_protocol_error",
                    "message": (
                        "Bilateral preparation was denied because the exact "
                        "repository identity could not be observed."
                    ),
                    "repair_hint": (
                        "REPOSITORY_IDENTITY: restore exact-head/source-tree "
                        "observation and reconfirm before preparation."
                    ),
                    "deterministic_denial": True,
                    "council_override_allowed": False,
                    "human_reconfirmation_required": True,
                    "exception_type": type(exc).__name__,
                    "proposal_only": True,
                    "human_review_required": True,
                    "production_mutation": False,
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                }
            _trusted_bilateral_handoff = _mint_trusted_bilateral_handoff(
'''
        if text.count(old) != 1:
            raise SystemExit("connector identity call did not match exactly once")
        text = text.replace(old, new, 1)
    target.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    target = Path("tests/test_aura_bilateral_planning_enforcement.py")
    text = target.read_text(encoding="utf-8")
    if "AuraExternalLLMSessionManager" not in text:
        text = text.replace(
            "from aura_arena_architect_connector import AuraArenaArchitectConnector\n",
            "from aura_arena_architect_connector import AuraArenaArchitectConnector\n"
            "from aura_architect_control import normalize_control_profile\n"
            "from aura_external_llm_session import (\n"
            "    AuraExternalLLMSessionManager,\n"
            "    ExternalLLMSession,\n"
            ")\n",
            1,
        )
    if 'assert "SCOPE_PRESERVATION" in result["repair_hint"]' not in text:
        text = text.replace(
            '    assert result["error_category"] == "scope_too_broad"\n\n\n@pytest.mark.parametrize',
            '    assert result["error_category"] == "scope_too_broad"\n'
            '    assert "SCOPE_PRESERVATION" in result["repair_hint"]\n\n\n@pytest.mark.parametrize',
            1,
        )
    if 'assert unprojected["positive_requirements"]' not in text:
        text = text.replace(
            '    assert unprojected["negative_requirements"]\n',
            '    assert unprojected["positive_requirements"]\n'
            '    assert unprojected["negative_requirements"]\n',
            1,
        )
    old = '''    note = " ".join(
        [
            *bilateral_contract.positive_requirements,
            *bilateral_contract.negative_requirements,
            *bilateral_contract.hard_guardrail_ids,
            *bilateral_contract.human_guardrail_ids,
            *bilateral_contract.editable_guardrail_ids,
            *bilateral_contract.required_verifiers,
        ]
    )
    packet = _compile_compass_with_forced_assessments(
        bilateral_contract,
        [{"assessment_id": "a1", "participant_refs": ["x"], "note": note}],
        monkeypatch,
    )
'''
    new = '''    packet = _compile_compass_with_forced_assessments(
        bilateral_contract,
        [
            {
                "assessment_id": "a1",
                "participant_refs": [
                    f"file:{bilateral_contract.allowed_paths[0]}#assess_plan"
                ],
            }
        ],
        monkeypatch,
    )
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit("fully projected Compass test block did not match")

    marker = "def test_external_llm_turn_bounds_large_bilateral_micro_context"
    if marker not in text:
        text += '''

class _LargeBilateralMicroContextBridge:
    def aura_get_micro_context(self, **_: object) -> dict:
        return {
            "ok": True,
            "compressed_context": "base context",
            "bilateral_micro_context": {
                "positive_requirements": ["x" * 20_000],
                "negative_requirements": ["y" * 20_000],
            },
            "line_ranges": [],
            "tests": [],
        }

    def aura_read_slice(self, **_: object) -> dict:
        return {"ok": False}


def test_external_llm_turn_bounds_large_bilateral_micro_context() -> None:
    manager = AuraExternalLLMSessionManager(
        repo_root=".",
        bridge=_LargeBilateralMicroContextBridge(),
    )
    session = ExternalLLMSession(
        session_id="ELLM-bounded",
        objective="Keep bilateral context bounded.",
        plan_phase_hash="phase",
        provider="test",
        model="stub",
        act_capsules=[
            {
                "task_id": "T1",
                "objective": "Bound context.",
                "target_file": "aura_external_llm_session.py",
                "target_symbol": "AuraExternalLLMSessionManager._build_turn",
            }
        ],
        max_context_tokens=256,
        max_output_tokens=256,
        max_turns=2,
    )
    turn = manager._build_turn(session, role="worker", failure_packet={})
    assert turn is not None
    assert turn.context_token_estimate <= session.max_context_tokens
    assert len(turn.compressed_context) <= session.max_context_tokens * 4
    assert "TRUNCATED" in turn.compressed_context


def test_prepare_selected_plan_denies_repository_identity_failure(
    bilateral_contract: BilateralPlanningContract,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = AuraArenaArchitectConnector(
        repo_root=".",
        bridge=AuraAgentArenaBridge(repo_root="."),
    )

    def _boom(*_: object, **__: object) -> None:
        raise subprocess.SubprocessError("identity unavailable")

    monkeypatch.setattr("aura_arena_gate_dialogue._repository_identity", _boom)
    result = connector._prepare_selected_plan(
        objective="Fail closed when repository identity is unavailable.",
        selected_plan=_complete_plan(bilateral_contract),
        profile=normalize_control_profile(None, surface="native"),
        bilateral_contract=bilateral_contract,
        bilateral_gate={"passed": True},
    )
    assert result["ok"] is False
    assert result["error"] == "repository_identity_unavailable"
    assert result["deterministic_denial"] is True
    assert result["council_override_allowed"] is False
    assert result["human_reconfirmation_required"] is True
'''
    target.write_text(text, encoding="utf-8")


def main() -> None:
    patch_compass()
    patch_external_context()
    patch_connector()
    patch_tests()


if __name__ == "__main__":
    main()
