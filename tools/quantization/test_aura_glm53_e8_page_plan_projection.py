from __future__ import annotations

from dataclasses import replace
import unittest

import numpy as np

from tools.quantization.aura_glm53_packed_expert_quantization_plan import (
    BANK_RESIDENT_BOUNDED,
    PER_EXPERT_SLICEABLE,
    IndexedQuantizedRepresentation,
    PackedExpertQuantizationRequest,
)
from tools.quantization.aura_glm53_e8_indexed_expert_page_reference import (
    ExpertPage,
    pack_expert_page,
)
from tools.quantization.aura_glm53_e8_page_plan_projection import (
    E8_EXACT_HEAD,
    E8_EXACT_RUN,
    Q2_EXACT_HEAD,
    Q2_EXACT_RUN,
    bind_selected_e8_pages_to_q2_plan,
    e8_codebook_bytes,
    e8_plan_representation_id,
    e8_q2_representation,
    implementation_binding_digest,
)

MODEL = "zai-org/GLM-5.3@fixture"
REV = "aura-e8-ref-v1"
LAYER = 7


def plan_request(*, selected=(0, 2), parameters_per_expert=128, assignments=None):
    rid = e8_plan_representation_id()
    if assignments is None:
        assignments = (rid, rid, rid)
    return PackedExpertQuantizationRequest(
        num_experts=3,
        parameters_per_expert=parameters_per_expert,
        expert_representation_ids=tuple(assignments),
        selected_expert_ids=tuple(selected),
        cache_budget_bytes=3_000_000,
        bank_resident_companion_cap_bytes=2_000_000,
        lifecycle_mode="BACKGROUND",
    )


def representations():
    rep = e8_q2_representation()
    return {rep.representation_id: rep}


def make_page(expert_id: int, role: str, *, size=64, rep_rev=REV, layer=LAYER, model=MODEL):
    rng = np.random.default_rng(1000 + expert_id * 10 + (0 if role == "gate_up_proj" else 1))
    w = rng.normal(0.0, 0.02, size=(1, size)).astype(np.float32)
    return pack_expert_page(
        w,
        model_revision=model,
        representation_revision=rep_rev,
        layer_id=layer,
        expert_id=expert_id,
        tensor_role=role,
        block_size=64,
    )


def complete_pages(selected=(0, 2)):
    return tuple(make_page(e, role) for e in selected for role in ("gate_up_proj", "down_proj"))


def bind(*, req=None, reps=None, pages=None, model=MODEL, rev=REV, layer=LAYER):
    return bind_selected_e8_pages_to_q2_plan(
        plan_request=plan_request() if req is None else req,
        representations=representations() if reps is None else reps,
        pages=complete_pages() if pages is None else pages,
        model_revision=model,
        representation_revision=rev,
        layer_id=layer,
    )


class E8PagePlanProjectionTests(unittest.TestCase):
    def test_projection_is_exact_2p25_bpw_with_bounded_shared_codebook(self):
        rep = e8_q2_representation()
        self.assertEqual(rep.companion_layout, BANK_RESIDENT_BOUNDED)
        self.assertEqual(rep.bank_resident_companion_bytes, 58112 * 8 * 4)
        self.assertEqual(rep.bank_resident_companion_bytes, e8_codebook_bytes())
        self.assertAlmostEqual(rep.effective_bits_per_weight, 2.25, places=12)
        self.assertIn("codebook-sha256:", rep.representation_id)
        self.assertEqual(len(implementation_binding_digest()), 64)

    def test_complete_selected_page_pairs_match_q2_codec_working_set(self):
        out = bind()
        self.assertEqual(out.exact_parent_heads, (Q2_EXACT_HEAD, E8_EXACT_HEAD))
        self.assertEqual(out.exact_parent_runs, (Q2_EXACT_RUN, E8_EXACT_RUN))
        self.assertTrue(out.selected_page_roles_complete)
        self.assertTrue(out.selected_parameter_count_matches_plan)
        self.assertTrue(out.shared_codebook_matches_q2_bounded_companion)
        self.assertTrue(out.q2_codec_working_set_matches_concrete_pages)
        self.assertEqual(out.selected_codec_payload_bytes, 72)
        self.assertEqual(out.q2_selected_working_set_bytes, e8_codebook_bytes() + 72)
        self.assertGreater(out.selected_serialized_page_bytes, out.selected_codec_payload_bytes)
        self.assertGreater(out.serialized_page_overhead_bytes, 0)
        self.assertFalse(out.serialized_working_set_matches_q2_plan)
        self.assertFalse(out.page_headers_accounted_in_q2_cache_budget)

    def test_missing_selected_tensor_role_fails_closed(self):
        pages = list(complete_pages())
        pages.pop()
        with self.assertRaisesRegex(ValueError, "SELECTED_PAGE_ROLE_COVERAGE_INCOMPLETE"):
            bind(pages=tuple(pages))

    def test_duplicate_role_and_unselected_page_fail_closed(self):
        pages = list(complete_pages())
        pages.append(pages[0])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EXPERT_TENSOR_ROLE_PAGE"):
            bind(pages=tuple(pages))
        foreign = make_page(1, "gate_up_proj")
        with self.assertRaisesRegex(ValueError, "FOREIGN_OR_UNSELECTED_E8_PAGE"):
            bind(pages=complete_pages() + (foreign,))

    def test_page_model_representation_and_layer_identity_are_exact(self):
        pages = list(complete_pages())
        pages[0] = make_page(0, "gate_up_proj", rep_rev="other")
        with self.assertRaisesRegex(ValueError, "PAGE_REPRESENTATION_REVISION_MISMATCH"):
            bind(pages=tuple(pages))
        pages = list(complete_pages())
        pages[0] = make_page(0, "gate_up_proj", layer=LAYER + 1)
        with self.assertRaisesRegex(ValueError, "PAGE_LAYER_MISMATCH"):
            bind(pages=tuple(pages))
        pages = list(complete_pages())
        pages[0] = make_page(0, "gate_up_proj", model="other-model")
        with self.assertRaisesRegex(ValueError, "PAGE_MODEL_REVISION_MISMATCH"):
            bind(pages=tuple(pages))

    def test_selected_expert_parameter_coverage_must_match_q2(self):
        pages = list(complete_pages())
        pages[0] = make_page(0, "gate_up_proj", size=128)
        with self.assertRaisesRegex(ValueError, "SELECTED_EXPERT_PARAMETER_COUNT_MISMATCH"):
            bind(pages=tuple(pages))

    def test_per_role_padding_ambiguity_is_rejected_not_hidden(self):
        pages = list(complete_pages())
        pages[0] = make_page(0, "gate_up_proj", size=65)
        with self.assertRaisesRegex(ValueError, "PAGE_ROLE_WEIGHT_COUNT_MUST_BE_BLOCK_ALIGNED"):
            bind(pages=tuple(pages), req=plan_request(parameters_per_expert=129))

    def test_selected_expert_must_use_exact_projected_e8_representation(self):
        rid = e8_plan_representation_id()
        other = IndexedQuantizedRepresentation("OTHER", 8, 16, 64, 16, BANK_RESIDENT_BOUNDED, bank_resident_companion_bytes=100)
        req = plan_request(assignments=("OTHER", rid, rid), selected=(0, 2))
        reps = representations(); reps["OTHER"] = other
        with self.assertRaisesRegex(ValueError, "SELECTED_EXPERT_NOT_ASSIGNED_EXACT_E8_REPRESENTATION"):
            bind(req=req, reps=reps)

    def test_same_id_with_different_q2_layout_cannot_impersonate_projection(self):
        exact = e8_q2_representation()
        fake = IndexedQuantizedRepresentation(
            exact.representation_id,
            exact.vector_dim,
            exact.index_bits_per_vector,
            exact.scale_group_weights,
            exact.scale_bits_per_group,
            PER_EXPERT_SLICEABLE,
            companion_bytes_per_expert=exact.bank_resident_companion_bytes,
        )
        with self.assertRaisesRegex(ValueError, "EXACT_E8_Q2_REPRESENTATION_REQUIRED"):
            bind(reps={exact.representation_id: fake})

    def test_payload_tamper_fails_before_accounting(self):
        pages = list(complete_pages())
        p = pages[0]
        raw = bytearray(p.payload); raw[-1] ^= 1
        pages[0] = replace(p, payload=bytes(raw))
        with self.assertRaisesRegex(ValueError, "payload digest mismatch"):
            bind(pages=tuple(pages))

    def test_successful_projection_remains_nonauthorizing(self):
        out = bind()
        for name in (
            "source_tensor_bytes_authenticated",
            "planned_layout_executed_proven",
            "selected_experts_actually_served_proven",
            "physical_io_observed",
            "model_execution_performed",
            "glm53_quality_preserved_proven",
            "general_performance_winner_proven",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(out, name), name)
        self.assertEqual(len(out.receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
