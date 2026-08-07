from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text.rstrip() + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Certificate APIs must converge expired workspaces through cleanup before
# inspecting or mutating certificate state. This keeps TTL, lease, and sandbox
# lifecycle semantics identical to the execution path.
path = "aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
text = replace_once(
    text,
    '''    """Prepare a proposal-only certificate; no domain operation is authorized."""
    record = _workspace(store, workspace_id)
''',
    '''    """Prepare a proposal-only certificate; no domain operation is authorized."""
    _expire_if_needed(workspace_id, store=store, now=now)
    record = _workspace(store, workspace_id)
''',
    "certificate preparation expiry cleanup",
)
text = replace_once(
    text,
    '''    """Advance one exact receipt step under ACTIVE-state certificate CAS."""
    record = _workspace(store, workspace_id)
''',
    '''    """Advance one exact receipt step under ACTIVE-state certificate CAS."""
    _expire_if_needed(workspace_id, store=store, now=timestamp)
    record = _workspace(store, workspace_id)
''',
    "certificate advancement expiry cleanup",
)
write(path, text)


path = "tests/test_aura_ephemeral_workspace_runtime_v2.py"
text = read(path)

# Positive proof that unchanged identity closure really reuses VERIFIED receipts.
anchor = '''    assert independent in plan2["reexecute_node_ids"]


def test_action_certificate_lifecycle_is_monotonic_owner_bound_and_non_authoritative(tmp_path: Path) -> None:
'''
replacement = '''    assert independent in plan2["reexecute_node_ids"]


def test_partial_reexecution_reuses_verified_receipts_when_identity_closure_is_unchanged(
    tmp_path: Path,
) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    _execute_all(workspace_id, graph, store, registry)
    receipts = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["node_receipts"]
    plan = runtime.partial_reexecution_plan_v2(
        graph, prior_receipts=receipts, changed_node_ids=[],
    )
    assert set(plan["reusable_node_ids"]) == set(receipts)
    assert plan["reexecute_node_ids"] == []


def test_action_certificate_lifecycle_is_monotonic_owner_bound_and_non_authoritative(tmp_path: Path) -> None:
'''
text = replace_once(text, anchor, replacement, "positive partial reexecution regression")

# Expired certificate preparation must also dissolve/revoke the workspace.
text = replace_once(
    text,
    '''    with pytest.raises(ValueError, match="certificate expiry"):
        runtime.prepare_spatial_action_certificate_v2(
            workspace_id, store=store,
            principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
            subject_refs=["source:aura"], target_refs=["forge:candidate"],
            policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
            runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
            assumptions_digest=D["3"], cost_microusd=0, reversible=True,
            proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-prepare",
            expires_at=time.time() + 120, now=time.time() - 3600,
        )

    _, registry2, _, _, store2, workspace_id2 = _admitted(tmp_path / "advance")
''',
    '''    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.prepare_spatial_action_certificate_v2(
            workspace_id, store=store,
            principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
            subject_refs=["source:aura"], target_refs=["forge:candidate"],
            policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
            runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
            assumptions_digest=D["3"], cost_microusd=0, reversible=True,
            proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-prepare",
            expires_at=time.time() + 120, now=time.time() - 3600,
        )
    prepared_record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert prepared_record["state"] == "DISSOLVED"
    assert prepared_record["lease_status"] == "REVOKED"

    _, registry2, _, _, store2, workspace_id2 = _admitted(tmp_path / "advance")
''',
    "certificate preparation dissolves expired workspace regression",
)

# Expired certificate advancement must converge through the same cleanup path.
text = replace_once(
    text,
    '''    with pytest.raises(ValueError, match="workspace_certificate_invalidated"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id2, store=store2, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
            timestamp=prepared["issued_at"],
        )
''',
    '''    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id2, store=store2, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
            timestamp=prepared["issued_at"],
        )
    advanced_record = runtime.workspace_status_v2(workspace_id2, store=store2)["workspace"]
    assert advanced_record["state"] == "DISSOLVED"
    assert advanced_record["lease_status"] == "REVOKED"
''',
    "certificate advancement dissolves expired workspace regression",
)
write(path, text)
