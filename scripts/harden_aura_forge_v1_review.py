from __future__ import annotations

import json
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"missing source fragment in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_source() -> None:
    replace_once(
        "aura_forge.py",
        '''    "bearer_token",
    "refresh_token",
})
''',
        '''    "bearer_token",
    "refresh_token",
    "authorization",
    "client_secret",
    "passphrase",
    "signing_key",
})
''',
    )
    replace_once(
        "aura_forge.py",
        '''    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized
''',
        '''    if not normalized or normalized == ".":
        raise ValueError(f"{field_name} must not be empty")
    return normalized
''',
    )
    replace_once(
        "aura_forge.py",
        '''            metadata={
                "forge_version": FORGE_VERSION,
                "forge_contract_id": state["contract"].contract_id,
                **dict(request.metadata),
            },
''',
        '''            metadata={
                **dict(request.metadata),
                "forge_version": FORGE_VERSION,
                "forge_contract_id": state["contract"].contract_id,
            },
''',
    )
    replace_once(
        "aura_forge.py",
        '''        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": state["status"],
            "contract": state["contract"].to_dict(),
            "session": _sanitize(session),
            "decision_eligible": state["status"] == REVIEW_READY_STATUS,
            "production_mutation": False,
            "human_review_required": True,
        }
''',
        '''        review_packet = (
            self.human_review_packet(run_id)
            if state["status"] == REVIEW_READY_STATUS
            else None
        )
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": state["status"],
            "contract": state["contract"].to_dict(),
            "session": _sanitize(session),
            "decision_eligible": bool(
                review_packet and review_packet.get("decision_eligible") is True
            ),
            "human_review_packet": review_packet,
            "production_mutation": False,
            "human_review_required": True,
        }
''',
    )
    replace_once(
        "aura_forge.py",
        '''    if not list(value.get("required_gates") or []):
        errors.append("required_gates_must_not_be_empty")
    if not list(value.get("act_capsules") or []):
''',
        '''    required_gates = list(value.get("required_gates") or [])
    if not required_gates:
        errors.append("required_gates_must_not_be_empty")
    else:
        unsupported = sorted(set(required_gates) - SUPPORTED_REQUIRED_GATES)
        if unsupported:
            errors.append(f"unsupported_required_gates:{','.join(unsupported)}")
    if not list(value.get("act_capsules") or []):
''',
    )


def patch_tests() -> None:
    replace_once(
        "tests/test_aura_forge.py",
        '''        "metadata": {"ticket": "ENG-42", "api_key": "must-not-leak"},
''',
        '''        "metadata": {
            "ticket": "ENG-42",
            "api_key": "must-not-leak",
            "forge_contract_id": "spoofed-lineage",
        },
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''    assert contract["metadata"] == {"ticket": "ENG-42"}
''',
        '''    assert contract["metadata"] == {
        "ticket": "ENG-42",
        "forge_contract_id": "spoofed-lineage",
    }
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''    assert manager.opened["metadata"]["forge_contract_id"] == result["contract"]["contract_id"]
''',
        '''    assert manager.opened["metadata"]["forge_contract_id"] == result["contract"]["contract_id"]
    assert manager.opened["metadata"]["forge_contract_id"] != "spoofed-lineage"
    assert manager.opened["metadata"]["forge_version"] == "AURA_FORGE_V1"
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''def test_submit_stops_at_human_review_without_promotion(tmp_path: Path) -> None:
''',
        '''def test_status_does_not_claim_decision_eligibility_without_proof(tmp_path: Path) -> None:
    runtime, _bridge, manager = build_runtime(tmp_path)
    started = runtime.start(request())
    manager.status = "READY_FOR_HUMAN_REVIEW"

    status = runtime.status(started["run_id"])

    assert status["status"] == "READY_FOR_HUMAN_REVIEW"
    assert status["decision_eligible"] is False
    assert status["human_review_packet"]["required_gate_results"] == {
        "canonical_arena_verifier": False,
        "hotswap_readiness": True,
    }


def test_submit_stops_at_human_review_without_promotion(tmp_path: Path) -> None:
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
        '''def test_contract_validator_rejects_unsupported_gates(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)
    contract = runtime.prepare(request())["contract"]
    contract["required_gates"] = ["hidden_tests"]
    assert validate_forge_contract(contract) == ["unsupported_required_gates:hidden_tests"]


def test_export_delegates_to_safe_session_owner(tmp_path: Path) -> None:
''',
    )


def patch_schema() -> None:
    target = Path("schemas/aura_forge_arena_evidence_contract.schema.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["properties"]["required_gates"]["items"] = {
        "type": "string",
        "enum": ["canonical_arena_verifier", "hotswap_readiness"],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    patch_source()
    patch_tests()
    patch_schema()


if __name__ == "__main__":
    main()
