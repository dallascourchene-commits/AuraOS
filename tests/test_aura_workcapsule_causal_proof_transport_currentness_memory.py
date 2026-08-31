from __future__ import annotations

import copy
import inspect
import unittest

from scripts.aura_provenance_corroboration_memory_admission import (
    admit_evidence_nodes,
    seal_evidence_node,
)
from scripts.aura_workcapsule_causal_proof_transport_currentness_memory import (
    CAUSAL_HOST_ENVELOPE_CURRENTNESS_CONTEXT,
    CROSS_TRANSPORT_REJECTION,
    EVIDENCE_TYPE,
    CURRENTNESS_DOMAIN,
    PROOF_CURRENTNESS_CONTEXT,
    admit_causal_proof_transport_currentness_memory,
)
from tests.test_aura_workcapsule_causal_envelope_raw_slice_noninterchangeability import (
    pr573_receipt,
    pr574_receipt,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


def kwargs():
    return {
        "causal_artifact_host_receipt": pr573_receipt(),
        "causal_raw_slice_host_separation_receipt": pr574_receipt(),
        "pr568_receipt": pr568_receipt(),
        "pr572_receipt": pr572_receipt(),
    }


class CausalProofTransportCurrentnessMemoryTests(unittest.TestCase):
    def test_exact_relation_projects_two_proof_nodes_and_one_rank_neutral_edge(self) -> None:
        out = admit_causal_proof_transport_currentness_memory(**kwargs())
        nodes = out["proof_memory_nodes"]
        self.assertEqual(2, len(nodes))
        self.assertNotEqual(nodes[0]["artifact_ref"], nodes[1]["artifact_ref"])
        self.assertTrue(out["two_proof_artifacts_remain_two_memory_nodes"])
        self.assertEqual(1, out["corroboration_relation_count"])
        self.assertEqual(2, out["corroboration_kappa"])
        for node in nodes:
            self.assertEqual(EVIDENCE_TYPE, node["evidence_type"])
            self.assertEqual(CURRENTNESS_DOMAIN, node["currentness_domain"])
            self.assertTrue(node["current"])
        edge = [row for row in out["retrieval_admission"]["relations"] if row["kind"] == "CORROBORATES"][0]
        self.assertTrue(edge["dependency_distinct"])
        self.assertFalse(edge["rank_transition_credit"])
        self.assertFalse(edge["proof_artifacts_interchangeable"])
        self.assertFalse(edge["currentness_domains_interchangeable"])

    def test_causal_host_envelope_currentness_rejects_both_on_three_axes(self) -> None:
        out = admit_causal_proof_transport_currentness_memory(**kwargs())
        probe = out["causal_host_envelope_currentness_admission"]
        self.assertEqual([], probe["eligible_artifact_refs"])
        for node in out["proof_memory_nodes"]:
            self.assertEqual(
                CROSS_TRANSPORT_REJECTION,
                probe["excluded_by_artifact_ref"][node["artifact_ref"]],
            )
        self.assertFalse(out["causal_host_envelope_currentness_proven"])
        self.assertFalse(out["proof_to_host_envelope_type_conversion_performed"])

    def test_stale_proof_node_fails_even_in_owned_proof_domain(self) -> None:
        out = admit_causal_proof_transport_currentness_memory(**kwargs())
        stale = copy.deepcopy(out["proof_memory_nodes"][0])
        stale.pop("receipt_identity")
        stale["current"] = False
        stale = seal_evidence_node(stale)
        probe = admit_evidence_nodes([stale], PROOF_CURRENTNESS_CONTEXT)
        self.assertEqual([], probe["eligible_artifact_refs"])
        self.assertEqual(["NOT_CURRENT"], probe["excluded_by_artifact_ref"][stale["artifact_ref"]])

    def test_pr577_world_drift_fails_before_memory_projection(self) -> None:
        values = kwargs()
        values["pr572_receipt"] = pr572_receipt(source_generation=44)
        with self.assertRaisesRegex(ValueError, "PR577_LIVE_SOURCE_INSTANCE_MISMATCH"):
            admit_causal_proof_transport_currentness_memory(**values)

    def test_pr594_authority_ceiling_survives_memory_projection(self) -> None:
        values = kwargs()
        widened = pr568_receipt()
        widened["authority"]["execution_authorized"] = True
        values["pr568_receipt"] = widened
        with self.assertRaisesRegex(ValueError, "PR577_PR568_AUTHORITY_WIDENED"):
            admit_causal_proof_transport_currentness_memory(**values)

    def test_all_positive_memory_results_remain_nonauthorizing(self) -> None:
        out = admit_causal_proof_transport_currentness_memory(**kwargs())
        for key in (
            "causal_host_envelope_currentness_proven",
            "proof_to_host_envelope_type_conversion_performed",
            "corroboration_rank_transition_performed",
            "producer_authenticated",
            "semantic_truth_proven",
            "host_resolver_trust_proven",
            "host_observation_authority_proven",
            "trusted_continuation_ready",
            "effect_authority_proven",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
        ):
            self.assertFalse(out[key], key)

    def test_public_boundary_has_only_four_exact_parent_receipts(self) -> None:
        params = set(inspect.signature(admit_causal_proof_transport_currentness_memory).parameters)
        self.assertEqual(
            {
                "causal_artifact_host_receipt",
                "causal_raw_slice_host_separation_receipt",
                "pr568_receipt",
                "pr572_receipt",
            },
            params,
        )
        forbidden = {
            "evidence_type", "currentness_domain", "current", "use_class", "context",
            "host_rank", "resolver", "producer_authenticated", "semantic_truth",
            "effect_authority", "k27_coordinate", "kv_cache",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_projection_is_deterministic(self) -> None:
        first = admit_causal_proof_transport_currentness_memory(**copy.deepcopy(kwargs()))
        second = admit_causal_proof_transport_currentness_memory(**copy.deepcopy(kwargs()))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
