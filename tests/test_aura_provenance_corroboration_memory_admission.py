from __future__ import annotations

import copy
import unittest

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
    verify_evidence_node,
)

CONTEXT = {"scope": "arena", "use_class": "retrieval"}


def node(
    artifact_ref: str,
    *,
    claim_key: str = "claim:alpha",
    claim_value_ref: str = "value:yes",
    world_ref: str = "world:1",
    dependency_class_ref: str = "dep:1",
    generation_ref: str = "gen:1",
    current: bool = True,
    revoked: bool = False,
    allowed_scopes: list[str] | None = None,
    allowed_use_classes: list[str] | None = None,
    supersedes: list[str] | None = None,
):
    scheme, value = artifact_ref.split(":", 1)
    return seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": artifact_ref,
            "artifact_ref_scheme": scheme,
            "artifact_ref_value": value,
            "claim_key": claim_key,
            "claim_value_ref": claim_value_ref,
            "world_ref": world_ref,
            "dependency_class_ref": dependency_class_ref,
            "generation_ref": generation_ref,
            "allowed_scopes": allowed_scopes or ["arena"],
            "allowed_use_classes": allowed_use_classes or ["retrieval"],
            "current": current,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": revoked,
            "supersedes_artifact_refs": supersedes or [],
        }
    )


class ProvenanceCorroborationMemoryAdmissionTests(unittest.TestCase):
    def test_exact_eligible_node_is_admitted_but_nonauthorizing(self) -> None:
        out = admit_evidence_nodes([node("artifact:a")], CONTEXT)
        self.assertEqual(["artifact:a"], out["eligible_artifact_refs"])
        self.assertTrue(out["hard_eligibility_precedes_ranking"])
        self.assertTrue(out["typed_artifact_reference_schemes_preserved"])
        self.assertFalse(out["reference_scheme_aliasing_performed"])
        self.assertFalse(out["input_currentness_reproved_by_this_module"])
        self.assertFalse(out["claim_world_semantics_reproved_by_this_module"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["producer_authentication_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(out["native_private_transformer_kv_accessed"])

    def test_stale_node_is_excluded_but_history_is_preserved(self) -> None:
        out = admit_evidence_nodes([node("artifact:stale", current=False)], CONTEXT)
        self.assertEqual(["artifact:stale"], out["verified_artifact_refs"])
        self.assertEqual([], out["eligible_artifact_refs"])
        self.assertEqual(["NOT_CURRENT"], out["excluded_by_artifact_ref"]["artifact:stale"])

    def test_revoked_node_is_excluded(self) -> None:
        out = admit_evidence_nodes([node("artifact:revoked", revoked=True)], CONTEXT)
        self.assertEqual([], out["eligible_artifact_refs"])
        self.assertIn("REVOKED", out["excluded_by_artifact_ref"]["artifact:revoked"])

    def test_scope_and_use_class_are_hard_gates(self) -> None:
        out = admit_evidence_nodes(
            [node("artifact:blocked", allowed_scopes=["other"], allowed_use_classes=["historical"])],
            CONTEXT,
        )
        self.assertEqual(
            ["SCOPE_NOT_ALLOWED", "USE_CLASS_NOT_ALLOWED"],
            out["excluded_by_artifact_ref"]["artifact:blocked"],
        )

    def test_same_lineage_corroborates_without_increasing_kappa(self) -> None:
        out = admit_evidence_nodes(
            [node("artifact:a", dependency_class_ref="dep:shared"), node("artifact:b", dependency_class_ref="dep:shared")],
            CONTEXT,
        )
        edge = [r for r in out["relations"] if r["kind"] == "CORROBORATES"][0]
        self.assertFalse(edge["dependency_distinct"])
        self.assertEqual(1, out["corroboration_groups"][0]["kappa"])
        self.assertFalse(out["artifact_identity_collapse_performed"])

    def test_dependency_distinct_corroborator_increases_kappa_without_node_merge(self) -> None:
        out = admit_evidence_nodes(
            [node("artifact:a", dependency_class_ref="dep:a"), node("artifact:b", dependency_class_ref="dep:b")],
            CONTEXT,
        )
        edge = [r for r in out["relations"] if r["kind"] == "CORROBORATES"][0]
        self.assertTrue(edge["dependency_distinct"])
        self.assertEqual(2, out["corroboration_groups"][0]["kappa"])
        self.assertEqual(2, len(out["verified_artifact_refs"]))

    def test_same_reference_value_across_schemes_remains_distinct_identity(self) -> None:
        digest = "a" * 64
        out = admit_evidence_nodes(
            [
                node(f"aura-workcapsule-target-sha256:{digest}", dependency_class_ref="dep:a"),
                node(f"aura-proof-artifact-sha256:{digest}", dependency_class_ref="dep:b"),
            ],
            CONTEXT,
        )
        edge = [r for r in out["relations"] if r["kind"] == "CORROBORATES"][0]
        self.assertTrue(edge["reference_schemes_distinct"])
        self.assertTrue(edge["reference_values_equal"])
        self.assertNotEqual(edge["left_artifact_ref"], edge["right_artifact_ref"])
        self.assertEqual(
            ["aura-proof-artifact-sha256", "aura-workcapsule-target-sha256"],
            out["corroboration_groups"][0]["artifact_reference_schemes"],
        )

    def test_typed_reference_fields_must_match_canonical_ref(self) -> None:
        item = node("artifact:a")
        item["artifact_ref_scheme"] = "other"
        self.assertIn("artifact_ref:TYPED_REFERENCE_MISMATCH", verify_evidence_node(item))
        with self.assertRaises(ValueError):
            admit_evidence_nodes([item], CONTEXT)

    def test_sha256_reference_scheme_requires_lower_hex_digest(self) -> None:
        raw = {
            "version": NODE_VERSION,
            "artifact_ref": "aura-proof-artifact-sha256:not-a-digest",
            "artifact_ref_scheme": "aura-proof-artifact-sha256",
            "artifact_ref_value": "not-a-digest",
            "claim_key": "claim:alpha",
            "claim_value_ref": "value:yes",
            "world_ref": "world:1",
            "dependency_class_ref": "dep:1",
            "generation_ref": "gen:1",
            "allowed_scopes": ["arena"],
            "allowed_use_classes": ["retrieval"],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
        with self.assertRaisesRegex(ValueError, "EXPECTED_LOWER_HEX_SHA256"):
            seal_evidence_node(raw)

    def test_same_claim_value_in_different_world_does_not_corroborate(self) -> None:
        out = admit_evidence_nodes([node("artifact:a", world_ref="world:1"), node("artifact:b", world_ref="world:2")], CONTEXT)
        self.assertEqual([], [r for r in out["relations"] if r["kind"] == "CORROBORATES"])

    def test_contradiction_is_preserved_without_last_write_wins(self) -> None:
        out = admit_evidence_nodes(
            [node("artifact:a", claim_value_ref="value:yes"), node("artifact:b", claim_value_ref="value:no", dependency_class_ref="dep:b")],
            CONTEXT,
        )
        self.assertEqual(1, len([r for r in out["relations"] if r["kind"] == "CONTRADICTS"]))
        self.assertEqual([{"claim_key": "claim:alpha", "world_ref": "world:1"}], out["contradictory_claim_worlds"])
        self.assertFalse(out["last_write_wins_performed"])

    def test_supersession_keeps_stale_history(self) -> None:
        old = node("artifact:old", current=False, generation_ref="gen:old")
        new = node("artifact:new", generation_ref="gen:new", supersedes=["artifact:old"])
        out = admit_evidence_nodes([old, new], CONTEXT)
        self.assertEqual(["artifact:new"], out["eligible_artifact_refs"])
        self.assertIn("artifact:old", out["verified_artifact_refs"])
        self.assertEqual(
            [{"kind": "SUPERSEDES", "from_artifact_ref": "artifact:new", "to_artifact_ref": "artifact:old"}],
            [r for r in out["relations"] if r["kind"] == "SUPERSEDES"],
        )

    def test_tampered_receipt_digest_fails_closed(self) -> None:
        item = node("artifact:a")
        item["claim_value_ref"] = "value:tampered"
        self.assertIn("NODE_RECEIPT_IDENTITY_DIGEST_MISMATCH", verify_evidence_node(item))
        with self.assertRaises(ValueError):
            admit_evidence_nodes([item], CONTEXT)

    def test_python_bool_int_confusion_fails_closed(self) -> None:
        item = node("artifact:a")
        raw = copy.deepcopy(item)
        raw.pop("receipt_identity")
        raw["current"] = 1
        with self.assertRaises(ValueError):
            seal_evidence_node(raw)

    def test_closed_schema_rejects_k27_or_cache_escape_hatches(self) -> None:
        item = node("artifact:a")
        item["k27_coordinate"] = [1, 2, 3]
        self.assertEqual(["NODE_CLOSED_SCHEMA_MISMATCH"], verify_evidence_node(item))
        with self.assertRaises(ValueError):
            admit_evidence_nodes([item], CONTEXT)

    def test_duplicate_artifact_identity_fails_closed(self) -> None:
        same = node("artifact:a")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ARTIFACT_REF"):
            admit_evidence_nodes([same, copy.deepcopy(same)], CONTEXT)

    def test_output_is_deterministic_under_input_permutation(self) -> None:
        a = node("artifact:a", dependency_class_ref="dep:a")
        b = node("artifact:b", dependency_class_ref="dep:b")
        self.assertEqual(admit_evidence_nodes([a, b], CONTEXT), admit_evidence_nodes([b, a], CONTEXT))


if __name__ == "__main__":
    unittest.main()
