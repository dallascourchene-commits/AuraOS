from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aura_coding_relationship_compass.py"

ANCHOR = '''    discovery = discover_bounded_emergent_candidates(
        objective=normalized_objective,
        neighborhood=neighborhood,
        compatibility=packet["typed_compatibility"],
        atlas=packet["atlas"],
        required_tests=required_tests,
        max_candidates=max_emergent_candidates,
        max_pairs_considered=max_neighborhood_candidate_pairs,
    )
'''

REPLACEMENT = '''    # Emergent discovery has its own hard input budget.  Feed it only the
    # source-bearing fields it actually consumes instead of the full Compass/Atlas
    # diagnostic packet.  This preserves the safety ceiling rather than raising it.
    bounded_neighborhood = {
        "neighborhood_digest": neighborhood.get("neighborhood_digest"),
        "participants": [
            {
                key: value
                for key, value in participant.items()
                if key in {
                    "participant_id",
                    "role",
                    "participant_type",
                    "kind",
                    "qualified_symbol",
                    "symbol",
                    "canonical_ref",
                    "source_hash",
                    "tests",
                    "metadata",
                }
            }
            for participant in (neighborhood.get("participants", ()) or ())
            if isinstance(participant, Mapping)
        ],
        "relations": [
            {
                key: value
                for key, value in relation.items()
                if key in {
                    "source_participant_id",
                    "target_participant_id",
                    "truth_class",
                }
            }
            for relation in (neighborhood.get("relations", ()) or ())
            if isinstance(relation, Mapping)
        ],
    }
    # Participant metadata can contain large Compass-side diagnostics.  Retain only
    # evidence fields consumed by bounded discovery.
    for participant in bounded_neighborhood["participants"]:
        metadata = participant.get("metadata")
        if isinstance(metadata, Mapping):
            participant["metadata"] = {
                key: value
                for key, value in metadata.items()
                if key in {
                    "canonical_ref",
                    "source_ref",
                    "source_hash",
                    "file_source_hash",
                    "file_path",
                    "tests",
                }
            }

    bounded_compatibility = {
        key: packet["typed_compatibility"].get(key)
        for key in ("outcome", "assessment_digest", "compatibility_digest")
        if key in packet["typed_compatibility"]
    }
    bounded_atlas = {
        "assessments": [
            {
                key: value
                for key, value in assessment.items()
                if key in {
                    "source_participant_id",
                    "target_participant_id",
                    "participant_a_id",
                    "participant_b_id",
                    "left_participant_id",
                    "right_participant_id",
                    "participant_ids",
                    "wiring_disposition",
                }
            }
            for assessment in (packet["atlas"].get("assessments", ()) or ())
            if isinstance(assessment, Mapping)
        ]
    }

    discovery = discover_bounded_emergent_candidates(
        objective=normalized_objective,
        neighborhood=bounded_neighborhood,
        compatibility=bounded_compatibility,
        atlas=bounded_atlas,
        required_tests=required_tests,
        max_candidates=max_emergent_candidates,
        max_pairs_considered=max_neighborhood_candidate_pairs,
    )
'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError(f"Compass bounded-handoff anchor expected once, found {count}")
    TARGET.write_text(text.replace(ANCHOR, REPLACEMENT, 1), encoding="utf-8")
    Path(__file__).unlink()
    print("Compass emergent discovery now receives a bounded evidence projection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
