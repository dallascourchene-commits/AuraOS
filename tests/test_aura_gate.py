from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from aura_forge import AuraForgeRuntime
import aura_gate as gate_module
from aura_gate import (
    AuraGateRuntime,
    GateError,
    GateLeaseStore,
    GatePolicyManifest,
    GateRunRequest,
    gate_purpose_digest,
)
from aura_gate_audit import GateAuditError, GateAuditLedger
from aura_gate_oidc import VerifiedGateIdentity


class FakeBridge:
    def __init__(self) -> None:
        self.prepare_calls = 0

    def aura_repo_digest(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "codemap_status": "AURA_CODEMAP_ACTIVE",
            "file_count": 10,
            "symbol_count": 20,
            "topology_nodes": 30,
            "topology_edges": 40,
            "source_of_truth": ["CODEMAP.json", "exact source files", "tests"],
        }

    def aura_prepare_arena(self, **kwargs: Any) -> dict[str, Any]:
        self.prepare_calls += 1
        return {
            "ok": True,
            "plan_phase_hash": "phase-gate",
            "act_capsules": [
                {
                    "task_id": "A1",
                    "target_file": "pkg/router.py",
                    "target_symbol": "route_failure",
                    "related_files": ["pkg/state.py"],
                    "objective": kwargs["objective"],
                }
            ],
            "grounding_evidence": [{"task_id": "A1", "file_exists": True}],
            "routing_decisions": [{"task_id": "A1", "route": "BUILDER_PATCH"}],
            "builder_patch_authorized": True,
            "blockers": [],
            "warnings": [],
        }

    def aura_get_micro_context(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "task_id": "A1",
            "target_file": "pkg/router.py",
            "target_symbol": "route_failure",
            "line_ranges": [{"file": "pkg/router.py", "line_range": [1, 20]}],
            "dependencies": ["pkg/state.py"],
            "tests": ["tests/test_router.py"],
            "route_decision": {"route": "BUILDER_PATCH"},
            "compressed_context": "exact bounded context",
            "jspace_packet": "state",
            "st3gg_egress": {},
        }

    def aura_hotswap_status(self, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "hotswap_ready": True, "promotion_performed": False}


class FakeManager:
    def __init__(self) -> None:
        self.open_calls = 0
        self.submit_calls = 0
        self.status = "WAITING_FOR_MODEL"

    def open_prepared_session(self, **_kwargs: Any) -> dict[str, Any]:
        self.open_calls += 1
        return {
            "ok": True,
            "session_created": True,
            "session": {"session_id": "SESSION-1", "status": self.status},
            "turn": {
                "turn_id": "TURN-1",
                "allowed_files": ["pkg/router.py", "pkg/state.py"],
                "instruction": "Return only the bounded change for human verification.",
            },
            "control_profile": {"human_review_required": True, "production_mutation": False},
        }

    def submit_response(self, **_kwargs: Any) -> dict[str, Any]:
        self.submit_calls += 1
        self.status = "READY_FOR_HUMAN_REVIEW"
        return {
            "ok": True,
            "status": self.status,
            "session": {"session_id": "SESSION-1", "status": self.status},
            "verification": {"ok": True, "tests": {"passed": 3, "total": 3}},
            "hotswap_status": {"hotswap_ready": True, "promotion_performed": False},
        }

    def get_session(self, _session_id: str) -> dict[str, Any]:
        return {"ok": True, "session": {"session_id": "SESSION-1", "status": self.status}}


class FailingStartAudit:
    def __init__(self, delegate: GateAuditLedger) -> None:
        self.delegate = delegate

    def verify(self) -> dict[str, Any]:
        return self.delegate.verify()

    def record(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs["action"] == "FORGE_START":
            raise GateAuditError("forced_audit_failure", "forced audit failure")
        return self.delegate.record(**kwargs)

    def require_authority_issuance(self, **kwargs: Any) -> dict[str, Any]:
        return self.delegate.require_authority_issuance(**kwargs)

    def export_siem(self, output_path: str | Path) -> dict[str, Any]:
        return self.delegate.export_siem(output_path)


def identity(*, actor_ref: str = "ACTOR-1", expires_at: float = 2000.0) -> VerifiedGateIdentity:
    return VerifiedGateIdentity(
        actor_ref=actor_ref,
        issuer="https://issuer.example",
        audiences=("aura-gate",),
        authorized_party=None,
        roles=("aura-gate-developer", "aura-gate-auditor"),
        groups=("engineering",),
        issued_at=900.0,
        expires_at=expires_at,
        not_before=900.0,
        verified_at=1000.0,
        key_id="key-1",
        token_digest="sha256:" + "1" * 64,
        claims_digest="sha256:" + "2" * 64,
        jwks_digest="sha256:" + "3" * 64,
    )


def policy(objective: str) -> GatePolicyManifest:
    return GatePolicyManifest.create(
        name="test-private-gate",
        allowed_purpose_digests=[gate_purpose_digest(objective)],
        allowed_capabilities=[
            "FORGE_START",
            "FORGE_SUBMIT",
            "FORGE_STATUS",
            "FORGE_REVOKE",
            "PROPOSE.PATCH",
            "READ.REPOSITORY",
            "RUN.TESTS",
        ],
        allowed_files=["pkg/router.py", "pkg/state.py", "tests/test_router.py"],
        allowed_destinations=["https://provider.example"],
        allowed_providers=["test-provider"],
        allowed_models=["test-model"],
        allowed_data_classes=["BOUNDED_SOURCE_CONTEXT"],
        allowed_egress_fields=["turn_id", "allowed_files", "instruction"],
        allowed_retention_classes=["TRANSIENT"],
        allowed_protocols=["NATIVE", "MCP", "A2A"],
        required_verifiers=["canonical_arena_verifier", "hotswap_readiness"],
        required_roles=["aura-gate-developer"],
        required_groups=["engineering"],
        max_lease_ttl_seconds=500.0,
        max_payload_bytes=20_000,
        max_token_estimate=4000,
        max_context_tokens=2200,
        max_output_tokens=2400,
        max_turns=12,
        max_local_repairs=2,
        max_provider_calls=4,
    )


def request(policy_: GatePolicyManifest, objective: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "policy_id": policy_.policy_id,
        "purpose_digest": gate_purpose_digest(objective),
        "objective": objective,
        "target_file": "pkg/router.py",
        "target_symbol": "route_failure",
        "acceptance_criteria": ["tests pass", "human review packet is complete"],
        "risk_map": ["scope drift"],
        "constraints": [],
        "capabilities": [
            "FORGE_START",
            "FORGE_SUBMIT",
            "FORGE_STATUS",
            "FORGE_REVOKE",
            "PROPOSE.PATCH",
            "READ.REPOSITORY",
            "RUN.TESTS",
        ],
        "destination": "https://provider.example",
        "provider": "test-provider",
        "model": "test-model",
        "data_classes": ["BOUNDED_SOURCE_CONTEXT"],
        "retention_class": "TRANSIENT",
        "egress_fields": ["turn_id", "allowed_files", "instruction"],
        "protocol": "NATIVE",
        "lease_ttl_seconds": 300.0,
        "nonce": "request-nonce-1",
        "council_mode": "SELECTIVE_V3",
        "max_context_tokens": 2200,
        "max_output_tokens": 2400,
        "max_turns": 12,
        "max_local_repairs": 2,
        "max_provider_calls": 4,
    }
    value.update(overrides)
    return value


def build_runtime(tmp_path: Path) -> tuple[AuraGateRuntime, FakeBridge, FakeManager, list[float]]:
    objective = "Refactor exact failure routing without changing public behavior"
    policy_ = policy(objective)
    codemap = tmp_path / ".aura" / "CODEMAP.json"
    codemap.parent.mkdir(parents=True, exist_ok=True)
    codemap.write_text('{"version": 1}', encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("b" * 40, encoding="ascii")
    bridge = FakeBridge()
    manager = FakeManager()
    forge = AuraForgeRuntime(
        tmp_path,
        bridge=bridge,
        session_manager_factory=lambda _request, _bridge, _root: manager,
    )
    now = [1000.0]
    audit = GateAuditLedger(tmp_path / "audit", clock=lambda: now[0])
    runtime = AuraGateRuntime(
        forge=forge,
        policies=[policy_],
        lease_store=GateLeaseStore(tmp_path / "state" / "leases.sqlite3"),
        audit=audit,
        clock=lambda: now[0],
    )
    return runtime, bridge, manager, now


def prepare(runtime: AuraGateRuntime) -> dict[str, Any]:
    policy_ = next(iter(runtime.policies.values()))
    return runtime.prepare(
        identity(),
        request(
            policy_,
            "Refactor exact failure routing without changing public behavior",
        ),
    )


def test_policy_round_trip_and_strict_contract() -> None:
    policy_ = policy("one exact objective")

    restored = GatePolicyManifest.from_mapping(policy_.to_dict())

    assert restored == policy_
    malformed = policy_.to_dict()
    malformed["production_mutation"] = "false"
    with pytest.raises(GateError, match="invalid_production_mutation"):
        GatePolicyManifest.from_mapping(malformed)


def test_request_binds_exact_objective_and_rejects_unknown_fields() -> None:
    objective = "one exact objective"
    policy_ = policy(objective)
    valid = request(policy_, objective)

    assert GateRunRequest.from_mapping(valid).purpose_digest == gate_purpose_digest(objective)
    invalid = dict(valid, purpose_digest=gate_purpose_digest("another objective"))
    with pytest.raises(GateError, match="purpose_objective_mismatch"):
        GateRunRequest.from_mapping(invalid)
    invalid = dict(valid, actor_ref="spoofed")
    with pytest.raises(GateError, match="invalid_gate_request_fields"):
        GateRunRequest.from_mapping(invalid)


def test_prepare_issues_durable_exact_authority(tmp_path: Path) -> None:
    runtime, bridge, _manager, _now = build_runtime(tmp_path)

    result = prepare(runtime)

    assert result["ok"] is True
    assert result["status"] == "ACTIVE"
    envelope, status = runtime.lease_store.get(result["gate_run_id"])
    assert status == "ACTIVE"
    assert envelope.forge_contract_digest == result["forge_contract_digest"]
    assert envelope.allowed_files == (
        "pkg/router.py",
        "pkg/state.py",
        "tests/test_router.py",
    )
    assert envelope.arena_lease["holder"] == identity().actor_ref
    assert bridge.prepare_calls == 1
    assert runtime.audit.verify()["event_count"] == 1

    reopened = GateLeaseStore(tmp_path / "state" / "leases.sqlite3")
    assert reopened.get(result["gate_run_id"])[0] == envelope


def test_prepare_nonce_is_single_use_before_forge_or_audit(tmp_path: Path) -> None:
    runtime, bridge, _manager, _now = build_runtime(tmp_path)

    first = prepare(runtime)
    replay = prepare(runtime)

    assert first["ok"] is True
    assert replay["ok"] is False
    assert replay["error"] == "lease_nonce_replay"
    assert replay["stage"] == "PREPARE"
    assert bridge.prepare_calls == 1
    assert runtime.audit.verify()["event_count"] == 1


def test_incomplete_capability_bundle_is_denied_before_forge(tmp_path: Path) -> None:
    runtime, bridge, _manager, _now = build_runtime(tmp_path)
    policy_ = next(iter(runtime.policies.values()))

    denied = runtime.prepare(
        identity(),
        request(
            policy_,
            "Refactor exact failure routing without changing public behavior",
            capabilities=[
                "FORGE_START",
                "FORGE_SUBMIT",
                "FORGE_STATUS",
                "FORGE_REVOKE",
            ],
        ),
    )

    assert denied["ok"] is False
    assert denied["error"] == "capability_bundle_incomplete"
    assert bridge.prepare_calls == 0
    assert runtime.audit.verify()["event_count"] == 0


def test_sensitive_egress_fields_require_bounded_context_class(tmp_path: Path) -> None:
    runtime, bridge, _manager, _now = build_runtime(tmp_path)
    base = next(iter(runtime.policies.values()))
    values = base.to_dict()
    create_fields = {
        key: value
        for key, value in values.items()
        if key
        not in {
            "policy_id",
            "private_only",
            "human_review_required",
            "production_mutation",
            "automatic_promotion",
            "version",
        }
    }
    create_fields["allowed_data_classes"] = [
        "BOUNDED_SOURCE_CONTEXT",
        "OBJECTIVE",
    ]
    create_fields["allowed_egress_fields"] = ["source_slices"]
    strict_policy = GatePolicyManifest.create(**create_fields)
    runtime.policies = {strict_policy.policy_id: strict_policy}

    denied = runtime.prepare(
        identity(),
        request(
            strict_policy,
            "Refactor exact failure routing without changing public behavior",
            data_classes=["OBJECTIVE"],
            egress_fields=["source_slices"],
        ),
    )

    assert denied["ok"] is False
    assert denied["error"] == "egress_data_class_binding_missing"
    assert bridge.prepare_calls == 0


def test_lease_row_cannot_be_rebound_to_another_valid_envelope(tmp_path: Path) -> None:
    runtime, _bridge, _manager, _now = build_runtime(tmp_path)
    first = prepare(runtime)
    policy_ = next(iter(runtime.policies.values()))
    second = runtime.prepare(
        identity(),
        request(
            policy_,
            "Refactor exact failure routing without changing public behavior",
            nonce="request-nonce-2",
        ),
    )
    database = tmp_path / "state" / "leases.sqlite3"
    with sqlite3.connect(database) as connection:
        donor = connection.execute(
            "SELECT envelope_json, envelope_digest FROM gate_leases WHERE gate_run_id = ?",
            (second["gate_run_id"],),
        ).fetchone()
        assert donor is not None
        connection.execute(
            "UPDATE gate_leases SET envelope_json = ?, envelope_digest = ? WHERE gate_run_id = ?",
            (donor[0], donor[1], first["gate_run_id"]),
        )

    with pytest.raises(GateError, match="lease_store_integrity"):
        runtime.lease_store.get(first["gate_run_id"])


def test_internally_consistent_fabricated_lease_has_no_audit_authority(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    envelope, _status = runtime.lease_store.get(prepared["gate_run_id"])
    forged = envelope.to_dict()
    forged["nonce"] = "fabricated-operational-state"
    basis = dict(forged)
    basis.pop("authority_id")
    basis.pop("gate_run_id")
    forged["authority_id"] = gate_module._authority_id(basis)
    forged["gate_run_id"] = f"GATE-{forged['authority_id'].removeprefix('GATE-AUTH-sha256:')[:24]}"
    encoded = gate_module._canonical_json(forged)
    digest = gate_module._sha256(forged)
    database = tmp_path / "state" / "leases.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE gate_leases SET gate_run_id = ?, authority_id = ?, "
            "envelope_json = ?, envelope_digest = ? WHERE gate_run_id = ?",
            (
                forged["gate_run_id"],
                forged["authority_id"],
                encoded,
                digest,
                prepared["gate_run_id"],
            ),
        )

    denied = runtime.start(identity(), forged["gate_run_id"])

    assert denied["ok"] is False
    assert denied["error"] == "AURA_GATE_AUDIT_AUTHORITY_BINDING"
    assert manager.open_calls == 0


def test_start_uses_retained_forge_run_and_governs_exact_egress(tmp_path: Path) -> None:
    runtime, bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)

    started = runtime.start(identity(), prepared["gate_run_id"])

    assert started["ok"] is True
    assert started["status"] == "STARTED"
    assert started["turn"]["turn_id"] == "TURN-1"
    assert started["egress_capsule"]["production_promotion_authority"] is False
    assert started["egress_capsule"]["source_mutation_performed"] is False
    assert bridge.prepare_calls == 1
    assert manager.open_calls == 1
    assert runtime.status(identity(), prepared["gate_run_id"])["status"] == "STARTED"

    repeated = runtime.start(identity(), prepared["gate_run_id"])
    assert repeated["ok"] is False
    assert repeated["error"] == "invalid_lease_state"
    assert manager.open_calls == 1


def test_actor_mismatch_fails_before_forge_start(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)

    denied = runtime.start(identity(actor_ref="ACTOR-2"), prepared["gate_run_id"])

    assert denied["ok"] is False
    assert denied["error"] == "actor_mismatch"
    assert manager.open_calls == 0
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "ACTIVE"


def test_audit_failure_denies_before_forge_start(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    runtime.audit = FailingStartAudit(runtime.audit)  # type: ignore[assignment]

    denied = runtime.start(identity(), prepared["gate_run_id"])

    assert denied["ok"] is False
    assert denied["error"] == "forced_audit_failure"
    assert manager.open_calls == 0
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "ACTIVE"


def test_expiry_is_audited_and_durable(tmp_path: Path) -> None:
    runtime, _bridge, manager, now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    now[0] = 1300.0

    denied = runtime.start(identity(expires_at=2000.0), prepared["gate_run_id"])

    assert denied["ok"] is False
    assert denied["error"] == "lease_expired"
    assert manager.open_calls == 0
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "EXPIRED"
    assert runtime.audit.verify()["event_count"] == 2


def test_revoke_is_one_way_and_blocks_execution(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)

    revoked = runtime.revoke(identity(), prepared["gate_run_id"], reason_code="USER_CANCELLED")

    assert revoked["ok"] is True
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "REVOKED"
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is False
    assert manager.open_calls == 0
    observed = runtime.status(identity(), prepared["gate_run_id"])
    assert observed["ok"] is True
    assert observed["status"] == "REVOKED"
    assert observed["forge_status"] is None


def test_restart_revokes_nonterminal_lease_when_forge_state_is_lost(
    tmp_path: Path,
) -> None:
    runtime, bridge, _manager, now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    policy_ = next(iter(runtime.policies.values()))
    fresh_manager = FakeManager()
    fresh_forge = AuraForgeRuntime(
        tmp_path,
        bridge=bridge,
        session_manager_factory=lambda _request, _bridge, _root: fresh_manager,
    )
    restarted = AuraGateRuntime(
        forge=fresh_forge,
        policies=[policy_],
        lease_store=GateLeaseStore(tmp_path / "state" / "leases.sqlite3"),
        audit=GateAuditLedger(tmp_path / "audit", clock=lambda: now[0]),
        clock=lambda: now[0],
    )

    observed = restarted.status(identity(), prepared["gate_run_id"])

    assert observed["ok"] is False
    assert observed["error"] == "forge_state_unavailable"
    assert restarted.lease_store.get(prepared["gate_run_id"])[1] == "REVOKED"
    assert fresh_manager.open_calls == 0


def test_submit_dissolves_at_human_review_without_promotion(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is True

    submitted = runtime.submit(
        identity(),
        prepared["gate_run_id"],
        turn_id="TURN-1",
        response="bounded worker response",
        provider_usage={"input_tokens": 20, "output_tokens": 8},
    )

    assert submitted["ok"] is True
    assert submitted["status"] == "DISSOLVED"
    assert submitted["automatic_promotion"] is False
    assert submitted["human_review_required"] is True
    assert manager.submit_calls == 1
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "DISSOLVED"
    assert runtime.status(identity(), prepared["gate_run_id"])["status"] == "DISSOLVED"


def test_submit_output_budget_is_enforced_before_forge(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is True

    denied = runtime.submit(
        identity(),
        prepared["gate_run_id"],
        turn_id="TURN-1",
        response="x" * (2400 * 4 + 1),
    )

    assert denied["ok"] is False
    assert denied["error"] == "output_budget_exceeded"
    assert manager.submit_calls == 0


@pytest.mark.parametrize(
    ("usage", "error"),
    [
        ({"input_tokens": 4001}, "provider_input_usage_exceeded"),
        ({"output_tokens": 2401}, "provider_output_usage_exceeded"),
        (
            {"input_tokens": 20, "output_tokens": 8, "total_tokens": 29},
            "provider_total_usage_inconsistent",
        ),
    ],
)
def test_reported_provider_usage_must_fit_authority_budget(
    tmp_path: Path,
    usage: dict[str, int],
    error: str,
) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is True

    denied = runtime.submit(
        identity(),
        prepared["gate_run_id"],
        turn_id="TURN-1",
        response="bounded worker response",
        provider_usage=usage,
    )

    assert denied["ok"] is False
    assert denied["error"] == error
    assert manager.submit_calls == 0
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "REVOKED"


def test_provider_call_budget_is_consumed_before_next_turn_release(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    policy_ = next(iter(runtime.policies.values()))
    prepared = runtime.prepare(
        identity(),
        request(
            policy_,
            "Refactor exact failure routing without changing public behavior",
            max_provider_calls=1,
        ),
    )
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is True
    assert runtime.lease_store.provider_call_usage(prepared["gate_run_id"]) == 1

    def submit_with_next_turn(**_kwargs: Any) -> dict[str, Any]:
        manager.submit_calls += 1
        return {
            "ok": True,
            "status": "WAITING_FOR_MODEL",
            "session": {"session_id": "SESSION-1", "status": "WAITING_FOR_MODEL"},
            "turn": {
                "turn_id": "TURN-2",
                "allowed_files": ["pkg/router.py", "pkg/state.py"],
                "instruction": "Return the next bounded response.",
            },
        }

    manager.submit_response = submit_with_next_turn  # type: ignore[method-assign]
    denied = runtime.submit(
        identity(),
        prepared["gate_run_id"],
        turn_id="TURN-1",
        response="bounded worker response",
    )

    assert denied["ok"] is False
    assert denied["error"] == "provider_call_budget_exceeded"
    assert runtime.lease_store.provider_call_usage(prepared["gate_run_id"]) == 1
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "REVOKED"
    assert manager.submit_calls == 1
    export_path = runtime.audit.export_root / "budget-events.jsonl"
    runtime.audit.export_siem(export_path)
    events = [json.loads(line) for line in export_path.read_text(encoding="utf-8").splitlines()]
    assert sum(event["action"] == "EGRESS_RELEASE" for event in events) == 1


def test_provider_call_consumption_is_content_idempotent(tmp_path: Path) -> None:
    runtime, _bridge, _manager, now = build_runtime(tmp_path)
    prepared = prepare(runtime)
    assert runtime.start(identity(), prepared["gate_run_id"])["ok"] is True

    first = runtime.lease_store.consume_provider_call(
        prepared["gate_run_id"],
        max_provider_calls=4,
        operation_id="EGRESS-test-idempotency",
        now=now[0],
    )
    repeated = runtime.lease_store.consume_provider_call(
        prepared["gate_run_id"],
        max_provider_calls=4,
        operation_id="EGRESS-test-idempotency",
        now=now[0],
    )

    assert first == repeated == 2
    assert runtime.lease_store.provider_call_usage(prepared["gate_run_id"]) == 2


def test_egress_mismatch_revokes_started_session(tmp_path: Path) -> None:
    runtime, _bridge, manager, _now = build_runtime(tmp_path)
    policy_ = next(iter(runtime.policies.values()))
    bad_request = request(
        policy_,
        "Refactor exact failure routing without changing public behavior",
        egress_fields=["turn_id"],
    )
    prepared = runtime.prepare(identity(), bad_request)

    denied = runtime.start(identity(), prepared["gate_run_id"])

    assert denied["ok"] is False
    assert denied["error"] == "unauthorized_payload_field"
    assert manager.open_calls == 1
    assert runtime.lease_store.get(prepared["gate_run_id"])[1] == "REVOKED"


def test_siem_export_requires_auditor_role(tmp_path: Path) -> None:
    runtime, _bridge, _manager, _now = build_runtime(tmp_path)
    prepare(runtime)
    no_auditor = identity()
    object.__setattr__(no_auditor, "roles", ("aura-gate-developer",))

    denied = runtime.export_siem(no_auditor, runtime.audit.export_root / "denied.jsonl")
    allowed = runtime.export_siem(identity(), runtime.audit.export_root / "gate.jsonl")

    assert denied["ok"] is False
    assert denied["error"] == "audit_role_required"
    assert allowed["ok"] is True
    assert allowed["event_count"] == 1
    assert (runtime.audit.export_root / "gate.jsonl").is_file()
