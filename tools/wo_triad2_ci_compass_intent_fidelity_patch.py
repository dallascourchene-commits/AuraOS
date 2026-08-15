from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_coding_relationship_compass.py"

ANCHOR = '''    packet["grounding_receipt"] = grounding_receipt
    packet["grounding_receipt_digest"] = stable_digest(grounding_receipt)

    discovery = discover_bounded_emergent_candidates(
'''

REPLACEMENT = '''    packet["grounding_receipt"] = grounding_receipt
    packet["grounding_receipt_digest"] = stable_digest(grounding_receipt)

    # Bilateral intent fidelity is a deterministic admission gate, not a score.
    # Once Atlas projection proves any confirmed obligation is unprojected (or
    # there is no assessment at all), stop before emergent discovery/scoring so
    # secondary resource limits can never mask the human-reconfirmation route.
    intent_fidelity_denied = bool(
        bilateral is not None
        and (
            not atlas_intelligence.get("assessments")
            or has_unprojected_bilateral_obligation
        )
    )
    if intent_fidelity_denied:
        preflight_failure_classes: list[str] = []
        if packet["typed_compatibility"].get("outcome") in {"PROHIBITED", "INCOMPATIBLE", "BLOCKED"}:
            preflight_failure_classes.append("INTERFACE")
        if packet.get("prohibitions"):
            preflight_failure_classes.append("PROHIBITION")
        preflight_failure_classes.append("INTENT_FIDELITY")

        packet["bounded_emergent_discovery"] = {
            "skipped": True,
            "reason": "INTENT_FIDELITY",
            "candidates": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["bounded_emergent_verification"] = {
            "skipped": True,
            "reason": "INTENT_FIDELITY",
            "accepted_candidates": [],
            "rejected_candidates": [],
            "proposal_only": True,
        }
        packet["change_graph"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "phase_capsules": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["phase_capsules"] = []
        packet["act_capsules"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "act_capsules": [],
            "proposal_only": True,
            "safe_to_patch": False,
        }
        packet["agent_ir"] = {
            "ok": False,
            "reason": "INTENT_FIDELITY",
            "nodes": [],
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        packet["council_route"] = route_compass_failure_classes(preflight_failure_classes)
        packet["experience_projection_template"] = {
            "relationship_ids": [],
            "required_outcomes": ["DENIAL"],
            "valid_time_bound_to_repository_head": True,
            "transaction_time_bound_to_receipt_creation": True,
            "eligibility_gate_closed_by_default": True,
            "proposal_only": True,
        }
        packet["compass_digest"] = _stable_digest(_compass_digest_payload(packet))
        return packet

    discovery = discover_bounded_emergent_candidates(
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"Compass intent-fidelity insertion anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("Compass now denies unprojected bilateral intent before emergent discovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
