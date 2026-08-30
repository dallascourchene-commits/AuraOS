import unittest

from aura_arena_workgraph import apply_action, project_workgraph
import mission_completion_evidence_firewall as m

WORKER = "worker-1"
CELL = "cell-1"
MISSION = "mission:test"
CURRENT = "current:1"
CANDIDATE = "candidate://artifact-1"
CANDIDATE_DIGEST = "c" * 64


def base_state():
    return {
        "schema": "AuraArenaWorkGraphStateV1",
        "project_id": "project-1",
        "mission_ref": MISSION,
        "canonical_orientation_ref": "front-door:test",
        "board_ref": "board:test",
        "board_revision": "board-rev:1",
        "route_policy_ref": "route:1",
        "source_digests": ["sha256:source"],
        "currentness_ref": CURRENT,
        "workers": [{
            "worker_id": WORKER,
            "worker_class": "CHATGPT",
            "capabilities": ["reasoning"],
            "currentness_ref": CURRENT,
            "joined": True,
            "state": "IDLE",
            "effect_ceiling": "D0",
            "eligible": True,
        }],
        "cells": [{
            "cell_id": CELL,
            "parent_objective": "test completion",
            "state": "OPEN",
            "priority": "P0",
            "dependencies": [],
            "required_capabilities": ["reasoning"],
            "effect_class": "D0",
            "reuse_value": 1,
            "estimated_effort": 1,
            "cost_ceiling_provider_usd": 0.0,
            "free_first_route": ["R1_LOCAL_DETERMINISTIC"],
            "expected_output": "artifact",
            "acceptance": ["mission policy satisfied"],
            "currentness_ref": CURRENT,
            "reopen_conditions": ["currentness change"],
            "execution_state": "NOT_STARTED",
            "execution_receipt_refs": [],
            "blocker_reason": "",
        }],
        "claims": [],
    }


def claimed_state(now_ms=1000):
    state = base_state()
    p = project_workgraph(state, now_ms=now_ms)
    state, _ = apply_action(
        state,
        action={
            "action": "CLAIM",
            "basis_graph_digest": p["graph_digest"],
            "cell_id": CELL,
            "worker_id": WORKER,
            "lease_ms": 10000,
        },
        now_ms=now_ms,
    )
    return state


def policy(**changes):
    values = dict(
        policy_ref="mission-policy://completion-v1",
        policy_generation="policy-gen:1",
        policy_currentness_ref="policy-current:1",
        project_id="project-1",
        mission_ref=MISSION,
        cell_id=CELL,
        workgraph_currentness_ref=CURRENT,
        candidate_ref=CANDIDATE,
        candidate_digest=CANDIDATE_DIGEST,
        trusted_attestation_issuer_refs=("mission-evidence-owner://1",),
        allows_not_required=False,
        requires_execution_verification=False,
    )
    values.update(changes)
    return m.MissionCompletionPolicyBindingV1(**values)


def attestation(state=None, now_ms=1000, **changes):
    state = state or claimed_state(now_ms)
    p = project_workgraph(state, now_ms=now_ms)
    cell = next(c for c in p["cells"] if c["cell_id"] == CELL)
    claim = next(c for c in cell["active_claims"] if c["worker_id"] == WORKER)
    values = dict(
        issuer_ref="mission-evidence-owner://1",
        issuer_generation="issuer-gen:1",
        policy_ref="mission-policy://completion-v1",
        policy_generation="policy-gen:1",
        policy_currentness_ref="policy-current:1",
        project_id="project-1",
        mission_ref=MISSION,
        cell_id=CELL,
        claim_id=claim["claim_id"],
        worker_id=WORKER,
        graph_digest=p["graph_digest"],
        currentness_ref=CURRENT,
        candidate_ref=CANDIDATE,
        candidate_digest=CANDIDATE_DIGEST,
        acceptance_refs=("accept://1",),
        output_refs=("output://1",),
        evidence_refs=("evidence://mission-owner/1",),
        evidence_digests=("e" * 64,),
        evidence_domain=m.EvidenceDomain.MISSION_COMPLETION,
        disposition=m.CompletionDisposition.SATISFIED,
    )
    values.update(changes)
    return m.MissionCompletionAttestationV1(**values)


def admit(state=None, p=None, a=None, now_ms=1000):
    state = state or claimed_state(now_ms)
    projection = project_workgraph(state, now_ms=now_ms)
    return m.admit_mission_completion(
        projection=projection,
        policy=p or policy(),
        attestation=a or attestation(state, now_ms),
        worker_id=WORKER,
        cell_id=CELL,
        acceptance_refs=("accept://1",),
        output_refs=("output://1",),
    )


class MissionCompletionEvidenceFirewallTests(unittest.TestCase):
    def test_exact_mission_completion_attestation_admitted_zero_authority(self):
        result = admit()
        self.assertTrue(result["coordination_complete_preflight_pass"])
        self.assertEqual("MISSION_COMPLETION", result["evidence_domain"])
        self.assertFalse(result["execution_verified_by_this_module"])
        self.assertFalse(result["review_pass_proven"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["promotion_authorized"])
        self.assertFalse(result["policy_resolution_proven_by_this_module"])

    def test_review_adjudication_cannot_complete_mission(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, evidence_domain=m.EvidenceDomain.REVIEW_ADJUDICATION))
        self.assertEqual("COMPLETION_EVIDENCE_DOMAIN_MISMATCH", cm.exception.code)

    def test_review_context_cache_cannot_complete_mission(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, evidence_domain=m.EvidenceDomain.REVIEW_CONTEXT))
        self.assertEqual("COMPLETION_EVIDENCE_DOMAIN_MISMATCH", cm.exception.code)

    def test_model_prefix_kv_cannot_complete_mission(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, evidence_domain=m.EvidenceDomain.MODEL_PREFIX_KV))
        self.assertEqual("COMPLETION_EVIDENCE_DOMAIN_MISMATCH", cm.exception.code)

    def test_untrusted_attestation_issuer_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, issuer_ref="caller://self-minted"))
        self.assertEqual("COMPLETION_ATTESTATION_ISSUER_UNTRUSTED", cm.exception.code)

    def test_stale_graph_digest_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, graph_digest="stale-graph"))
        self.assertEqual("COMPLETION_GRAPH_STALE", cm.exception.code)

    def test_stale_currentness_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, currentness_ref="current:old"))
        self.assertEqual("COMPLETION_CURRENTNESS_STALE", cm.exception.code)

    def test_policy_stale_to_workgraph_currentness_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, p=policy(workgraph_currentness_ref="current:old"))
        self.assertEqual("COMPLETION_POLICY_CURRENTNESS_STALE", cm.exception.code)

    def test_policy_wrong_cell_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, p=policy(cell_id="cell-other"))
        self.assertEqual("COMPLETION_POLICY_CELL_MISMATCH", cm.exception.code)

    def test_candidate_ref_and_digest_are_policy_bound(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, candidate_ref="candidate://other"))
        self.assertEqual("COMPLETION_CANDIDATE_REF_MISMATCH", cm.exception.code)
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, candidate_digest="d" * 64))
        self.assertEqual("COMPLETION_CANDIDATE_DIGEST_MISMATCH", cm.exception.code)

    def test_wrong_claim_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, claim_id="claim:wrong"))
        self.assertEqual("COMPLETION_CLAIM_MISMATCH", cm.exception.code)

    def test_acceptance_ref_mismatch_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, acceptance_refs=("accept://other",)))
        self.assertEqual("COMPLETION_ACCEPTANCE_REFS_MISMATCH", cm.exception.code)

    def test_blocked_attestation_refused(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=attestation(state, disposition=m.CompletionDisposition.BLOCKED))
        self.assertEqual("MISSION_COMPLETION_BLOCKED", cm.exception.code)

    def test_not_required_must_be_explicitly_allowed_by_policy(self):
        state = claimed_state()
        a = attestation(state, disposition=m.CompletionDisposition.NOT_REQUIRED)
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, a=a)
        self.assertEqual("MISSION_COMPLETION_NOT_REQUIRED_NOT_ALLOWED", cm.exception.code)
        result = admit(state=state, p=policy(allows_not_required=True), a=a)
        self.assertEqual("NOT_REQUIRED", result["disposition"])

    def test_execution_requirement_remains_orthogonal(self):
        state = claimed_state()
        with self.assertRaises(m.CompletionEvidenceError) as cm:
            admit(state=state, p=policy(requires_execution_verification=True))
        self.assertEqual("REQUIRED_EXECUTION_VERIFICATION_MISSING", cm.exception.code)

    def test_attestation_cannot_self_assert_execution_review_or_effect(self):
        state = claimed_state()
        for field in ("execution_verified", "review_pass_proven", "effect_authorized"):
            with self.assertRaises(m.CompletionEvidenceError) as cm:
                attestation(state, **{field: True})
            self.assertEqual("ATTESTATION_AUTHORITY_WIDENING", cm.exception.code)

    def test_transition_request_stops_before_raw_workgraph_mutation(self):
        state = claimed_state()
        a = attestation(state)
        request = m.compile_terminal_completion_request(
            state,
            policy=policy(),
            attestation=a,
            worker_id=WORKER,
            cell_id=CELL,
            acceptance_refs=("accept://1", "accept://1"),
            output_refs=("output://1", "output://1"),
            now_ms=1000,
        )
        self.assertEqual("COMPLETE", request["action"])
        self.assertEqual(("accept://1",), request["acceptance_refs"])
        self.assertEqual(("output://1",), request["output_refs"])
        self.assertTrue(request["raw_workgraph_v1_complete_bypass_unrepaired"])
        self.assertFalse(request["execution_state_mutation_authorized"])
        projection = project_workgraph(state, now_ms=1000)
        cell = next(c for c in projection["cells"] if c["cell_id"] == CELL)
        self.assertEqual("CLAIMED", cell["effective_state"])
        self.assertEqual("NOT_STARTED", cell["execution_state"])

    def test_policy_generation_changes_request_identity(self):
        state = claimed_state()
        req1 = m.compile_terminal_completion_request(
            state, policy=policy(), attestation=attestation(state), worker_id=WORKER, cell_id=CELL,
            acceptance_refs=("accept://1",), output_refs=("output://1",), now_ms=1000,
        )
        req2 = m.compile_terminal_completion_request(
            state,
            policy=policy(policy_generation="policy-gen:2"),
            attestation=attestation(state, policy_generation="policy-gen:2"),
            worker_id=WORKER,
            cell_id=CELL,
            acceptance_refs=("accept://1",),
            output_refs=("output://1",),
            now_ms=1000,
        )
        self.assertNotEqual(req1["request_digest"], req2["request_digest"])


if __name__ == "__main__":
    unittest.main()
