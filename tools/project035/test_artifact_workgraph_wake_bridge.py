from __future__ import annotations

import unittest

from artifact_workgraph_wake_bridge import (
    ArtifactWakeBridgeError,
    ArtifactWorkDependencyBinding,
    compile_dependency_ready_proposal,
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
        "receipt_digest": "receipt:1",
        "runtime_execution_proven": False,
        "provider_calls": 0,
    }
    row.update(overrides)
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


class ArtifactWorkGraphWakeBridgeTests(unittest.TestCase):
    def test_valid_event_compiles_reopen_proposal_only(self):
        result = compile_dependency_ready_proposal(
            artifact_event=artifact_event(),
            binding=binding(),
            workgraph_projection=projection(),
        )
        self.assertEqual("REOPEN", result.requested_workgraph_action)
        self.assertTrue(result.requires_canonical_workgraph_transition)
        self.assertTrue(result.requires_admitted_worker)
        self.assertFalse(result.wake_scan_allowed)
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.effect_authorized)
        self.assertFalse(result.provider_calls_authorized)
        self.assertFalse(result.runtime_execution_proven)
        self.assertFalse(result.background_execution_claimed)

    def test_proposal_identity_is_replay_stable(self):
        first = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        second = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        self.assertEqual(first.proposal_id, second.proposal_id)

    def test_tombstone_never_reopens(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_TOMBSTONED_REVIEW_REQUIRED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(event_type="ARTIFACT_TOMBSTONED"),
                binding=binding(),
                workgraph_projection=projection(),
            )

    def test_authority_laundering_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_EVENT_AUTHORITY_WIDENING"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(execution_authorized=True),
                binding=binding(),
                workgraph_projection=projection(),
            )

    def test_stale_currentness_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "ARTIFACT_CURRENTNESS_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(currentness_ref="head:old"),
                binding=binding(),
                workgraph_projection=projection(),
            )

    def test_wrong_live_index_revision_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "LIVE_INDEX_REVISION_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(live_index_revision="index:old"),
                binding=binding(),
                workgraph_projection=projection(),
            )

    def test_stale_graph_basis_fails_closed(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "WORKGRAPH_BASIS_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(),
                binding=binding(basis_graph_digest="graph:old"),
                workgraph_projection=projection(),
            )

    def test_complete_cell_requires_successor_not_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1",
            "state": "COMPLETE",
            "effective_state": "COMPLETE",
            "execution_state": "VERIFIED_COMPLETE",
            "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "HISTORICAL_CELL_REQUIRES_SUCCESSOR"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_non_declared_blocked_cell_cannot_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1",
            "state": "OPEN",
            "effective_state": "BLOCKED",
            "execution_state": "NOT_STARTED",
            "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TARGET_CELL_NOT_DECLARED_BLOCKED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_reopen_condition_must_be_exact(self):
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "REOPEN_CONDITION_BINDING_MISMATCH"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(),
                binding=binding(target_reopen_condition="some other trigger"),
                workgraph_projection=projection(),
            )

    def test_ambiguous_effect_state_blocks_reopen(self):
        p = projection(cells=[{
            "cell_id": "C1",
            "state": "BLOCKED",
            "effective_state": "BLOCKED",
            "execution_state": "EFFECT_STARTED",
            "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "RECONCILE_EFFECT_STATE_REQUIRED"):
            compile_dependency_ready_proposal(
                artifact_event=artifact_event(), binding=binding(), workgraph_projection=p
            )

    def test_wrong_transition_action_does_not_unlock_wake_scan(self):
        proposal = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "WORKGRAPH_TRANSITION_NOT_REOPEN"):
            verify_canonical_reopen_transition(
                proposal=proposal,
                transition_receipt=transition_receipt(action="CLAIM"),
                after_projection=after_projection(),
            )

    def test_wrong_transition_basis_does_not_unlock_wake_scan(self):
        proposal = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "TRANSITION_BASIS_MISMATCH"):
            verify_canonical_reopen_transition(
                proposal=proposal,
                transition_receipt=transition_receipt(basis_graph_digest="graph:other"),
                after_projection=after_projection(),
            )

    def test_verified_reopen_allows_existing_wake_scan_but_emits_no_wake(self):
        proposal = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        result = verify_canonical_reopen_transition(
            proposal=proposal,
            transition_receipt=transition_receipt(),
            after_projection=after_projection(),
        )
        self.assertEqual("POST_TRANSITION_WAKE_SCAN_ALLOWED", result["decision"])
        self.assertTrue(result["requires_existing_h_g_wake_scan"])
        self.assertFalse(result["wake_intent_emitted"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["provider_calls_authorized"])
        self.assertFalse(result["runtime_execution_proven"])
        self.assertFalse(result["background_execution_claimed"])

    def test_after_projection_must_show_open_cell(self):
        proposal = compile_dependency_ready_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=projection()
        )
        bad_after = after_projection(cells=[{
            "cell_id": "C1",
            "state": "BLOCKED",
            "effective_state": "BLOCKED",
            "execution_state": "NOT_STARTED",
            "reopen_conditions": ["artifact:apr-1 available"],
        }])
        with self.assertRaisesRegex(ArtifactWakeBridgeError, "REOPEN_TRANSITION_NOT_VISIBLE_AS_OPEN"):
            verify_canonical_reopen_transition(
                proposal=proposal,
                transition_receipt=transition_receipt(),
                after_projection=bad_after,
            )


if __name__ == "__main__":
    unittest.main()
