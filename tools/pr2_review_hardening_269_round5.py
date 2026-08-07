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


runtime_path = "aura_ephemeral_workspace_runtime_v2.py"
text = read(runtime_path)
text = replace_once(
    text,
    '    moment = time.time() if timestamp is None else _finite(timestamp, "timestamp")\n',
    '    moment = _trusted_now(timestamp)\n',
    "authoritative certificate advancement timestamp",
)
write(runtime_path, text)


test_path = "tests/test_aura_ephemeral_workspace_runtime_v2.py"
text = read(test_path)
anchor = '''def test_master_negative_runtime_cannot_close_certificate_with_self_proof(tmp_path: Path) -> None:\n'''
regression = '''def test_certificate_advancement_clamps_backdated_receipt_timestamp_to_trusted_now(\n    tmp_path: Path,\n) -> None:\n    _, registry, _, _, store, workspace_id = _admitted(tmp_path)\n    assert runtime.activate_workspace_v2(\n        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),\n    )["ok"]\n    prepared = runtime.prepare_spatial_action_certificate_v2(\n        workspace_id, store=store,\n        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",\n        subject_refs=["source:aura"], target_refs=["forge:candidate"],\n        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",\n        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",\n        assumptions_digest=D["3"], cost_microusd=0, reversible=True,\n        proof_obligations=["EXACT_SOURCE"], nonce="cert-trusted-receipt-time",\n        expires_at=time.time() + 120,\n    )["certificate"]\n    real_before = time.time()\n    advanced = runtime.advance_spatial_action_certificate_v2(\n        workspace_id, store=store, expected_status="PREPARED",\n        evidence_digest=D["4"], owner="spatial_runtime",\n        timestamp=prepared["issued_at"] - 3600,\n    )["certificate"]\n    receipt_time = advanced["receipts"][-1]["timestamp"]\n    assert receipt_time >= real_before\n    assert receipt_time > prepared["issued_at"] - 3600\n\n\n'''
text = replace_once(text, anchor, regression + anchor, "trusted receipt timestamp regression")
write(test_path, text)


doc_path = "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md"
text = read(doc_path)
text = replace_once(
    text,
    "The registry binds deterministic callable bytes rather than process-specific\n`repr()` values. Revocation changes the adapter identity and blocks later calls.\n",
    "The registry binds portable callable source identity (module, qualified name, and\nSHA-256 of source text) rather than process- or checkout-specific bytecode/`repr()`\nvalues. Revocation changes the adapter identity and blocks later calls.\n",
    "portable adapter identity documentation",
)
write(doc_path, text)
