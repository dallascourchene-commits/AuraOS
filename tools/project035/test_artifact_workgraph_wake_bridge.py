from __future__ import annotations

import unittest

from artifact_workgraph_wake_bridge import (
    ArtifactWakeBridgeError,
    ArtifactWorkDependencyBinding,
    compile_dependency_ready_proposal,
    compute_workgraph_transition_receipt_digest,
    verify_canonical_reopen_transition,
)


def artifact_event(**overrides):
    row = {
        "schema": "ArtifactAvailableEventV1",
        "event_type": "ARTIFACT_AVAILABLE",
        "event_id": "aae-1",
        "project_id": "P1",
        "artifact_sid": "artifact-sha256-abc",
        "persistence_receipt_id": "apr-1",
        "live_index_revision": "index:2",
        "currentness_ref": "head:2",
        "persisted_surface": "google_drive",
        "resource_ref": "drive:file:1",
        "owner_binding_status": "PENDING_EXTERNAL_OWNER",
        "owner_ref": None,
        "coordinate_binding_status": "PENDING_EXTERNAL_OWNER",
        "coordinate_ref": None,
        "delivery_intent_only": True,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    row.update(overrides)
    return row


def projection(**overrides):
    row = {
        "schema": "AuraArenaWorkGraphProjectionV1",
        "project_id": "P1",
        "currentness_ref": "head:2",
        "graph_digest": "graph:before",
        "cells": [
            {
                "cell_id": "C1",
                "state": "BLOCKED",
                "effective_state": "BLOCKED",
                "execution_state": "NOT_STARTED",
                "reopen_conditions": ["artifact:apr-1 available"],
            }
        ],
    }
    row.update(overrides)
    return row


def binding(**overrides):
    values = {
        "project_id": "P1",
        "artifact_sid": "artifact-sha256-abc",
        "persistence_receipt_id": "apr-1",
        "live_index_revision": "index:2",
        "currentness_ref": "head:2",
        "target_cell_id": "C1",
        "target_reopen_condition": "artifact:apr-1 available",
        "basis_graph_digest": "graph:before",
    }
    values.update(overrides)
    return ArtifactWorkDependencyBinding(**values)


def transition_receipt(**overrides):
    row = {
        "schema": "AuraArenaWorkGraphTransitionReceiptV1",
        "action": "REOPEN",
        "project_id": "P1",
        "worker_id": "W1",
        "cell_id": "C1",
        "basis_graph_digest": "graph:before",
        "before_state_digest": "state:before",
        "after_state_digest": "state:after",
        "after_graph_digest": "graph:after",
        "now_ms": 1234,
        "runtime_execution_proven": False,
        "provider_calls": 0,
    }
    row.update(overrides)
    if "receipt_digest" not in overrides:
        row["receipt_digest"] = compute_workgraph_transition_receipt_digest(row)
    return row


def after_projection(**overrides):
    row = {
        "schema": "AuraArenaWorkGraphProjectionV1",
        "project_id": "P1",
        "currentness_ref": "head:2",
        "graph_digest": "graph:after",
        "cells": [
            {
                "cell_id": "C1",
                "state": "OPEN",
                "effective_state": "OPEN",
                "execution_state": "NOT_STARTED",
                "reopen_conditions": ["artifact:apr-1 available"],
            }
        ],
    }
    row.update(overrides)
    return row


def canonical_evidence(receipt=None, **overrides):
    receipt = receipt or transition_receipt()
    row = {
        "schema": "CanonicalWorkGraphTransitionEvidenceV1",
        "status": "VERIFIED_PERSISTED_TRANSITION",
        "transition_receipt_digest": receipt["receipt_digest"],
        "project_id": "P1",
        "cell_id": "C1",
        "currentness_ref": "head:2",
        "basis_graph_digest": "graph:before",
        "before_state_digest": "state:before",
        "after_state_digest": "state:after",
        "after_graph_digest": "graph:after",
        "canonical_workgraph_owner_ref": "workgraph-owner:canonical",
        "canonical_store_ref": "workgraph-store:primary",
        "persistence_verification_ref": "wg-persist:receipt-1",
        "readback_ref": "wg-readback:after-1",
        "persistence_verified": True,
        "readback_verified": True,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    row.update(overrides)
    return row


def resolver_for(evidence):
    expected = evidence["transition_receipt_digest"]

    def resolve(receipt_digest):
        if receipt_digest != expected:
            raise AssertionError("resolver called with unexpected receipt digest")
        return dict(evidence)

    return resolve


class ArtifactWorkGraphWakeBridgeTests(unittest.TestCase):
    def proposal(self):
        return compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )

    def test_01_valid_event_compiles_reopen_proposal_only(self):
        result = self.proposal()
        self.assertEqual("REOPEN", result.requested_workgraph_action)
        self.assertTrue(result.requires_canonical_workgraph_transition)
        self.assertTrue(result.requires_admitted_worker)
        self.assertFalse(result.wake_scan_allowed)
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.effect_authorized)
        self.assertFalse(result.provider_calls_authorized)
        self.assertFalse(result.runtime_execution_proven)
        self.assertFalse(result.background_execution_claimed)

    def test_02_proposal_identity_is_replay_stable(self):
        self.assertEqual(self.proposal().proposal_id, self.proposal().proposal_id)

    def test_03_tombstone_never_reopens(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_TOMBSTONED_REVIEW_REQUIRED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(event_type="ARTIFACT_TOMBSTONED"),
                binding=binding(), workgraph_projection=projection(),
            )

    def test_04_authority_laundering_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_EVENT_AUTHORITY_WIDENING"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(execution_authorized=True),
                binding=binding(), workgraph_projection=projection(),
            )

    def test_05_stale_currentness_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_CURRENTNESS_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(currentness_ref="head:old"),
                binding=binding(), workgraph_projection=projection(),
            )

    def test_06_wrong_live_index_revision_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "LIVE_INDEX_REVISION_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(live_index_revision="index:old"),
                binding=binding(), workgraph_projection=projection(),
            )

    def test_07_stale_graph_basis_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "WORKGRAPH_BASIS_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(basis_graph_digest="graph:old"),
                workgraph_projection=projection(),
            )

    def test_08_complete_cell_requires_successor_not_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1", "state": "COMPLETE", "effective_state": "COMPLETE",
            "execution_state": "VERIFIED_COMPLETE", "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "HISTORICAL_CELL_REQUIRES_SUCCESSOR"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_09_non_declared_blocked_cell_cannot_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1", "state": "OPEN", "effective_state": "BLOCKED",
            "execution_state": "NOT_STARTED", "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TARGET_CELL_NOT_DECLARED_BLOCKED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_10_reopen_condition_must_be_exact(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "REOPEN_CONDITION_BINDING_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(),
                binding=binding(target_reopen_condition="some other trigger"),
                workgraph_projection=projection(),
            )

    def test_11_ambiguous_effect_state_blocks_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1", "state": "BLOCKED", "effective_state": "BLOCKED",
            "execution_state": "EFFECT_STARTED", "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "RECONCILE_EFFECT_STATE_REQUIRED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_12_wrong_transition_action_does_not_unlock_wake_scan(self):
        r = transition_receipt(action="CLAIM")
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "WORKGRAPH_TRANSITION_NOT_REOPEN"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r,
                after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(canonical_evidence(r)),
            )

    def test_13_wrong_transition_basis_does_not_unlock_wake_scan(self):
        r = transition_receipt(basis_graph_digest="graph:other")
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TRANSITION_BASIS_MISMATCH"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r,
                after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(canonical_evidence(r, basis_graph_digest="graph:other")),
            )

    def test_14_after_projection_must_show_open_cell(self):
        r = transition_receipt()
        bad_after = after_projection(cells=[{
            "cell_id": "C1", "state": "BLOCKED", "effective_state": "BLOCKED",
            "execution_state": "NOT_STARTED", "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "REOPEN_TRANSITION_NOT_VISIBLE_AS_OPEN"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=bad_after,
                canonical_transition_resolver=resolver_for(canonical_evidence(r)),
            )

    def test_15_missing_trusted_resolver_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_TRANSITION_EVIDENCE_RESOLVER_REQUIRED"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=transition_receipt(),
                after_projection=after_projection(),
            )

    def test_16_forged_or_missing_receipt_digest_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TRANSITION_RECEIPT_DIGEST_MISMATCH"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=transition_receipt(receipt_digest="forged"),
                after_projection=after_projection(),
                canonical_transition_resolver=lambda _: canonical_evidence(),
            )
        r = transition_receipt()
        r.pop("receipt_digest")
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TRANSITION_RECEIPT_DIGEST_REQUIRED"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r,
                after_projection=after_projection(), canonical_transition_resolver=lambda _: {},
            )

    def test_17_unpersisted_reference_transition_fails_closed(self):
        r = transition_receipt()
        e = canonical_evidence(r, status="REFERENCE_ONLY", persistence_verified=False)
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_TRANSITION_NOT_PERSISTED"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(e),
            )

    def test_18_stale_canonical_evidence_fails_closed(self):
        r = transition_receipt()
        e = canonical_evidence(r, currentness_ref="head:old")
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_EVIDENCE_CURRENTNESS_MISMATCH"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(e),
            )

    def test_19_mismatched_canonical_readback_fails_closed(self):
        r = transition_receipt()
        e = canonical_evidence(r, after_graph_digest="graph:other")
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_EVIDENCE_AFTER_GRAPH_MISMATCH"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(e),
            )

    def test_20_evidence_requires_owner_store_persistence_and_readback_refs(self):
        r = transition_receipt()
        for field, code in (
            ("canonical_workgraph_owner_ref", "CANONICAL_WORKGRAPH_OWNER_REF_REQUIRED"),
            ("canonical_store_ref", "CANONICAL_WORKGRAPH_STORE_REF_REQUIRED"),
            ("persistence_verification_ref", "TRANSITION_PERSISTENCE_VERIFICATION_REF_REQUIRED"),
            ("readback_ref", "TRANSITION_READBACK_REF_REQUIRED"),
        ):
            e = canonical_evidence(r)
            e[field] = ""
            with self.assertRaisesRegex(ArtifactWakeBridgeError, code):
                verify_canonical_reopen_transition(
                    proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
                    canonical_transition_resolver=resolver_for(e),
                )

    def test_21_evidence_cannot_launder_authority(self):
        r = transition_receipt()
        e = canonical_evidence(r, execution_authorized=True)
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_TRANSITION_EVIDENCE_AUTHORITY_WIDENING"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
                canonical_transition_resolver=resolver_for(e),
            )

    def test_22_self_minted_evidence_mapping_is_not_an_api_parameter(self):
        r = transition_receipt()
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "CANONICAL_TRANSITION_EVIDENCE_RESOLVER_REQUIRED"):
            verify_canonical_reopen_transition(
                proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
            )

    def test_23_verified_persisted_reopen_allows_scan_but_emits_no_wake(self):
        r = transition_receipt()
        e = canonical_evidence(r)
        result = verify_canonical_reopen_transition(
            proposal=self.proposal(), transition_receipt=r, after_projection=after_projection(),
            canonical_transition_resolver=resolver_for(e),
        )
        self.assertEqual("POST_TRANSITION_WAKE_SCAN_ALLOWED", result["decision"])
        self.assertEqual(r["receipt_digest"], result["transition_receipt_digest"])
        self.assertEqual("workgraph-owner:canonical", result["canonical_workgraph_owner_ref"])
        self.assertEqual("workgraph-store:primary", result["canonical_store_ref"])
        self.assertEqual("wg-persist:receipt-1", result["persistence_verification_ref"])
        self.assertEqual("wg-readback:after-1", result["readback_ref"])
        self.assertTrue(result["requires_existing_h_g_wake_scan"])
        self.assertFalse(result["wake_intent_emitted"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["provider_calls_authorized"])
        self.assertFalse(result["runtime_execution_proven"])
        self.assertFalse(result["background_execution_claimed"])


if __name__ == "__main__":
    unittest.main()
