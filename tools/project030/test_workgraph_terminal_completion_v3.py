import unittest

from aura_arena_workgraph import apply_action, project_workgraph
from workgraph_terminal_completion_v3 import (
    AxisDisposition,
    AxisPolicyV3,
    TerminalCompletionError,
    WorkGraphAxisAttestationV3,
    WorkGraphCompletionPolicyV3,
    apply_terminal_completion_v3,
)

WORKER = "W-GHR014"
CELL = "GHR-014"
MISSION = "mission:review-harness"
CURRENT = "current:ghr014"
CANDIDATE = "candidate:exact"
CANDIDATE_DIGEST = "a" * 64


def base_state():
    return {
        "schema": "AuraArenaWorkGraphStateV1",
        "project_id": "AURA-REVIEW-HARNESS",
        "mission_ref": MISSION,
        "canonical_orientation_ref": "front-door:review-harness",
        "board_ref": "drive:review-board",
        "board_revision": "rev:1",
        "route_policy_ref": "route:free-first",
        "source_digests": ["sha256:source"],
        "currentness_ref": CURRENT,
        "workers": [{
            "worker_id": WORKER,
            "worker_class": "CHATGPT",
            "capabilities": ["reasoning"],
            "currentness_ref": CURRENT,
            "joined": True,
            "state": "ACTIVE",
            "effect_ceiling": "D0",
            "eligible": True,
        }],
        "cells": [{
            "cell_id": CELL,
            "parent_objective": "integrate terminal evidence",
            "state": "OPEN",
            "priority": "P0",
            "dependencies": [],
            "required_capabilities": ["reasoning"],
            "effect_class": "D0",
            "reuse_value": 10,
            "estimated_effort": 1,
            "cost_ceiling_provider_usd": 0.0,
            "free_first_route": ["R1_LOCAL_DETERMINISTIC"],
            "expected_output": "terminal receipt",
            "acceptance": ["mission", "execution", "quality"],
            "currentness_ref": CURRENT,
            "reopen_conditions": ["policy changes"],
            "execution_state": "NOT_STARTED",
            "execution_receipt_refs": [],
            "blocker_reason": "",
        }],
        "claims": [],
    }


def claimed_state(now_ms=1000):
    state = base_state()
    p = project_workgraph(state, now_ms=now_ms)
    claimed, _ = apply_action(
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
    return claimed


def axis_policy(axis, *, required=True, evidence_domain=None):
    return AxisPolicyV3(
        axis=axis,
        responsibility_class=f"{axis}_OWNER_BACKED",
        evidence_domain=evidence_domain or f"{axis}_EVIDENCE",
        owner_ref=f"owner:{axis.lower()}",
        owner_generation="gen:1",
        owner_currentness_ref=CURRENT,
        trusted_issuer_refs=(f"issuer:{axis.lower()}",),
        required=required,
    )


def policy(*, execution_required=False):
    return WorkGraphCompletionPolicyV3(
        policy_ref="policy:completion-v3",
        policy_generation="pg:1",
        policy_currentness_ref=CURRENT,
        project_id="AURA-REVIEW-HARNESS",
        mission_ref=MISSION,
        cell_id=CELL,
        workgraph_currentness_ref=CURRENT,
        candidate_ref=CANDIDATE,
        candidate_digest=CANDIDATE_DIGEST,
        axes=(
            axis_policy("MISSION"),
            axis_policy("EXECUTION", required=execution_required),
            axis_policy("QUALITY"),
        ),
    )


def attestations(state, pol, *, execution=AxisDisposition.NOT_REQUIRED, mutate=None, now_ms=1000):
    projection = project_workgraph(state, now_ms=now_ms)
    cell = next(c for c in projection["cells"] if c["cell_id"] == CELL)
    claim = next(c for c in cell["active_claims"] if c["worker_id"] == WORKER)
    rows = []
    by_axis = {x.axis: x for x in pol.axes}
    for axis in ("MISSION", "EXECUTION", "QUALITY"):
        ap = by_axis[axis]
        disposition = execution if axis == "EXECUTION" else AxisDisposition.SATISFIED
        values = dict(
            axis=axis,
            responsibility_class=ap.responsibility_class,
            evidence_domain=ap.evidence_domain,
            owner_ref=ap.owner_ref,
            owner_generation=ap.owner_generation,
            owner_currentness_ref=ap.owner_currentness_ref,
            issuer_ref=ap.trusted_issuer_refs[0],
            issuer_generation="issuer-gen:1",
            policy_ref=pol.policy_ref,
            policy_generation=pol.policy_generation,
            policy_currentness_ref=pol.policy_currentness_ref,
            project_id=pol.project_id,
            mission_ref=pol.mission_ref,
            cell_id=CELL,
            claim_id=claim["claim_id"],
            worker_id=WORKER,
            graph_digest=projection["graph_digest"],
            currentness_ref=CURRENT,
            candidate_ref=CANDIDATE,
            candidate_digest=CANDIDATE_DIGEST,
            acceptance_refs=("accept:1",),
            output_refs=("output:1",),
            evidence_refs=(f"evidence:{axis.lower()}",),
            evidence_digests=(({"MISSION":"1", "EXECUTION":"2", "QUALITY":"3"}[axis]) * 64,),
            disposition=disposition,
        )
        if mutate and mutate[0] == axis:
            values[mutate[1]] = mutate[2]
        rows.append(WorkGraphAxisAttestationV3(**values))
    return tuple(rows)


def action(state, now_ms=1000):
    p = project_workgraph(state, now_ms=now_ms)
    return {
        "action": "COMPLETE",
        "basis_graph_digest": p["graph_digest"],
        "cell_id": CELL,
        "worker_id": WORKER,
        "acceptance_refs": ["accept:1"],
        "output_refs": ["output:1"],
    }


class TerminalCompletionV3Tests(unittest.TestCase):
    def test_valid_nonexecution_terminal_completion_does_not_mint_verified_execution(self):
        state = claimed_state()
        pol = policy(execution_required=False)
        rows = attestations(state, pol)
        next_state, receipt = apply_terminal_completion_v3(
            state, action=action(state), policy=pol, attestations=rows, now_ms=1000
        )
        cell = next(c for c in next_state["cells"] if c["cell_id"] == CELL)
        self.assertEqual("COMPLETE", cell["state"])
        self.assertEqual("NOT_STARTED", cell["execution_state"])
        self.assertEqual([], cell["execution_receipt_refs"])
        self.assertFalse(receipt["execution_axis_satisfied"])
        self.assertTrue(receipt["owner_integration_required"])
        self.assertFalse(receipt["effect_authorized"])

    def test_required_execution_axis_can_verify_execution_only_from_execution_evidence(self):
        state = claimed_state()
        pol = policy(execution_required=True)
        rows = attestations(state, pol, execution=AxisDisposition.SATISFIED)
        next_state, receipt = apply_terminal_completion_v3(
            state, action=action(state), policy=pol, attestations=rows, now_ms=1000
        )
        cell = next(c for c in next_state["cells"] if c["cell_id"] == CELL)
        self.assertEqual("VERIFIED_COMPLETE", cell["execution_state"])
        self.assertEqual(["evidence:execution"], cell["execution_receipt_refs"])
        self.assertTrue(receipt["execution_axis_satisfied"])

    def test_required_execution_axis_cannot_be_not_required(self):
        state = claimed_state()
        pol = policy(execution_required=True)
        rows = attestations(state, pol, execution=AxisDisposition.NOT_REQUIRED)
        with self.assertRaisesRegex(TerminalCompletionError, "REQUIRED_AXIS_NOT_SATISFIED:EXECUTION"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_quality_cannot_cast_into_mission_domain(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("QUALITY", "evidence_domain", "MISSION_EVIDENCE"))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_EVIDENCE_DOMAIN_MISMATCH:QUALITY"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_untrusted_axis_issuer_refused(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("MISSION", "issuer_ref", "issuer:attacker"))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_ISSUER_UNTRUSTED:MISSION"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_stale_graph_attestation_refused(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("QUALITY", "graph_digest", "stale:graph"))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_TARGET_BINDING_MISMATCH:QUALITY"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_candidate_digest_mismatch_refused(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("MISSION", "candidate_digest", "b" * 64))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_TARGET_BINDING_MISMATCH:MISSION"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_acceptance_ref_mismatch_refused(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("MISSION", "acceptance_refs", ("accept:other",)))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_TARGET_BINDING_MISMATCH:MISSION"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_axis_owner_generation_mismatch_refused(self):
        state = claimed_state()
        pol = policy()
        rows = attestations(state, pol, mutate=("QUALITY", "owner_generation", "gen:stale"))
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_OWNER_BINDING_MISMATCH:QUALITY"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=rows, now_ms=1000)

    def test_blocked_axis_refuses_terminal_completion(self):
        state = claimed_state()
        pol = policy()
        rows = list(attestations(state, pol))
        q = rows[2]
        values = q.__dict__.copy()
        values["disposition"] = AxisDisposition.BLOCKED
        rows[2] = WorkGraphAxisAttestationV3(**values)
        with self.assertRaisesRegex(TerminalCompletionError, "AXIS_BLOCKED:QUALITY"):
            apply_terminal_completion_v3(state, action=action(state), policy=pol, attestations=tuple(rows), now_ms=1000)

    def test_policy_requires_exact_three_distinct_axes(self):
        with self.assertRaisesRegex(TerminalCompletionError, "POLICY_AXIS_SET_INVALID"):
            WorkGraphCompletionPolicyV3(
                policy_ref="policy:x", policy_generation="g", policy_currentness_ref=CURRENT,
                project_id="AURA-REVIEW-HARNESS", mission_ref=MISSION, cell_id=CELL,
                workgraph_currentness_ref=CURRENT, candidate_ref=CANDIDATE,
                candidate_digest=CANDIDATE_DIGEST,
                axes=(axis_policy("MISSION"), axis_policy("MISSION"), axis_policy("QUALITY")),
            )

    def test_raw_v1_complete_remains_explicit_owner_integration_blocker(self):
        state = claimed_state()
        legacy_next, _ = apply_action(state, action=action(state), now_ms=1000)
        cell = next(c for c in legacy_next["cells"] if c["cell_id"] == CELL)
        self.assertEqual("COMPLETE", cell["state"])
        self.assertEqual("VERIFIED_COMPLETE", cell["execution_state"])
        self.assertEqual(["accept:1", "output:1"], cell["execution_receipt_refs"])
        # This passing test documents why this child cannot claim the canonical V1
        # owner repaired until PR #323 absorbs/retargets the V3 seam.


if __name__ == "__main__":
    unittest.main()
