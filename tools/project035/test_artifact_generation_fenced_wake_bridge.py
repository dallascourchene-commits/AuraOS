from __future__ import annotations

import unittest

import artifact_generation_fenced_wake_bridge as fence
import artifact_workgraph_wake_bridge as core


def artifact_event(**overrides):
    row = {
        "schema": "ArtifactAvailableEventV1",
        "event_type": "ARTIFACT_AVAILABLE",
        "event_id": "aae-generation-7",
        "project_id": "P1",
        "artifact_sid": "artifact-sha256-generation-7",
        "persistence_receipt_id": "apr-generation-7",
        "live_index_revision": "index:7",
        "currentness_ref": "head:7",
        "persisted_surface": "google_drive",
        "resource_ref": "drive:file:1",
        "source_event_generation": 7,
        "mirror_fence": "mirror:7",
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


def binding(**overrides):
    values = {
        "project_id": "P1",
        "artifact_sid": "artifact-sha256-generation-7",
        "persistence_receipt_id": "apr-generation-7",
        "live_index_revision": "index:7",
        "currentness_ref": "head:7",
        "target_cell_id": "C1",
        "target_reopen_condition": "artifact:apr-generation-7 available",
        "basis_graph_digest": "graph:before",
    }
    values.update(overrides)
    return core.ArtifactWorkDependencyBinding(**values)


def before_projection():
    return {
        "schema": "AuraArenaWorkGraphProjectionV1",
        "project_id": "P1",
        "currentness_ref": "head:7",
        "graph_digest": "graph:before",
        "cells": [{
            "cell_id": "C1",
            "state": "BLOCKED",
            "effective_state": "BLOCKED",
            "execution_state": "NOT_STARTED",
            "reopen_conditions": ["artifact:apr-generation-7 available"],
        }],
    }


def after_projection():
    return {
        "schema": "AuraArenaWorkGraphProjectionV1",
        "project_id": "P1",
        "currentness_ref": "head:7",
        "graph_digest": "graph:after",
        "cells": [{
            "cell_id": "C1",
            "state": "OPEN",
            "effective_state": "OPEN",
            "execution_state": "NOT_STARTED",
            "reopen_conditions": ["artifact:apr-generation-7 available"],
        }],
    }


def generation_evidence(**overrides):
    row = {
        "schema": fence.GENERATION_EVIDENCE_SCHEMA,
        "status": "VERIFIED_CURRENT_RESOURCE_GENERATION",
        "project_id": "P1",
        "persisted_surface": "google_drive",
        "resource_ref": "drive:file:1",
        "resource_generation": 7,
        "artifact_sid": "artifact-sha256-generation-7",
        "persistence_receipt_id": "apr-generation-7",
        "currentness_ref": "head:7",
        "current_live_index_revision": "index:9",
        "canonical_artifact_index_owner_ref": "artifact-index-owner:canonical",
        "canonical_store_ref": "artifact-index-store:primary",
        "readback_ref": "artifact-index-readback:9",
        "readback_verified": True,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    row.update(overrides)
    row["evidence_digest"] = fence.generation_evidence_digest(row)
    return row


def generation_resolver(evidence):
    def resolve(project_id, persisted_surface, resource_ref):
        self_key = (project_id, persisted_surface, resource_ref)
        if self_key != ("P1", "google_drive", "drive:file:1"):
            raise AssertionError(self_key)
        return dict(evidence)
    return resolve


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
    row["receipt_digest"] = core.compute_workgraph_transition_receipt_digest(row)
    return row


def transition_evidence(receipt):
    return {
        "schema": "CanonicalWorkGraphTransitionEvidenceV1",
        "status": "VERIFIED_PERSISTED_TRANSITION",
        "transition_receipt_digest": receipt["receipt_digest"],
        "project_id": "P1",
        "cell_id": "C1",
        "currentness_ref": "head:7",
        "basis_graph_digest": "graph:before",
        "before_state_digest": "state:before",
        "after_state_digest": "state:after",
        "after_graph_digest": "graph:after",
        "canonical_workgraph_owner_ref": "workgraph-owner:canonical",
        "canonical_store_ref": "workgraph-store:primary",
        "persistence_verification_ref": "workgraph-persist:1",
        "readback_ref": "workgraph-readback:1",
        "persistence_verified": True,
        "readback_verified": True,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }


def transition_resolver(evidence):
    expected = evidence["transition_receipt_digest"]
    return lambda receipt_digest: dict(evidence) if receipt_digest == expected else None


class ArtifactGenerationFencedWakeBridgeTests(unittest.TestCase):
    def proposal(self, *, event=None, evidence=None):
        event = event or artifact_event()
        evidence = evidence or generation_evidence()
        return fence.compile_generation_fenced_proposal(
            artifact_event=event,
            binding=binding(),
            workgraph_projection=before_projection(),
            canonical_generation_resolver=generation_resolver(evidence),
        )

    def test_current_generation_compiles_non_authorizing_reopen_proposal(self):
        proposal = self.proposal()
        self.assertEqual(7, proposal.source_event_generation)
        self.assertEqual("index:9", proposal.generation_evidence_index_revision)
        self.assertFalse(proposal.wake_scan_allowed)
        self.assertFalse(proposal.execution_authorized)
        self.assertFalse(proposal.effect_authorized)

    def test_stale_artifact_generation_cannot_compile_reopen(self):
        evidence = generation_evidence(resource_generation=8, artifact_sid="artifact-sha256-generation-8", persistence_receipt_id="apr-generation-8")
        with self.assertRaises(fence.GenerationFenceError) as ctx:
            self.proposal(evidence=evidence)
        self.assertEqual("ARTIFACT_GENERATION_STALE", ctx.exception.code)

    def test_same_artifact_identity_with_wrong_generation_still_fails(self):
        evidence = generation_evidence(resource_generation=8)
        with self.assertRaises(fence.GenerationFenceError) as ctx:
            self.proposal(evidence=evidence)
        self.assertEqual("ARTIFACT_GENERATION_STALE", ctx.exception.code)

    def test_resource_head_artifact_must_match(self):
        evidence = generation_evidence(artifact_sid="different-artifact")
        with self.assertRaises(fence.GenerationFenceError) as ctx:
            self.proposal(evidence=evidence)
        self.assertEqual("RESOURCE_HEAD_ARTIFACT_MISMATCH", ctx.exception.code)

    def test_generation_evidence_digest_is_verified(self):
        evidence = generation_evidence()
        evidence["evidence_digest"] = "wrong"
        with self.assertRaises(fence.GenerationFenceError) as ctx:
            self.proposal(evidence=evidence)
        self.assertEqual("GENERATION_EVIDENCE_DIGEST_MISMATCH", ctx.exception.code)

    def test_global_live_index_can_advance_if_resource_generation_is_still_current(self):
        evidence = generation_evidence(current_live_index_revision="index:999")
        proposal = self.proposal(evidence=evidence)
        self.assertEqual("index:999", proposal.generation_evidence_index_revision)
        self.assertEqual(7, proposal.source_event_generation)

    def test_generation_advance_during_workgraph_transition_blocks_wake_scan(self):
        first = generation_evidence()
        later = generation_evidence(
            resource_generation=8,
            artifact_sid="artifact-sha256-generation-8",
            persistence_receipt_id="apr-generation-8",
            current_live_index_revision="index:10",
        )
        calls = [first, later]

        def resolver(project_id, persisted_surface, resource_ref):
            return dict(calls.pop(0))

        proposal = fence.compile_generation_fenced_proposal(
            artifact_event=artifact_event(), binding=binding(), workgraph_projection=before_projection(),
            canonical_generation_resolver=resolver,
        )
        receipt = transition_receipt()
        with self.assertRaises(fence.GenerationFenceError) as ctx:
            fence.verify_generation_fenced_reopen(
                fenced_proposal=proposal,
                artifact_event=artifact_event(),
                transition_receipt=receipt,
                after_projection=after_projection(),
                canonical_transition_resolver=transition_resolver(transition_evidence(receipt)),
                canonical_generation_resolver=resolver,
            )
        self.assertEqual("ARTIFACT_GENERATION_STALE", ctx.exception.code)

    def test_persisted_reopen_plus_current_generation_allows_existing_scanner_only(self):
        evidence = generation_evidence()
        proposal = self.proposal(evidence=evidence)
        receipt = transition_receipt()
        result = fence.verify_generation_fenced_reopen(
            fenced_proposal=proposal,
            artifact_event=artifact_event(),
            transition_receipt=receipt,
            after_projection=after_projection(),
            canonical_transition_resolver=transition_resolver(transition_evidence(receipt)),
            canonical_generation_resolver=generation_resolver(evidence),
        )
        self.assertEqual("GENERATION_CURRENT_POST_TRANSITION_WAKE_SCAN_ALLOWED", result["decision"])
        self.assertEqual(7, result["source_event_generation"])
        self.assertFalse(result["wake_intent_emitted"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["provider_calls_authorized"])
        self.assertFalse(result["runtime_execution_proven"])
        self.assertFalse(result["background_execution_claimed"])


if __name__ == "__main__":
    unittest.main()
