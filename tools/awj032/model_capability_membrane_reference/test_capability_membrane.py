from __future__ import annotations

import itertools
import random
import unittest

from capability_membrane import (
    AdapterIdentity,
    CapabilityRequest,
    Decision,
    ExternalEvidenceCard,
    GLM_PREFETCH_IMPLEMENTATION,
    ModelFamily,
    Operation,
    PrefetchContract,
    RuntimeProof,
    SourceBinding,
    admit,
)


def source(current=True):
    return SourceBinding(
        model_revision="model@sha256:abc",
        airllm_revision="55e435087d951da8c25ab3672e969025241a398e",
        topology_root="topology:123",
        tokenizer_root="tokenizer:456",
        current=current,
    )


def runtime(current=True):
    return RuntimeProof("workcell:1", "attempt:1", "runtime:g1", current)


def qwen_adapter(exact=True, verified=True):
    return AdapterIdentity(
        "AirLLMLoRA(AirLLMQwen3_5)" if exact else "AirLLMLoRAQwen4Exp(AirLLMQwen4Exp)",
        "adapter:aaa",
        "base:bbb",
        verified,
    )


def glm_prefetch(router_ok=True):
    return PrefetchContract(
        GLM_PREFETCH_IMPLEMENTATION,
        "glm-router:g1",
        "pager:source-bound",
        prediction_owns_transfer_only=router_ok,
        native_route_owns_execution=router_ok,
    )


class CapabilityMembraneTests(unittest.TestCase):
    def test_qwen_training_admits_only_exact_current_runtime_and_adapter(self):
        req = CapabilityRequest(
            ModelFamily.QWEN3_8_DENSE,
            Operation.STREAMED_TRAINING,
            source(), runtime(), qwen_adapter(), None,
        )
        self.assertEqual(admit(req).decision, Decision.ADMIT_D0)

    def test_glm_training_stays_hold_even_with_qwen_runtime_and_adapter(self):
        req = CapabilityRequest(
            ModelFamily.GLM_5_3,
            Operation.STREAMED_TRAINING,
            source(), runtime(), qwen_adapter(), None,
        )
        self.assertEqual(admit(req).decision, Decision.HOLD_PORT_REQUIRED)

    def test_glm_prefetch_admits_only_router_separated_contract(self):
        good = CapabilityRequest(
            ModelFamily.GLM_5_3,
            Operation.INFERENCE_PREFETCH,
            source(), None, None, glm_prefetch(True),
        )
        bad = CapabilityRequest(
            ModelFamily.GLM_5_3,
            Operation.INFERENCE_PREFETCH,
            source(), None, None, glm_prefetch(False),
        )
        self.assertEqual(admit(good).decision, Decision.ADMIT_D0)
        self.assertEqual(admit(bad).decision, Decision.HOLD_ROUTER_SEPARATION)

    def test_external_evidence_never_mints_authority_or_admission(self):
        card = ExternalEvidenceCard(
            "ext://airllm/training/2026-09",
            "https://github.com/lyogavin/airllm",
            "2026-09-07",
            "AirLLM documents streamed Qwen training",
            "PUBLIC_UPSTREAM",
        )
        held = CapabilityRequest(
            ModelFamily.GLM_5_3,
            Operation.STREAMED_TRAINING,
            source(), runtime(), qwen_adapter(), None,
        )
        receipt = admit(held, [card])
        self.assertEqual(receipt.decision, Decision.HOLD_PORT_REQUIRED)
        self.assertEqual(receipt.authority_ceiling, "D0_NONPROMOTING")
        self.assertNotEqual(receipt.external_evidence_digest, "")

    def test_y13_is_x12_plus_derived_witness(self):
        req = CapabilityRequest(
            ModelFamily.GLM_5_3,
            Operation.INFERENCE_PREFETCH,
            source(), None, None, glm_prefetch(True),
        )
        a = admit(req)
        b = admit(req)
        self.assertEqual(len(a.y13), 13)
        self.assertEqual(a.y13, b.y13)
        self.assertEqual(len(a.y13[-1]), 64)

    def test_operation_root_changes_on_consequence_bearing_identity_change(self):
        a = CapabilityRequest(ModelFamily.QWEN3_8_DENSE, Operation.STREAMED_TRAINING, source(), runtime(), qwen_adapter(), None)
        b = CapabilityRequest(ModelFamily.QWEN3_8_DENSE, Operation.STREAMED_TRAINING, source(), RuntimeProof("workcell:1", "attempt:2", "runtime:g1", True), qwen_adapter(), None)
        self.assertNotEqual(admit(a).operation_root, admit(b).operation_root)

    def test_eight_corner_crystalline_lattice_qwen_training(self):
        # 2^3 adversarial crystal: source current × runtime current × adapter exact.
        outcomes = {}
        for source_ok, runtime_ok, adapter_ok in itertools.product([False, True], repeat=3):
            req = CapabilityRequest(
                ModelFamily.QWEN3_8_DENSE,
                Operation.STREAMED_TRAINING,
                source(source_ok), runtime(runtime_ok), qwen_adapter(adapter_ok), None,
            )
            outcomes[(source_ok, runtime_ok, adapter_ok)] = admit(req).decision
        self.assertEqual(sum(v is Decision.ADMIT_D0 for v in outcomes.values()), 1)
        self.assertEqual(outcomes[(True, True, True)], Decision.ADMIT_D0)

    def test_eight_corner_crystalline_lattice_glm_prefetch(self):
        # 2^3: source current × transfer-only × native-execution-owned.
        outcomes = {}
        for source_ok, transfer_only, native_owned in itertools.product([False, True], repeat=3):
            p = PrefetchContract(
                GLM_PREFETCH_IMPLEMENTATION,
                "glm-router:g1",
                "pager:source-bound",
                transfer_only,
                native_owned,
            )
            req = CapabilityRequest(ModelFamily.GLM_5_3, Operation.INFERENCE_PREFETCH, source(source_ok), None, None, p)
            outcomes[(source_ok, transfer_only, native_owned)] = admit(req).decision
        self.assertEqual(sum(v is Decision.ADMIT_D0 for v in outcomes.values()), 1)
        self.assertEqual(outcomes[(True, True, True)], Decision.ADMIT_D0)

    def test_hyperscale_1000_frozen_cases_no_unsafe_glm_training_admission(self):
        rng = random.Random(530032)
        families = list(ModelFamily)
        decisions = set()
        glm_training = 0
        glm_training_admitted = 0
        for i in range(1000):
            fam = rng.choice(families)
            op = rng.choice(list(Operation))
            s = source(rng.choice([True, False]))
            r = runtime(rng.choice([True, False])) if rng.choice([True, False]) else None
            a = qwen_adapter(rng.choice([True, False]), rng.choice([True, False])) if rng.choice([True, False]) else None
            p = glm_prefetch(rng.choice([True, False])) if rng.choice([True, False]) else None
            req = CapabilityRequest(fam, op, s, r, a, p)
            result = admit(req)
            decisions.add(result.decision)
            if fam is ModelFamily.GLM_5_3 and op is Operation.STREAMED_TRAINING:
                glm_training += 1
                glm_training_admitted += result.decision is Decision.ADMIT_D0
            self.assertEqual(len(result.y13), 13)
            self.assertTrue(all(v in (-1, 1) for v in result.k27))
        self.assertGreater(glm_training, 0)
        self.assertEqual(glm_training_admitted, 0)
        self.assertGreaterEqual(len(decisions), 5)

    def test_external_kv_order_does_not_change_admission_or_digest(self):
        cards = [
            ExternalEvidenceCard("ext://research/cache-router", "https://arxiv.org/abs/2609.04895", "2026-09-07", "cache-aware MoE", "ARXIV"),
            ExternalEvidenceCard("ext://airllm/qwen-training", "https://github.com/lyogavin/airllm", "2026-09-07", "Qwen streamed LoRA", "UPSTREAM"),
        ]
        req = CapabilityRequest(ModelFamily.GLM_5_3, Operation.STREAMED_TRAINING, source(), runtime(), qwen_adapter(), None)
        a = admit(req, cards)
        b = admit(req, reversed(cards))
        self.assertEqual(a.decision, b.decision)
        self.assertEqual(a.external_evidence_digest, b.external_evidence_digest)


if __name__ == "__main__":
    unittest.main()
