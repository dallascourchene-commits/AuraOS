from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPASS = ROOT / "aura_coding_relationship_compass.py"
NAVIGATOR = ROOT / "aura_codebase_navigator.py"

COMPASS_ANCHOR = '''    packet["grounding_receipt"] = grounding_receipt
    packet["grounding_receipt_digest"] = stable_digest(grounding_receipt)

    discovery = discover_bounded_emergent_candidates(
        objective=normalized_objective,
        neighborhood=neighborhood,
        compatibility=packet["typed_compatibility"],
        atlas=packet["atlas"],
        required_tests=required_tests,
        max_candidates=max_emergent_candidates,
        max_pairs_considered=max_neighborhood_candidate_pairs,
    )
'''

COMPASS_REPLACEMENT = '''    packet["grounding_receipt"] = grounding_receipt
    packet["grounding_receipt_digest"] = stable_digest(grounding_receipt)

    # Bilateral intent fidelity is a deterministic admission gate, not a score.
    # Stop before emergent discovery when confirmed intent is not fully projected,
    # so secondary resource limits cannot mask the human-reconfirmation route.
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

    # Bounded emergent discovery consumes only a narrow projection of the rich
    # neighborhood/Atlas packet. Keep the exact original neighborhood for the
    # downstream verifier, but do not charge unrelated CODEMAP metadata against
    # the 512-KiB discovery input ceiling.
    discovery_participants: list[dict[str, Any]] = []
    for item in neighborhood.get("participants", ()) or ():
        if not isinstance(item, Mapping):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
        discovery_participants.append({
            "participant_id": item.get("participant_id"),
            "qualified_symbol": item.get("qualified_symbol"),
            "symbol": item.get("symbol"),
            "role": item.get("role"),
            "participant_type": item.get("participant_type"),
            "kind": item.get("kind"),
            "canonical_ref": item.get("canonical_ref"),
            "source_hash": item.get("source_hash"),
            "tests": list(item.get("tests", ()) or ())[:32],
            "metadata": {
                "file_path": metadata.get("file_path"),
                "canonical_ref": metadata.get("canonical_ref"),
                "source_ref": metadata.get("source_ref"),
                "source_hash": metadata.get("source_hash"),
                "file_source_hash": metadata.get("file_source_hash"),
                "tests": list(metadata.get("tests", ()) or ())[:32],
            },
        })
    discovery_relations = [
        {
            "source_participant_id": item.get("source_participant_id"),
            "target_participant_id": item.get("target_participant_id"),
            "truth_class": item.get("truth_class"),
        }
        for item in neighborhood.get("relations", ()) or ()
        if isinstance(item, Mapping)
    ]
    discovery_neighborhood = {
        "neighborhood_digest": neighborhood.get("neighborhood_digest"),
        "participants": discovery_participants,
        "relations": discovery_relations,
    }
    discovery_assessment_keys = (
        "source_participant_id", "participant_a_id", "left_participant_id",
        "target_participant_id", "participant_b_id", "right_participant_id",
        "participant_ids", "wiring_disposition",
    )
    discovery_atlas = {
        "assessments": [
            {key: item.get(key) for key in discovery_assessment_keys if key in item}
            for item in packet["atlas"].get("assessments", ()) or ()
            if isinstance(item, Mapping)
        ]
    }
    compatibility = packet["typed_compatibility"]
    discovery_compatibility = {
        key: compatibility.get(key)
        for key in ("outcome", "assessment_digest", "compatibility_digest")
        if key in compatibility
    }
    if not discovery_compatibility.get("assessment_digest") and not discovery_compatibility.get("compatibility_digest"):
        discovery_compatibility["compatibility_digest"] = stable_digest(compatibility)

    discovery = discover_bounded_emergent_candidates(
        objective=normalized_objective,
        neighborhood=discovery_neighborhood,
        compatibility=discovery_compatibility,
        atlas=discovery_atlas,
        required_tests=required_tests,
        max_candidates=max_emergent_candidates,
        max_pairs_considered=max_neighborhood_candidate_pairs,
    )
'''

COMMAND_MENTIONS_ANCHOR = '''def _command_mentions(text: str) -> list[str]:
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    return commands[:20]


def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based line references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        hits = [
            index
            for index, line in enumerate(lines, start=1)
            if " ".join(line.strip().split()).startswith(needle)
        ]
        if hits:
            locations[command] = hits[:8]
    return locations
'''

COMMAND_MENTIONS_REPLACEMENT = '''def _command_mentions(text: str) -> list[str]:
    """Extract executable Python invocations and Aura-style bang commands."""
    commands: list[str] = []
    for match in re.finditer(r"(?m)^\\s*(python(?:3)?\\s+-m\\s+[A-Za-z0-9_\\.]+|python(?:3)?\\s+[A-Za-z0-9_./-]+\\.py[^\\n]*)", text):
        command = " ".join(match.group(1).strip().split())
        if command and command not in commands:
            commands.append(command)
    for match in re.finditer(r"(?<!\\w)![A-Za-z_][\\w-]*", text):
        command = match.group(0)
        if command not in commands:
            commands.append(command)
    return commands[:20]


def _command_locations(text: str, commands: list[str]) -> dict[str, list[int]]:
    """Return stable 1-based line references for extracted commands."""
    lines = text.splitlines()
    locations: dict[str, list[int]] = {}
    for command in commands:
        needle = " ".join(command.strip().split())
        if needle.startswith("!"):
            hits = [index for index, line in enumerate(lines, start=1) if needle in line]
        else:
            hits = [
                index
                for index, line in enumerate(lines, start=1)
                if " ".join(line.strip().split()).startswith(needle)
            ]
        if hits:
            locations[command] = hits[:8]
    return locations
'''

COMMAND_INDEX_ANCHOR = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        for command in card.get("commands", []):
            if card["path"] not in out[command]:
                out[command].append(card["path"])
    return dict(out)
'''

COMMAND_INDEX_REPLACEMENT = '''def _command_index(cards: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map commands to source locations so consumers can resolve enclosing symbols."""
    out: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        path = str(card.get("path") or "")
        command_lines = card.get("command_lines", {}) if isinstance(card.get("command_lines"), dict) else {}
        for command in card.get("commands", []):
            lines = command_lines.get(command, []) if isinstance(command_lines.get(command, []), list) else []
            locations = [f"{path}:{int(line)}" for line in lines if isinstance(line, int) and line > 0] or [path]
            for location in locations:
                if location not in out[command]:
                    out[command].append(location)
    return dict(out)
'''


def replace_once(path: Path, anchor: str, replacement: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label} anchor expected once, found {count}")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")


def main() -> int:
    replace_once(COMPASS, COMPASS_ANCHOR, COMPASS_REPLACEMENT, "Compass repair")
    replace_once(NAVIGATOR, COMMAND_MENTIONS_ANCHOR, COMMAND_MENTIONS_REPLACEMENT, "command mentions")
    replace_once(NAVIGATOR, COMMAND_INDEX_ANCHOR, COMMAND_INDEX_REPLACEMENT, "command index")
    print("Phase-3 Compass + CODEMAP command-index contract repairs applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
