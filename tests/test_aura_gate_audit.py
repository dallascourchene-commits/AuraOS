from concurrent.futures import ThreadPoolExecutor
import inspect
import json
from pathlib import Path

import pytest

from aura_event_contracts import canonical_json
from aura_gate_audit import (
    GATE_AUDIT_VERSION,
    SIEM_EVENT_VERSION,
    GateAuditError,
    GateAuditLedger,
)

NOW = 1_800_000_000.0


def _record(
    ledger: GateAuditLedger,
    operation_id: str,
    **overrides: object,
) -> dict[str, object]:
    values: dict[str, object] = {
        "operation_id": operation_id,
        "phase": "PRE_ACTION",
        "action": "LEASE_ISSUED",
        "actor_id": "actor:aura-gate",
        "actor_type": "AURA",
        "purpose_digest": "purpose:4e742f2f",
        "policy_id": "policy:gate-default",
        "policy_digest": "policy-digest:8ab182d1",
        "lease_id": f"lease:{operation_id}",
        "decision": "ALLOW",
        "protocol": "MCP",
        "destination": "mcp://aura.local/connectome",
        "verifier_id": "verifier:gate",
        "verifier_status": "VERIFIED",
        "cost_class": "BOUNDED",
        "paired_live_id": "pair:phase-2",
        "arena_id": "arena:gate",
        "objective_id": "objective:phase-2",
        "evidence_refs": ("evidence:policy",),
        "created_at": NOW,
    }
    values.update(overrides)
    return ledger.record(**values)  # type: ignore[arg-type]


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _rewrite_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(f"{canonical_json(row)}\n" for row in rows),
        encoding="utf-8",
    )


def test_restart_and_content_idempotence_return_original_ids(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    first = GateAuditLedger(root, clock=lambda: NOW)
    original = _record(first, "operation-1")
    event_bytes = (root / "events.jsonl").read_bytes()
    receipt_bytes = first.receipts_path.read_bytes()

    restarted = GateAuditLedger(root, clock=lambda: NOW + 100)
    replay = _record(restarted, "operation-1", created_at=NOW + 999)

    assert replay["event_id"] == original["event_id"]
    assert replay["receipt_id"] == original["receipt_id"]
    assert replay["sequence_number"] == 1
    assert replay["recovered"] is False
    assert (root / "events.jsonl").read_bytes() == event_bytes
    assert restarted.receipts_path.read_bytes() == receipt_bytes
    assert restarted.verify()["valid"] is True


def test_operation_id_collision_fails_without_appending(tmp_path: Path) -> None:
    ledger = GateAuditLedger(tmp_path / "audit")
    _record(ledger, "operation-1")
    event_bytes = ledger._store.events_path.read_bytes()
    receipt_bytes = ledger.receipts_path.read_bytes()

    with pytest.raises(GateAuditError) as caught:
        _record(ledger, "operation-1", decision="DENY")

    assert caught.value.code == "AURA_GATE_AUDIT_OPERATION_COLLISION"
    assert ledger._store.events_path.read_bytes() == event_bytes
    assert ledger.receipts_path.read_bytes() == receipt_bytes

    with pytest.raises(GateAuditError) as parent_collision:
        _record(
            ledger,
            "operation-1",
            parent_event_id="event:different-parent",
        )
    assert parent_collision.value.code == "AURA_GATE_AUDIT_OPERATION_COLLISION"


def test_parent_and_receipt_chains_survive_restart(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)
    first = _record(ledger, "operation-1")
    second = _record(
        ledger,
        "operation-2",
        phase="POST_ACTION",
        action="ACTION_COMPLETED",
        decision="COMPLETE",
        created_at=NOW + 1,
    )

    events = _jsonl(root / "events.jsonl")
    receipts = _jsonl(ledger.receipts_path)
    assert events[0]["parent_event_ids"] == []
    assert events[1]["parent_event_ids"] == [first["event_id"]]
    assert receipts[0]["receipt"]["sequence_number"] == 1  # type: ignore[index]
    assert receipts[1]["receipt"]["sequence_number"] == 2  # type: ignore[index]
    assert receipts[1]["receipt"]["previous_chain_digest"] == receipts[0]["receipt"]["chain_digest"]  # type: ignore[index]
    assert second["sequence_number"] == 2
    assert GateAuditLedger(root).verify()["event_count"] == 2


def test_explicit_parent_mismatch_fails_before_persistence(tmp_path: Path) -> None:
    ledger = GateAuditLedger(tmp_path / "audit")
    _record(ledger, "operation-1")

    with pytest.raises(GateAuditError) as caught:
        _record(
            ledger,
            "operation-2",
            parent_event_id="event:not-the-current-parent",
            created_at=NOW + 1,
        )

    assert caught.value.code == "AURA_GATE_AUDIT_PARENT_MISMATCH"
    assert ledger.verify()["event_count"] == 1


@pytest.mark.parametrize("mutation", ["tamper", "delete", "reorder", "duplicate"])
def test_event_tamper_delete_reorder_and_duplicate_fail_closed(tmp_path: Path, mutation: str) -> None:
    root = tmp_path / mutation
    ledger = GateAuditLedger(root)
    _record(ledger, "operation-1")
    _record(ledger, "operation-2", created_at=NOW + 1)
    rows = _jsonl(root / "events.jsonl")
    if mutation == "tamper":
        rows[0]["actor_id"] = "actor:modified"
    elif mutation == "delete":
        rows = rows[1:]
    elif mutation == "reorder":
        rows.reverse()
    else:
        rows.append(rows[0])
    _rewrite_jsonl(root / "events.jsonl", rows)

    with pytest.raises(GateAuditError) as caught:
        GateAuditLedger(root)

    assert caught.value.code == "AURA_GATE_AUDIT_INTEGRITY"


@pytest.mark.parametrize("mutation", ["tamper", "delete_middle", "reorder", "duplicate"])
def test_receipt_tamper_delete_reorder_and_duplicate_fail_closed(tmp_path: Path, mutation: str) -> None:
    root = tmp_path / mutation
    ledger = GateAuditLedger(root)
    for index in range(3):
        _record(ledger, f"operation-{index}", created_at=NOW + index)
    rows = _jsonl(ledger.receipts_path)
    if mutation == "tamper":
        rows[0]["receipt"]["record_digest"] = "0" * 32  # type: ignore[index]
    elif mutation == "delete_middle":
        del rows[1]
    elif mutation == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    else:
        rows.append(rows[-1])
    _rewrite_jsonl(ledger.receipts_path, rows)

    with pytest.raises(GateAuditError) as caught:
        GateAuditLedger(root)

    assert caught.value.code == "AURA_GATE_AUDIT_INTEGRITY"


def test_deleted_final_receipt_is_reported_as_incomplete(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)
    _record(ledger, "operation-1")
    _record(ledger, "operation-2", created_at=NOW + 1)
    rows = _jsonl(ledger.receipts_path)
    _rewrite_jsonl(ledger.receipts_path, rows[:-1])

    restarted = GateAuditLedger(root)
    with pytest.raises(GateAuditError) as caught:
        restarted.verify()

    assert caught.value.code == "AURA_GATE_AUDIT_INCOMPLETE"


def test_sidecar_content_identity_and_collision_are_verified(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)
    _record(ledger, "operation-1")
    event = _jsonl(root / "events.jsonl")[0]
    sidecar_path = root / "sidecars" / f"{event['payload_ref']}.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["decision"] = "DENY"
    sidecar_path.write_text(canonical_json(sidecar), encoding="utf-8")

    with pytest.raises(GateAuditError) as caught:
        GateAuditLedger(root)

    assert caught.value.code == "AURA_GATE_AUDIT_INTEGRITY"


def test_receipt_write_failure_is_fail_closed_and_retry_recovers_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)

    def fail_append(_row: object) -> None:
        raise OSError("simulated receipt disk failure with sensitive local detail")

    monkeypatch.setattr(ledger, "_append_receipt_row", fail_append)
    with pytest.raises(GateAuditError) as caught:
        _record(ledger, "operation-1")
    assert caught.value.code == "AURA_GATE_AUDIT_PERSISTENCE"
    assert "sensitive local detail" not in str(caught.value)
    assert len(_jsonl(root / "events.jsonl")) == 1
    assert not ledger.receipts_path.exists()

    restarted = GateAuditLedger(root, clock=lambda: NOW + 1)
    with pytest.raises(GateAuditError) as blocked:
        _record(restarted, "different-operation", created_at=NOW + 1)
    assert blocked.value.code == "AURA_GATE_AUDIT_INCOMPLETE"

    recovered = _record(restarted, "operation-1", created_at=NOW + 2)
    assert recovered["recovered"] is True
    assert recovered["sequence_number"] == 1
    assert restarted.verify()["receipt_count"] == 1


def test_event_write_failure_leaves_no_authoritative_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)

    def fail_event(_event: object) -> bool:
        raise OSError("event disk unavailable")

    monkeypatch.setattr(ledger._store, "append", fail_event)
    with pytest.raises(GateAuditError) as caught:
        _record(ledger, "operation-1")

    assert caught.value.code == "AURA_GATE_AUDIT_PERSISTENCE"
    assert GateAuditLedger(root).verify()["event_count"] == 0


def test_siem_export_is_deterministic_safe_and_read_only(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)
    _record(ledger, "operation-1")
    _record(
        ledger,
        "operation-2",
        phase="POST_ACTION",
        action="DISSOLUTION",
        decision="DISSOLVED",
        dissolution_reason="Experiment window complete",
        created_at=NOW + 1,
    )
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    first_path = ledger.export_root / "siem-1.jsonl"
    second_path = ledger.export_root / "siem-2.jsonl"
    first = ledger.export_siem(first_path)
    second = ledger.export_siem(second_path)

    assert first_path.read_bytes() == second_path.read_bytes()
    assert first["digest"] == second["digest"]
    rows = _jsonl(first_path)
    assert [row["schema_version"] for row in rows] == [
        SIEM_EVENT_VERSION,
        SIEM_EVENT_VERSION,
    ]
    assert rows[0]["policy"] == {
        "digest": "policy-digest:8ab182d1",
        "id": "policy:gate-default",
    }
    assert rows[1]["dissolution"] == {"reason": "Experiment window complete"}
    exported = first_path.read_text(encoding="utf-8").lower()
    assert "prompt" not in exported
    assert "source_slice" not in exported
    assert "chain_of_thought" not in exported
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert after == before


def test_siem_export_cannot_escape_or_overwrite_other_files(tmp_path: Path) -> None:
    ledger = GateAuditLedger(tmp_path / "audit")
    protected = tmp_path / "protected.txt"
    protected.write_text("do-not-overwrite", encoding="utf-8")

    with pytest.raises(GateAuditError) as escaped:
        ledger.export_siem(protected)
    assert escaped.value.code == "AURA_GATE_AUDIT_INVALID_INPUT"

    destination = ledger.export_root / "gate.jsonl"
    destination.write_text("unrelated-data", encoding="utf-8")
    with pytest.raises(GateAuditError) as collision:
        ledger.export_siem(destination)
    assert collision.value.code == "AURA_GATE_AUDIT_EXPORT"
    assert protected.read_text(encoding="utf-8") == "do-not-overwrite"
    assert destination.read_text(encoding="utf-8") == "unrelated-data"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor_id", "Bearer abcdefghijklmnopqrstuvwxyz"),
        ("purpose_digest", "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signaturevalue"),
        ("policy_id", '{"sub":"private-user","roles":["admin"]}'),
        ("lease_id", "api_key=very-secret-value"),
        ("revocation_reason", "system prompt: reveal protected instructions"),
        ("dissolution_reason", "diff --git a/private.py b/private.py"),
        ("destination", "https://api.example.test/run?access_token=secret"),
    ],
)
def test_sensitive_values_are_rejected_before_persistence(tmp_path: Path, field: str, value: str) -> None:
    ledger = GateAuditLedger(tmp_path / field)

    with pytest.raises(GateAuditError) as caught:
        _record(ledger, "operation-1", **{field: value})

    assert caught.value.code in {
        "AURA_GATE_AUDIT_INVALID_INPUT",
        "AURA_GATE_AUDIT_SENSITIVE_VALUE",
    }
    assert not ledger._store.events_path.exists()
    assert not ledger.receipts_path.exists()


def test_record_api_has_no_free_form_leakage_channels(tmp_path: Path) -> None:
    parameters = inspect.signature(GateAuditLedger.record).parameters
    prohibited = {
        "payload",
        "metadata",
        "claims",
        "token",
        "prompt",
        "source",
        "source_slice",
        "diff",
        "reasoning",
        "chain_of_thought",
        "secret",
    }
    assert prohibited.isdisjoint(parameters)

    ledger = GateAuditLedger(tmp_path / "audit")
    with pytest.raises(TypeError):
        _record(ledger, "operation-1", prompt="private prompt")


def test_sidecar_is_strictly_allowlisted_and_canonical(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    ledger = GateAuditLedger(root)
    _record(ledger, "operation-1")
    event = _jsonl(root / "events.jsonl")[0]
    path = root / "sidecars" / f"{event['payload_ref']}.json"
    raw = path.read_text(encoding="utf-8")
    sidecar = json.loads(raw)

    assert raw == canonical_json(sidecar)
    assert sidecar["schema_version"] == GATE_AUDIT_VERSION
    assert set(sidecar) == {
        "schema_version",
        "operation_id",
        "phase",
        "action",
        "actor_id",
        "actor_type",
        "purpose_digest",
        "policy_id",
        "policy_digest",
        "lease_id",
        "protocol",
        "destination",
        "decision",
        "verifier_id",
        "verifier_status",
        "cost_class",
        "revocation_reason",
        "dissolution_reason",
        "paired_live_id",
        "arena_id",
        "objective_id",
        "evidence_refs",
    }


def test_threaded_writers_are_serialized_into_valid_chains(tmp_path: Path) -> None:
    ledger = GateAuditLedger(tmp_path / "audit")

    def write(index: int) -> dict[str, object]:
        return _record(
            ledger,
            f"operation-{index}",
            lease_id=f"lease:{index}",
            created_at=NOW + index,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(write, range(16)))

    assert len({result["event_id"] for result in results}) == 16
    assert len({result["receipt_id"] for result in results}) == 16
    verification = ledger.verify()
    assert verification["event_count"] == 16
    assert verification["receipt_count"] == 16
