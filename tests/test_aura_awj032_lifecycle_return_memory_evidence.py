from __future__ import annotations

import copy
from dataclasses import replace
import inspect
import unittest

from scripts.aura_awj032_lifecycle_return_memory_evidence import (
    ARTIFACT_REF_SCHEME,
    EVIDENCE_TYPE,
    admit_lifecycle_return_memory_evidence,
    packet_artifact_ref,
    verify_lifecycle_return_memory_evidence,
)
from tests.test_aura_provenance_corroboration_memory_admission import node
from tools.awj032.test_glm53_owner_host_lifecycle_return_packet import (
    OwnerHostLifecycleReturnPacketTests,
)


def packet():
    return OwnerHostLifecycleReturnPacketTests().packet()


def context(*, accepted=None):
    return {
        "scope": "arena",
        "use_class": "retrieval",
        "accepted_evidence_types": accepted or [EVIDENCE_TYPE],
    }


def evidence(p=None, **changes):
    p = p or packet()
    kwargs = {
        "evidence_type": EVIDENCE_TYPE,
        "claim_key": "awj032:lifecycle-return-artifact",
        "claim_value_ref": "packet-digest:" + p.packet_digest,
        "world_ref": "awj032:glm53:c2-return-world",
        "dependency_class_ref": "awj032:c2-owner-host-attempt",
        "generation_ref": "pr586:aa3fcd9a4cefd18dbc991c3e8a450fcfbbb6726b",
    }
    kwargs.update(changes)
    return node(packet_artifact_ref(p), **kwargs)


class LifecycleReturnMemoryEvidenceTests(unittest.TestCase):
    def test_exact_packet_can_be_admitted_as_evidence_only(self):
        p = packet()
        e = evidence(p)
        self.assertEqual(
            [],
            verify_lifecycle_return_memory_evidence(
                lifecycle_return_packet=p, evidence_node=e, context=context()
            ),
        )
        out = admit_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p, evidence_node=e, context=context()
        )
        self.assertTrue(out["pr586_lifecycle_return_packet_ceiling_verified"])
        self.assertTrue(out["pr581_memory_admission_owner_reused"])
        self.assertTrue(out["memory_evidence_eligible"])
        self.assertTrue(out["attempt_telemetry_remembered_as_evidence_only"])
        self.assertFalse(out["memory_admission_is_lifecycle_measurement_admission"])
        self.assertFalse(out["memory_admission_is_lifecycle_registry_admission"])
        self.assertFalse(out["memory_admission_is_real_w4_policy_winner"])
        self.assertFalse(out["attempt_telemetry_promoted_to_lifecycle_metric_vector"])
        self.assertFalse(out["attempt_reported_physical_read_bytes_independently_attested"])
        self.assertFalse(out["input_currentness_reproved_by_child"])
        self.assertFalse(out["claim_world_semantics_reproved_by_child"])
        self.assertFalse(out["producer_authentication_proven"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["g2_admitted"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_stale_node_is_not_promoted_to_memory_eligibility_by_exact_packet(self):
        p = packet()
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p,
            evidence_node=evidence(p, current=False),
            context=context(),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:NOT_CURRENT", violations)

    def test_revoked_node_is_not_promoted_by_exact_packet(self):
        p = packet()
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p,
            evidence_node=evidence(p, revoked=True),
            context=context(),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:REVOKED", violations)

    def test_context_must_accept_lifecycle_return_evidence_type(self):
        p = packet()
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p,
            evidence_node=evidence(p),
            context=context(accepted=["some-other-evidence"]),
        )
        self.assertIn("MEMORY_NOT_ELIGIBLE:EVIDENCE_TYPE_NOT_ACCEPTED", violations)

    def test_internally_valid_foreign_packet_ref_rejects_at_relation_layer(self):
        p = packet()
        foreign_ref = f"{ARTIFACT_REF_SCHEME}:" + "0" * 64
        foreign = node(
            foreign_ref,
            evidence_type=EVIDENCE_TYPE,
            claim_key="awj032:lifecycle-return-artifact",
            claim_value_ref="packet-digest:" + "0" * 64,
            world_ref="awj032:glm53:c2-return-world",
            dependency_class_ref="awj032:c2-owner-host-attempt",
            generation_ref="foreign:valid-node",
        )
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p, evidence_node=foreign, context=context()
        )
        self.assertIn("LIFECYCLE_RETURN_PACKET_ARTIFACT_REF_MISMATCH", violations)
        self.assertIn("LIFECYCLE_RETURN_PACKET_REF_VALUE_MISMATCH", violations)

    def test_attempt_telemetry_change_changes_packet_identity_and_invalidates_old_node_ref(self):
        p = packet()
        old = evidence(p)
        changed = replace(
            p,
            attempt_reported_physical_read_bytes=p.attempt_reported_physical_read_bytes + 1,
        )
        self.assertNotEqual(p.packet_digest, changed.packet_digest)
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=changed, evidence_node=old, context=context()
        )
        self.assertIn("LIFECYCLE_RETURN_PACKET_ARTIFACT_REF_MISMATCH", violations)

    def test_packet_cannot_widen_physical_io_attestation_before_memory_admission(self):
        p = replace(packet(), physical_io_attested_by_this_packet=True)
        violations = verify_lifecycle_return_memory_evidence(
            lifecycle_return_packet=p, evidence_node=evidence(p), context=context()
        )
        self.assertIn(
            "PACKET_PR586_CEILING_WIDENED:physical_io_attested_by_this_packet",
            violations,
        )

    def test_packet_cannot_widen_registry_policy_g2_or_effect_before_memory_admission(self):
        for field in (
            "lifecycle_registry_verified_by_this_packet",
            "real_w4_policy_winner_proven",
            "g2_admitted",
            "effect_authority_proven",
        ):
            with self.subTest(field=field):
                p = replace(packet(), **{field: True})
                violations = verify_lifecycle_return_memory_evidence(
                    lifecycle_return_packet=p, evidence_node=evidence(p), context=context()
                )
                self.assertIn("PACKET_PR586_CEILING_WIDENED:" + field, violations)

    def test_public_boundary_has_no_metric_registry_auth_or_effect_escape_hatch(self):
        params = set(inspect.signature(verify_lifecycle_return_memory_evidence).parameters)
        self.assertEqual({"lifecycle_return_packet", "evidence_node", "context"}, params)
        forbidden = {
            "cache_hit_ratio",
            "energy_joules",
            "peak_resident_bytes",
            "warmup_seconds",
            "restart_seconds",
            "revalidation_seconds",
            "control_overhead_seconds",
            "physical_io_attested",
            "registry",
            "registry_record",
            "producer_authenticated",
            "real_w4_policy_winner_proven",
            "g2_admitted",
            "effect_authority_proven",
            "semantic_truth",
            "k27_coordinate",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_admission_is_deterministic(self):
        p = packet()
        kwargs = {
            "lifecycle_return_packet": p,
            "evidence_node": evidence(p),
            "context": context(),
        }
        first = admit_lifecycle_return_memory_evidence(**copy.deepcopy(kwargs))
        second = admit_lifecycle_return_memory_evidence(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
