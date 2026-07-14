from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once_or_present(
    path: str,
    old: str,
    new: str,
    *,
    marker: str | None = None,
) -> None:
    text = read(path)
    present = marker or new
    if present in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"expected one source span in {path}, found {count}; marker={present!r}"
        )
    write(path, text.replace(old, new, 1))


def replace_required(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"required text not found in {path}: {old!r}")
    write(path, text.replace(old, new))


def harden_event_contracts() -> None:
    replace_once_or_present(
        "aura_event_contracts.py",
        '''def _normalize_field_name(value: Any) -> str:\n    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value).strip())\n    return text.lower().replace("-", "_").replace(" ", "_")\n''',
        '''def _normalize_field_name(value: Any) -> str:\n    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value).strip())\n    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")\n''',
        marker='return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")',
    )
    replace_once_or_present(
        "aura_event_contracts.py",
        '''_COMPACT_PRIVATE_REASONING_KEYS = frozenset(\n    item.replace("_", "") for item in _NORMALIZED_PRIVATE_REASONING_KEYS\n)\n_PRIVATE_REASONING_SUFFIXES = tuple(\n    f"_{item}" for item in sorted(_NORMALIZED_PRIVATE_REASONING_KEYS)\n)\n''',
        '''_COMPACT_PRIVATE_REASONING_KEYS = frozenset(\n    item.replace("_", "") for item in _NORMALIZED_PRIVATE_REASONING_KEYS\n)\n_COMPACT_PRIVATE_REASONING_SUFFIXES = frozenset(\n    item for item in _COMPACT_PRIVATE_REASONING_KEYS if len(item) >= 8\n)\n_PRIVATE_REASONING_SUFFIXES = tuple(\n    f"_{item}" for item in sorted(_NORMALIZED_PRIVATE_REASONING_KEYS)\n)\n''',
        marker="_COMPACT_PRIVATE_REASONING_SUFFIXES",
    )
    replace_once_or_present(
        "aura_event_contracts.py",
        '''        or compact in _COMPACT_PRIVATE_REASONING_KEYS\n        or any(compact.endswith(item) for item in _COMPACT_PRIVATE_REASONING_KEYS)\n''',
        '''        or compact in _COMPACT_PRIVATE_REASONING_KEYS\n        or any(\n            compact.endswith(item)\n            for item in _COMPACT_PRIVATE_REASONING_SUFFIXES\n        )\n''',
        marker="for item in _COMPACT_PRIVATE_REASONING_SUFFIXES",
    )


def harden_workflow_gates() -> None:
    replace_once_or_present(
        "aura_workflow_gates.py",
        '''def _authority_requirement(state: WorkflowState, evidence: Mapping[str, Any]) -> Dict[str, str]:\n    defaults = _AUTHORITY_SCOPE_BY_STATE.get(state.name, {})\n    return {\n        "policy_scope": str(\n            evidence.get("required_policy_scope", defaults.get("policy_scope", ""))\n        ),\n        "capability_scope": str(\n            evidence.get(\n                "required_capability_scope",\n                defaults.get("capability_scope", ""),\n            )\n        ),\n    }\n''',
        '''def _authority_requirement(state: WorkflowState, evidence: Mapping[str, Any]) -> Dict[str, str]:\n    defaults = _AUTHORITY_SCOPE_BY_STATE.get(state.name, {})\n    policy_scope = defaults.get("policy_scope")\n    capability_scope = defaults.get("capability_scope")\n    return {\n        "policy_scope": str(\n            policy_scope\n            if policy_scope is not None\n            else evidence.get("required_policy_scope", "")\n        ),\n        "capability_scope": str(\n            capability_scope\n            if capability_scope is not None\n            else evidence.get("required_capability_scope", "")\n        ),\n    }\n''',
        marker="policy_scope if policy_scope is not None",
    )
    replace_once_or_present(
        "aura_workflow_gates.py",
        '''            verified_ids = {\n                str(item)\n                for item in evidence.get("verified_governance_decision_ids", ())\n            }\n''',
        '''            raw_verified_ids = evidence.get(\n                "verified_governance_decision_ids", ()\n            )\n            if isinstance(raw_verified_ids, (str, bytes)):\n                raise ValueError(\n                    "verified_governance_decision_ids must be a collection"\n                )\n            verified_ids = {\n                str(item).strip()\n                for item in raw_verified_ids\n                if str(item).strip()\n            }\n''',
        marker="verified_governance_decision_ids must be a collection",
    )
    replace_once_or_present(
        "aura_workflow_gates.py",
        '    if bool(evidence.get("human_approval")):\n',
        '    if evidence.get("human_approval") is True:\n',
        marker='evidence.get("human_approval") is True',
    )
    replace_required(
        "aura_workflow_gates.py",
        '"prior_state_verified_or_repair"',
        '"prior_state_agent_running_or_repair"',
    )
    replace_required(
        "aura_workflow_gates.py",
        '"requires_prior_state": ["VERIFIED", "REPAIR_REQUIRED"]',
        '"requires_prior_state": ["AGENT_RUNNING", "REPAIR_REQUIRED"]',
    )
    text = read("aura_workflow_gates.py")
    text = text.replace(
        "``PATCH_PROPOSED`` requires the prior state to be ``VERIFIED``",
        "``PATCH_PROPOSED`` requires the prior state to be ``AGENT_RUNNING``",
    )
    text = text.replace(
        "``PATCH_PROPOSED`` requires\n   ``VERIFIED`` or ``REPAIR_REQUIRED``",
        "``PATCH_PROPOSED`` requires\n   ``AGENT_RUNNING`` or ``REPAIR_REQUIRED``",
    )
    write("aura_workflow_gates.py", text)


def harden_relational_authority() -> None:
    replace_once_or_present(
        "aura_relational_authority.py",
        '''            parent_grant.validate(\n                now=current_time,\n                verified_authority_refs=trusted,\n            )\n            resolved_parent_ref = parent_grant.grant_id\n''',
        '''            parent_grant.validate(\n                now=current_time,\n                verified_authority_refs=trusted,\n            )\n            parent_grant._validate_identity()\n            resolved_parent_ref = parent_grant.grant_id\n''',
        marker="parent_grant._validate_identity()",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''        grant.validate(\n            now=current_time,\n            verified_authority_refs=verified_authority_refs,\n        )\n\n        principal = _required(principal_id, "principal_id")\n''',
        '''        grant.validate(\n            now=current_time,\n            verified_authority_refs=verified_authority_refs,\n        )\n        grant._validate_identity()\n        if created < grant.valid_from:\n            raise ValueError("attestation cannot predate its authority grant")\n\n        principal = _required(principal_id, "principal_id")\n''',
        marker="attestation cannot predate its authority grant",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''        if self.capability_scope not in grant.capability_scopes:\n            raise ValueError("attestation uses an unauthorized capability scope")\n        if current_time < self.created_at:\n''',
        '''        if self.capability_scope not in grant.capability_scopes:\n            raise ValueError("attestation uses an unauthorized capability scope")\n        if self.created_at < grant.valid_from:\n            raise ValueError("attestation predates its authority grant")\n        if self.expires_at > grant.expires_at:\n            raise ValueError("attestation outlives its authority grant")\n        if current_time < self.created_at:\n''',
        marker="attestation outlives its authority grant",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''        current_time = _now(now)\n        if not self.authorized:\n''',
        '''        current_time = _now(now)\n        if current_time < self.created_at:\n            raise ValueError("governance decision is not active yet")\n        if not self.authorized:\n''',
        marker="governance decision is not active yet",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    for attestation in supplied:\n        try:\n''',
        '''    seen_attestation_ids: set[str] = set()\n    for attestation in supplied:\n        if attestation.attestation_id in seen_attestation_ids:\n            reasons.append(f"duplicate_attestation:{attestation.attestation_id}")\n            continue\n        seen_attestation_ids.add(attestation.attestation_id)\n        try:\n''',
        marker="seen_attestation_ids: set[str]",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    abstentions = [\n        item for item in valid if item.decision == AttestationDecision.ABSTAIN.value\n    ]\n\n    role_to_principals: dict[str, set[str]] = {}\n    for approval in approvals:\n''',
        '''    abstentions = [\n        item for item in valid if item.decision == AttestationDecision.ABSTAIN.value\n    ]\n\n    counted_approvals: list[ApprovalAttestation] = []\n    seen_principal_roles: set[tuple[str, str]] = set()\n    for approval in approvals:\n        principal_role = (approval.principal_id, approval.functional_role)\n        if principal_role in seen_principal_roles:\n            reasons.append(\n                "duplicate_principal_role_approval:"\n                f"{approval.principal_id}:{approval.functional_role}"\n            )\n            continue\n        seen_principal_roles.add(principal_role)\n        counted_approvals.append(approval)\n\n    role_to_principals: dict[str, set[str]] = {}\n    for approval in counted_approvals:\n''',
        marker="counted_approvals: list[ApprovalAttestation]",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        "    approval_principals = {item.principal_id for item in approvals}\n",
        "    approval_principals = {item.principal_id for item in counted_approvals}\n",
        marker="item.principal_id for item in counted_approvals",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        "        0, quorum_policy.minimum_approval_count - len(approvals)\n",
        "        0, quorum_policy.minimum_approval_count - len(counted_approvals)\n",
        marker="minimum_approval_count - len(counted_approvals)",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    valid_expiries = [item.expires_at for item in approvals]\n    for approval in approvals:\n''',
        '''    valid_expiries = [item.expires_at for item in counted_approvals]\n    for approval in counted_approvals:\n''',
        marker="item.expires_at for item in counted_approvals",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''        else:\n            if self.emergency_ttl_seconds != 0:\n                raise ValueError("non-emergency policy has an emergency TTL")\n\n    def validate_emergency_against''',
        '''        else:\n            if self.emergency_ttl_seconds != 0:\n                raise ValueError("non-emergency policy has an emergency TTL")\n            if self.emergency_allowed_policy_scopes:\n                raise ValueError("non-emergency policy has emergency policy scopes")\n            if self.emergency_allowed_capability_scopes:\n                raise ValueError("non-emergency policy has emergency capability scopes")\n            if self.mandatory_post_event_review:\n                raise ValueError("non-emergency policy requires emergency review")\n            if self.baseline_policy_id or self.baseline_policy_digest:\n                raise ValueError("non-emergency policy references an emergency baseline")\n\n    def validate_emergency_against''',
        marker="non-emergency policy has emergency policy scopes",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''        return cls(\n            checkpoint_id=stable_id("authority-checkpoint", payload),\n            **payload,\n        )\n\n\n@dataclass(frozen=True)\nclass ChainedAuthorityReceipt:''',
        '''        return cls(\n            checkpoint_id=stable_id("authority-checkpoint", payload),\n            **payload,\n        )\n\n    def validate_integrity(\n        self, *, verified_checkpoint_refs: Iterable[str]\n    ) -> None:\n        trusted = _trusted_set(\n            verified_checkpoint_refs, "verified_checkpoint_refs"\n        )\n        if self.externally_signed_checkpoint_ref not in trusted:\n            raise ValueError("checkpoint signature reference is not externally trusted")\n        if self.schema_version != SCHEMA_VERSION:\n            raise ValueError("unsupported checkpoint schema version")\n        if self.sequence_number < 0:\n            raise ValueError("checkpoint sequence_number must be non-negative")\n        payload = _canonical_payload(self, exclude=("checkpoint_id",))\n        if self.checkpoint_id != stable_id("authority-checkpoint", payload):\n            raise ValueError("checkpoint ID does not match its content")\n\n\n@dataclass(frozen=True)\nclass ChainedAuthorityReceipt:''',
        marker="checkpoint ID does not match its content",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    ledger_ids = {item.ledger_id for item in items}\n    ledger_id = next(iter(ledger_ids), "")\n    if len(ledger_ids) > 1:\n''',
        '''    ledger_ids = {item.ledger_id for item in items}\n    ledger_id = sorted(ledger_ids)[0] if ledger_ids else ""\n    if len(ledger_ids) > 1:\n''',
        marker="ledger_id = sorted(ledger_ids)[0] if ledger_ids else \"\"",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    if trusted_checkpoint is not None:\n        if (\n            trusted_checkpoint.externally_signed_checkpoint_ref\n            not in checkpoint_trusted\n        ):\n            errors.append("checkpoint_reference_not_externally_verified")\n        else:\n            checkpoint_verified = True\n        if ledger_id and trusted_checkpoint.ledger_id != ledger_id:\n''',
        '''    if trusted_checkpoint is not None:\n        try:\n            trusted_checkpoint.validate_integrity(\n                verified_checkpoint_refs=checkpoint_trusted\n            )\n        except (TypeError, ValueError) as exc:\n            errors.append(f"invalid_trusted_checkpoint:{exc}")\n        else:\n            checkpoint_verified = True\n            if not ledger_id:\n                ledger_id = trusted_checkpoint.ledger_id\n        if ledger_id and trusted_checkpoint.ledger_id != ledger_id:\n''',
        marker="invalid_trusted_checkpoint:",
    )
    replace_once_or_present(
        "aura_relational_authority.py",
        '''    final_sequence = items[-1].sequence_number if items else 0\n    final_digest = items[-1].chain_digest if items else GENESIS_CHAIN_DIGEST\n''',
        '''    final_sequence = (\n        items[-1].sequence_number\n        if items\n        else (\n            trusted_checkpoint.sequence_number\n            if trusted_checkpoint is not None and checkpoint_verified\n            else 0\n        )\n    )\n    final_digest = (\n        items[-1].chain_digest\n        if items\n        else (\n            trusted_checkpoint.chain_digest\n            if trusted_checkpoint is not None and checkpoint_verified\n            else GENESIS_CHAIN_DIGEST\n        )\n    )\n''',
        marker="trusted_checkpoint is not None and checkpoint_verified",
    )


def write_regression_tests() -> None:
    write(
        "tests/test_p1_1_adversarial_review.py",
        '''from __future__ import annotations\n\nfrom dataclasses import replace\n\nimport pytest\n\nfrom aura_event_contracts import sanitize_payload\nfrom aura_relational_authority import (\n    ApprovalAttestation,\n    AttestationDecision,\n    AuthorityGrant,\n    QuorumPolicy,\n    RiskClass,\n    TrustedCheckpoint,\n    evaluate_governance,\n    stable_digest,\n    stable_id,\n    verify_receipt_chain,\n)\nfrom aura_workflow_gates import WorkflowState, can_transition, evaluate_gate, get_gate\n\nNOW = 1_800_000_000.0\nACTION_ID = "review-action"\nACTION_DIGEST = stable_digest({"patch": "exact"})\nAUTH_REF = "authority:reviewer"\nATTEST_REFS = {"attestation:one", "attestation:two"}\nCHECKPOINT_REF = "checkpoint:signed"\n\n\ndef make_grant(*, policy_scope: str = "workflow.commit", capability_scope: str = "commit") -> AuthorityGrant:\n    return AuthorityGrant.create(\n        principal_id="reviewer",\n        authorized_functional_roles=("APPROVE",),\n        policy_scopes=(policy_scope,),\n        capability_scopes=(capability_scope,),\n        valid_from=NOW - 100,\n        expires_at=NOW + 1_000,\n        externally_verified_authority_ref=AUTH_REF,\n        verified_authority_refs={AUTH_REF},\n        now=NOW,\n    )\n\n\ndef make_attestation(\n    grant: AuthorityGrant,\n    *,\n    attestation_ref: str = "attestation:one",\n    created_at: float = NOW - 10,\n    policy_scope: str = "workflow.commit",\n    capability_scope: str = "commit",\n) -> ApprovalAttestation:\n    return ApprovalAttestation.create(\n        action_id=ACTION_ID,\n        action_payload_digest=ACTION_DIGEST,\n        principal_id=grant.principal_id,\n        grant=grant,\n        decision=AttestationDecision.APPROVE,\n        functional_role="APPROVE",\n        policy_scope=policy_scope,\n        capability_scope=capability_scope,\n        public_rationale="Exact evidence supports this bounded action.",\n        evidence_refs=("evidence:exact",),\n        externally_verified_attestation_ref=attestation_ref,\n        verified_authority_refs={AUTH_REF},\n        verified_attestation_refs=ATTEST_REFS,\n        created_at=created_at,\n        expires_at=NOW + 500,\n        now=NOW,\n    )\n\n\ndef make_decision(*, policy_scope: str = "workflow.commit", capability_scope: str = "commit"):\n    grant = make_grant(policy_scope=policy_scope, capability_scope=capability_scope)\n    approval = make_attestation(\n        grant, policy_scope=policy_scope, capability_scope=capability_scope\n    )\n    policy = QuorumPolicy.create(\n        risk_class=RiskClass.LOW,\n        minimum_approval_count=1,\n        required_functional_roles=("APPROVE",),\n        minimum_distinct_principals=1,\n    )\n    return evaluate_governance(\n        action_id=ACTION_ID,\n        action_payload_digest=ACTION_DIGEST,\n        policy_scope=policy_scope,\n        capability_scope=capability_scope,\n        grants=(grant,),\n        attestations=(approval,),\n        quorum_policy=policy,\n        verified_authority_refs={AUTH_REF},\n        verified_attestation_refs=ATTEST_REFS,\n        now=NOW,\n    )\n\n\ndef reidentify_policy(policy: QuorumPolicy) -> QuorumPolicy:\n    payload = policy.to_dict()\n    payload.pop("policy_id")\n    payload.pop("policy_digest")\n    return replace(\n        policy,\n        policy_id=stable_id("quorum-policy", payload),\n        policy_digest=stable_digest(payload),\n    )\n\n\n@pytest.mark.parametrize(\n    "field_name",\n    ("chain.of.thought", "model/chain-of-thought", "internal:scratchpad"),\n)\ndef test_private_reasoning_punctuation_aliases_are_rejected(field_name: str) -> None:\n    with pytest.raises(ValueError, match="private reasoning field"):\n        sanitize_payload({field_name: "must not persist"})\n\n\ndef test_private_reasoning_acronym_does_not_block_unrelated_words() -> None:\n    assert sanitize_payload({"mascot": "turtle"}) == {"mascot": "turtle"}\n\n\ndef test_punctuation_separated_secret_field_is_redacted() -> None:\n    assert sanitize_payload({"api.key": "secret-value"}) == {\n        "api.key": "[REDACTED]"\n    }\n\n\ndef test_commit_gate_scope_cannot_be_downgraded_by_evidence() -> None:\n    decision = make_decision(policy_scope="workflow.read", capability_scope="read")\n    result = evaluate_gate(\n        "HUMAN_APPROVED_FOR_COMMIT",\n        {\n            "verified": True,\n            "tests_pass": True,\n            "governance_decision": decision,\n            "verified_governance_decision_ids": (decision.decision_id,),\n            "requested_action_id": ACTION_ID,\n            "requested_action_digest": ACTION_DIGEST,\n            "required_policy_scope": "workflow.read",\n            "required_capability_scope": "read",\n            "authority_now": NOW,\n        },\n    )\n    assert result["can_proceed"] is False\n    assert result["required_policy_scope"] == "workflow.commit"\n    assert result["required_capability_scope"] == "commit"\n\n\ndef test_string_human_approval_does_not_pass_legacy_gate() -> None:\n    result = evaluate_gate(\n        "HUMAN_APPROVED_FOR_COMMIT",\n        {"human_approval": "false", "verified": True, "tests_pass": True},\n    )\n    assert result["can_proceed"] is False\n    assert result["legacy_human_approval_used"] is False\n\n\ndef test_verified_decision_ids_must_be_a_collection() -> None:\n    decision = make_decision()\n    result = evaluate_gate(\n        "HUMAN_APPROVED_FOR_COMMIT",\n        {\n            "verified": True,\n            "tests_pass": True,\n            "governance_decision": decision,\n            "verified_governance_decision_ids": decision.decision_id,\n            "requested_action_id": ACTION_ID,\n            "requested_action_digest": ACTION_DIGEST,\n            "authority_now": NOW,\n        },\n    )\n    assert result["can_proceed"] is False\n    assert any(\n        "must be a collection" in item\n        for item in result["authority_missing_reasons"]\n    )\n\n\ndef test_patch_transition_order_matches_the_state_machine() -> None:\n    assert can_transition(WorkflowState.AGENT_RUNNING, WorkflowState.PATCH_PROPOSED)\n    assert can_transition(WorkflowState.REPAIR_REQUIRED, WorkflowState.PATCH_PROPOSED)\n    assert not can_transition(WorkflowState.VERIFIED, WorkflowState.PATCH_PROPOSED)\n    assert "prior_state_agent_running_or_repair" in get_gate(\n        WorkflowState.PATCH_PROPOSED\n    ).required_evidence\n\n\ndef test_duplicate_attestation_cannot_inflate_quorum() -> None:\n    grant = make_grant()\n    approval = make_attestation(grant)\n    policy = QuorumPolicy.create(\n        risk_class=RiskClass.LOW,\n        minimum_approval_count=2,\n        required_functional_roles=("APPROVE",),\n        minimum_distinct_principals=1,\n    )\n    decision = evaluate_governance(\n        action_id=ACTION_ID,\n        action_payload_digest=ACTION_DIGEST,\n        policy_scope="workflow.commit",\n        capability_scope="commit",\n        grants=(grant,),\n        attestations=(approval, approval),\n        quorum_policy=policy,\n        verified_authority_refs={AUTH_REF},\n        verified_attestation_refs=ATTEST_REFS,\n        now=NOW,\n    )\n    assert decision.authorized is False\n    assert decision.missing_quorum_count == 1\n    assert any(\n        item.startswith("duplicate_attestation:")\n        for item in decision.authority_missing_reasons\n    )\n\n\ndef test_same_principal_role_cannot_submit_multiple_counted_approvals() -> None:\n    grant = make_grant()\n    first = make_attestation(\n        grant, attestation_ref="attestation:one", created_at=NOW - 10\n    )\n    second = make_attestation(\n        grant, attestation_ref="attestation:two", created_at=NOW - 9\n    )\n    policy = QuorumPolicy.create(\n        risk_class=RiskClass.LOW,\n        minimum_approval_count=2,\n        required_functional_roles=("APPROVE",),\n        minimum_distinct_principals=1,\n    )\n    decision = evaluate_governance(\n        action_id=ACTION_ID,\n        action_payload_digest=ACTION_DIGEST,\n        policy_scope="workflow.commit",\n        capability_scope="commit",\n        grants=(grant,),\n        attestations=(first, second),\n        quorum_policy=policy,\n        verified_authority_refs={AUTH_REF},\n        verified_attestation_refs=ATTEST_REFS,\n        now=NOW,\n    )\n    assert decision.authorized is False\n    assert decision.missing_quorum_count == 1\n    assert (\n        "duplicate_principal_role_approval:reviewer:APPROVE"\n        in decision.authority_missing_reasons\n    )\n\n\ndef test_attestation_cannot_be_backdated_before_grant() -> None:\n    with pytest.raises(ValueError, match="predate"):\n        make_attestation(make_grant(), created_at=NOW - 200)\n\n\ndef test_tampered_grant_is_rejected_before_attestation_creation() -> None:\n    tampered = replace(make_grant(), principal_id="fabricated")\n    with pytest.raises(ValueError, match="digest or ID"):\n        make_attestation(tampered)\n\n\ndef test_future_governance_decision_is_not_active() -> None:\n    future = replace(make_decision(), created_at=NOW + 100)\n    payload = future.to_dict()\n    payload.pop("decision_id")\n    payload.pop("decision_digest")\n    future = replace(\n        future,\n        decision_id=stable_id("governance-decision", payload),\n        decision_digest=stable_digest(payload),\n    )\n    with pytest.raises(ValueError, match="not active yet"):\n        future.validate_for_action(\n            action_id=ACTION_ID,\n            action_payload_digest=ACTION_DIGEST,\n            policy_scope="workflow.commit",\n            capability_scope="commit",\n            now=NOW,\n        )\n\n\ndef test_non_emergency_policy_rejects_emergency_only_fields() -> None:\n    policy = QuorumPolicy.create(\n        risk_class=RiskClass.LOW,\n        minimum_approval_count=1,\n        required_functional_roles=("APPROVE",),\n        minimum_distinct_principals=1,\n    )\n    tampered = reidentify_policy(\n        replace(policy, emergency_allowed_policy_scopes=("workflow.commit",))\n    )\n    with pytest.raises(ValueError, match="emergency policy scopes"):\n        tampered.validate()\n\n\ndef test_tampered_trusted_checkpoint_is_rejected() -> None:\n    checkpoint = TrustedCheckpoint.create(\n        ledger_id="ledger-1",\n        sequence_number=4,\n        chain_digest="chain-4",\n        externally_signed_checkpoint_ref=CHECKPOINT_REF,\n        verified_checkpoint_refs={CHECKPOINT_REF},\n        created_at=NOW,\n    )\n    result = verify_receipt_chain(\n        (),\n        trusted_checkpoint=replace(checkpoint, chain_digest="fabricated"),\n        verified_checkpoint_refs={CHECKPOINT_REF},\n    )\n    assert result.valid is False\n    assert any(\n        item.startswith("invalid_trusted_checkpoint:") for item in result.errors\n    )\n\n\ndef test_empty_suffix_is_anchored_to_trusted_checkpoint() -> None:\n    checkpoint = TrustedCheckpoint.create(\n        ledger_id="ledger-1",\n        sequence_number=4,\n        chain_digest="chain-4",\n        externally_signed_checkpoint_ref=CHECKPOINT_REF,\n        verified_checkpoint_refs={CHECKPOINT_REF},\n        created_at=NOW,\n    )\n    result = verify_receipt_chain(\n        (),\n        trusted_checkpoint=checkpoint,\n        verified_checkpoint_refs={CHECKPOINT_REF},\n    )\n    assert result.valid is True\n    assert result.checkpoint_verified is True\n    assert result.ledger_id == "ledger-1"\n    assert result.final_sequence_number == 4\n    assert result.final_chain_digest == "chain-4"\n''',
    )


def main() -> None:
    harden_event_contracts()
    harden_workflow_gates()
    harden_relational_authority()
    write_regression_tests()
    print("P1.1 adversarial review repairs applied")


if __name__ == "__main__":
    main()
