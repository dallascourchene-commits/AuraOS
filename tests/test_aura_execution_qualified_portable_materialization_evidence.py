#!/usr/bin/env python3
import json
from pathlib import Path
import unittest

from tools.quantization import aura_execution_qualified_portable_materialization_evidence as q15

FIXTURE = Path(__file__).parent / "fixtures" / "q14_official_source_e8_materialization_receipt.json"


def run(run_id, head, workflow):
    return {"id": run_id, "head_sha": head, "name": workflow, "status": "completed", "conclusion": "success"}


def jobs(run_id, job_id):
    return {"jobs": [{"id": job_id, "run_id": run_id, "status": "completed", "conclusion": "success"}]}


def generations():
    return {
        "a7": {"head": q15.A7_SEMANTIC_HEAD, "generated_at": q15.A7_SEMANTIC_GENERATED_AT, "ancestor_of": q15.A7_HEAD, "ancestor_proven": True},
        "q14": {"head": q15.Q14_SEMANTIC_HEAD, "generated_at": q15.Q14_SEMANTIC_GENERATED_AT, "ancestor_of": q15.Q14_HEAD, "ancestor_proven": True},
    }


def admit(**overrides):
    args = dict(
        q14_raw=FIXTURE.read_bytes(),
        q14_artifact_digest=q15.Q14_ARTIFACT_DIGEST,
        convergence_parents=[q15.Q14_HEAD, q15.A7_HEAD],
        generation_evidence=generations(),
        a7_run=run(q15.A7_RUN, q15.A7_HEAD, q15.A7_WORKFLOW),
        a7_jobs=jobs(q15.A7_RUN, q15.A7_JOB),
        q14_run=run(q15.Q14_RUN, q15.Q14_HEAD, q15.Q14_WORKFLOW),
        q14_jobs=jobs(q15.Q14_RUN, q15.Q14_JOB),
    )
    args.update(overrides)
    return q15.admit(**args)


class Q15Contract(unittest.TestCase):
    def test_exact_fixture_admits_all_eight_lattice_axes(self):
        r = admit()
        self.assertTrue(r.execution_qualified_portable_materialization_evidence)
        self.assertTrue(all([r.c0_parent_identity, r.c1_source_slice_identity, r.c2_page_consequence, r.c3_portability_integrity, r.c4_provider_execution, r.c5_semantic_freshness, r.c6_nonpromotion_invalidation, r.c7_claim_ceiling]))
        self.assertEqual(r.hyperscale_level, "HS1")

    def test_wrong_parent_fails_closed(self):
        r = admit(convergence_parents=[q15.Q14_HEAD, "0"*40])
        self.assertFalse(r.execution_qualified_portable_materialization_evidence)
        self.assertEqual(r.reason, "EXACT_TWO_PARENT_DIAMOND_NOT_BOUND")

    def test_artifact_digest_substitution_fails(self):
        r = admit(q14_artifact_digest="sha256:" + "0"*64)
        self.assertFalse(r.c3_portability_integrity)

    def test_page_mutation_fails_file_and_receipt_integrity(self):
        payload = json.loads(FIXTURE.read_text())
        payload["role_canaries"][0]["page_payload_sha256"] = "0"*64
        raw = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
        r = admit(q14_raw=raw)
        self.assertFalse(r.c2_page_consequence)
        self.assertFalse(r.c3_portability_integrity)

    def test_successful_run_label_without_exact_job_fails(self):
        r = admit(a7_jobs={"jobs": []})
        self.assertFalse(r.c4_provider_execution)

    def test_executed_failure_fails(self):
        bad = jobs(q15.Q14_RUN, q15.Q14_JOB)
        bad["jobs"][0]["conclusion"] = "failure"
        r = admit(q14_jobs=bad)
        self.assertFalse(r.c4_provider_execution)

    def test_caller_time_without_generation_authentication_fails(self):
        g = generations()
        g["a7"]["ancestor_proven"] = False
        r = admit(generation_evidence=g)
        self.assertFalse(r.c5_semantic_freshness)

    def test_replay_cannot_promote_claims(self):
        r = admit()
        self.assertFalse(r.page_existence_implies_execution)
        self.assertFalse(r.execution_implies_page_identity)
        self.assertFalse(r.portability_resets_semantic_clock)
        self.assertFalse(r.replay_mints_successor_novelty)
        self.assertFalse(r.k27_coordinate_is_semantic_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)
        self.assertFalse(r.full_representative_page_set_proven)
        self.assertFalse(r.model_execution_proven)
        self.assertFalse(r.inference_proven)
        self.assertFalse(r.generalized_quality_or_performance_proven)
        self.assertFalse(r.merge_or_deployment_authorized)


if __name__ == "__main__":
    unittest.main()
