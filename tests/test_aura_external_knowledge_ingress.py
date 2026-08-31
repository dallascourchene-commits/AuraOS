from __future__ import annotations

from dataclasses import replace
import unittest

from tools import aura_external_knowledge_ingress as eki


def current_generation(*, uri="https://example.org/item/v1", digest="a"*64, value="rev-1"):
    return eki.SourceGeneration(
        generation_type="IMMUTABLE_REVISION",
        generation_value=value,
        checked_at="2026-08-31T16:30:00Z",
        exact_source_uri=uri,
        content_sha256=digest,
        etag='"example-etag"',
    )


def material(level, generation_id, payload):
    return eki.HydrationMaterial(
        level=level,
        source_generation_id=generation_id,
        payload=payload,
    )


class ExternalKnowledgeIngressTests(unittest.TestCase):
    def test_unknown_discovery_is_cacheable_but_heavy_hydration_and_execution_are_withheld(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.ARXIV,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="arXiv:2605.00529",
            canonical_uri="https://arxiv.org/abs/2605.00529",
            title="Hierarchical Abstract Tree",
            thesis="Hierarchical retrieval.",
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L4,
        )
        self.assertEqual(card.availability, eki.Availability.DISCOVERY_CACHEABLE.value)
        self.assertEqual(card.admitted_hydration_level, 1)
        self.assertFalse(card.execution_authorized)
        self.assertFalse(card.semantic_k27_authority)
        self.assertIsNone(card.exact_reopen_uri)

    def test_current_exact_arxiv_can_reach_l4_with_generation_bound_materials(self):
        generation = current_generation(
            uri="https://arxiv.org/pdf/2605.00529v1",
            digest="1"*64,
            value="2605.00529v1",
        )
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.ARXIV,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="arXiv:2605.00529",
            canonical_uri="https://arxiv.org/abs/2605.00529",
            title="Hierarchical Abstract Tree",
            thesis="Hierarchical retrieval.",
            currentness=eki.Currentness.CURRENT,
            generation=generation,
            rights=eki.RightsMetadata(
                state=eki.RightsState.DECLARED,
                license_expression="ARXIV-DISTRIBUTION-METADATA",
            ),
        )
        gid = generation.generation_id
        materials = (
            material(eki.HydrationLevel.L2, gid, {"claims": ["hierarchy", "multi-granular"]}),
            material(eki.HydrationLevel.L3, gid, {"falsifiers": ["distribution drift"]}),
            material(eki.HydrationLevel.L4, gid, {"source": "exact"}),
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L4,
            materials=materials,
        )
        self.assertEqual(card.admitted_hydration_level, 4)
        self.assertEqual(card.exact_reopen_uri, generation.exact_source_uri)
        self.assertEqual(card.content_sha256, "1"*64)
        self.assertEqual(card.availability, eki.Availability.READ_ONLY_REFERENCE_READY.value)

    def test_l4_without_content_digest_degrades_to_l3_not_fake_exactness(self):
        generation = eki.SourceGeneration(
            generation_type="VERSION",
            generation_value="v1",
            checked_at="2026-08-31T16:30:00Z",
            exact_source_uri="https://example.org/v1",
        )
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.WEB,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="example:1",
            canonical_uri="https://example.org/item",
            title="Example",
            thesis="Example",
            currentness=eki.Currentness.CURRENT,
            generation=generation,
        )
        gid = generation.generation_id
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L4,
            materials=(
                material(eki.HydrationLevel.L2, gid, {"x": 1}),
                material(eki.HydrationLevel.L3, gid, {"y": 2}),
                material(eki.HydrationLevel.L4, gid, {"z": 3}),
            ),
        )
        self.assertEqual(card.admitted_hydration_level, 3)
        self.assertIsNone(card.exact_reopen_uri)

    def test_generation_mismatch_rejects_heavy_material(self):
        generation = current_generation()
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.CODE,
            canonical_id="owner/repo",
            canonical_uri="https://github.com/owner/repo",
            title="Repo",
            thesis="Tooling",
            currentness=eki.Currentness.CURRENT,
            generation=generation,
        )
        with self.assertRaisesRegex(ValueError, "HYDRATION_GENERATION_MISMATCH"):
            eki.admit_external_knowledge(
                observation=observation,
                requested_level=eki.HydrationLevel.L2,
                materials=(material(eki.HydrationLevel.L2, "wrong", {"claims": []}),),
            )

    def test_stale_source_preserves_orientation_but_requires_reverification(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.CODE,
            canonical_id="owner/repo",
            canonical_uri="https://github.com/owner/repo",
            title="Repo",
            thesis="Tooling",
            currentness=eki.Currentness.STALE,
            generation=current_generation(value="commit-a"),
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L4,
        )
        self.assertEqual(card.availability, eki.Availability.STALE_REVERIFY_REQUIRED.value)
        self.assertEqual(card.admitted_hydration_level, 1)
        self.assertFalse(card.execution_authorized)

    def test_tool_with_unknown_rights_or_security_is_metadata_review_required(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.TOOL,
            canonical_id="owner/tool",
            canonical_uri="https://github.com/owner/tool",
            title="Tool",
            thesis="Useful agent tool",
            currentness=eki.Currentness.CURRENT,
            generation=current_generation(value="deadbeef"),
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L1,
        )
        self.assertEqual(card.availability, eki.Availability.TOOL_METADATA_REVIEW_REQUIRED.value)
        self.assertFalse(card.execution_authorized)

    def test_tool_with_declared_rights_and_security_is_inspection_ready_never_execution_ready(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.HUGGINGFACE_SPACE,
            artifact_class=eki.ArtifactClass.TOOL,
            canonical_id="org/space",
            canonical_uri="https://huggingface.co/spaces/org/space",
            title="Space",
            thesis="Candidate external tool",
            currentness=eki.Currentness.CURRENT,
            generation=current_generation(
                uri="https://huggingface.co/spaces/org/space/tree/rev1",
                value="rev1",
            ),
            rights=eki.RightsMetadata(
                state=eki.RightsState.DECLARED, license_expression="apache-2.0"
            ),
            security=eki.SecurityMetadata(
                state=eki.SecurityState.METADATA_RECORDED,
                remote_code_requested=True,
                network_capability=True,
                write_capability=None,
                secret_capability=None,
                security_notes=("provider-hosted executable surface",),
            ),
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L1,
        )
        self.assertEqual(card.availability, eki.Availability.TOOL_INSPECTION_READY.value)
        self.assertTrue(card.security["remote_code_requested"])
        self.assertFalse(card.execution_authorized)
        self.assertFalse(card.provider_effect_authorized)

    def test_unknown_security_facts_remain_null_not_sanitized_false(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.CODE,
            canonical_id="owner/repo",
            canonical_uri="https://github.com/owner/repo",
            title="Repo",
            thesis="Code",
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L1,
        )
        self.assertIsNone(card.hydration["L1"]["remote_code_requested"])
        self.assertIsNone(card.hydration["L1"]["write_capability"])
        self.assertIsNone(card.hydration["L1"]["secret_capability"])

    def test_scholar_discovery_cannot_self_mint_primary_source_currentness(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GOOGLE_SCHOLAR_DISCOVERY,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="scholar:discovery:1",
            canonical_uri="https://scholar.google.com/scholar?q=test",
            title="Discovery",
            thesis="Discovery pointer",
            currentness=eki.Currentness.CURRENT,
            generation=current_generation(),
        )
        with self.assertRaisesRegex(ValueError, "SCHOLAR_DISCOVERY_CANNOT_SELF_MINT"):
            observation.validate()

    def test_13d_projection_is_exactly_thirteen_trits_and_never_authority(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.REDDIT,
            artifact_class=eki.ArtifactClass.DISCUSSION,
            canonical_id="reddit:post:1",
            canonical_uri="https://www.reddit.com/r/Rag/comments/post",
            title="Discussion",
            thesis="Community falsification pressure",
            advisory_only=True,
        )
        projection = eki.build_projection_13d(observation, eki.HydrationLevel.L1)
        self.assertEqual(len(projection.trits), 13)
        self.assertTrue(all(v in (0, 1, 2) for v in projection.trits))
        self.assertFalse(projection.semantic_authority)

    def test_k27_locality_preserves_13d_prefix_and_is_routing_only(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.CODE,
            canonical_id="owner/repo",
            canonical_uri="https://github.com/owner/repo",
            title="Repo",
            thesis="Code",
        )
        projection = eki.build_projection_13d(observation, eki.HydrationLevel.L1)
        locality = eki.build_k27_locality(observation, projection)
        self.assertEqual(len(locality.trits), 27)
        self.assertEqual(tuple(locality.trits[:13]), projection.trits)
        self.assertTrue(locality.routing_only)
        self.assertFalse(locality.semantic_identity)
        self.assertFalse(locality.authority)

    def test_coordinate_changes_do_not_change_semantic_identity(self):
        base = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.GITHUB,
            artifact_class=eki.ArtifactClass.CODE,
            canonical_id="owner/repo",
            canonical_uri="https://github.com/owner/repo",
            title="Repo",
            thesis="Code",
            relevance=eki.RelevanceBand.LOW,
        )
        changed = replace(base, relevance=eki.RelevanceBand.HIGH)
        self.assertEqual(base.semantic_id, changed.semantic_id)
        p1 = eki.build_projection_13d(base, eki.HydrationLevel.L1)
        p2 = eki.build_projection_13d(changed, eki.HydrationLevel.L1)
        self.assertNotEqual(p1.trits, p2.trits)

    def test_generation_change_preserves_semantic_id_but_changes_generation_id(self):
        first = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.HUGGINGFACE_MODEL,
            artifact_class=eki.ArtifactClass.MODEL,
            canonical_id="org/model",
            canonical_uri="https://huggingface.co/org/model",
            title="Model",
            thesis="Model metadata",
            currentness=eki.Currentness.CURRENT,
            generation=current_generation(value="sha-a"),
        )
        second = replace(first, generation=current_generation(value="sha-b"))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.generation.generation_id, second.generation.generation_id)

    def test_toroidal_refresh_phase_is_deterministic_scheduler_hint_not_currentness(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.WEB,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="docs:api",
            canonical_uri="https://example.org/docs",
            title="Docs",
            thesis="Mutable docs",
            volatility=eki.Volatility.HIGH,
        )
        first = eki.build_refresh_phase(observation)
        second = eki.build_refresh_phase(observation)
        self.assertEqual(first, second)
        self.assertTrue(0 <= first.slot < 27)
        self.assertEqual(first.recommended_interval_seconds, 3600)
        self.assertFalse(first.currentness_witness)

    def test_missing_l2_material_does_not_hallucinate_requested_depth(self):
        generation = current_generation()
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.ARXIV,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="arXiv:1",
            canonical_uri="https://arxiv.org/abs/1",
            title="Paper",
            thesis="Paper",
            currentness=eki.Currentness.CURRENT,
            generation=generation,
        )
        card = eki.admit_external_knowledge(
            observation=observation,
            requested_level=eki.HydrationLevel.L3,
            materials=(),
        )
        self.assertEqual(card.admitted_hydration_level, 1)
        self.assertNotIn("L2", card.hydration)

    def test_receipt_is_deterministic_for_identical_inputs(self):
        observation = eki.ExternalDiscoveryObservation(
            source_kind=eki.SourceKind.WEB,
            artifact_class=eki.ArtifactClass.KNOWLEDGE,
            canonical_id="example",
            canonical_uri="https://example.org/",
            title="Example",
            thesis="Example",
        )
        first = eki.admit_external_knowledge(
            observation=observation, requested_level=eki.HydrationLevel.L1
        )
        second = eki.admit_external_knowledge(
            observation=observation, requested_level=eki.HydrationLevel.L1
        )
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_provider_json_preserves_unknown_security_and_currentness(self):
        observation = eki.observation_from_provider_metadata(
            {
                "source_kind": "GITHUB",
                "artifact_class": "TOOL",
                "canonical_id": "owner/tool",
                "canonical_uri": "https://github.com/owner/tool",
                "title": "Tool",
                "thesis": "Tool",
                "rights": {"state": "UNKNOWN"},
                "security": {"state": "UNKNOWN"},
            }
        )
        self.assertEqual(observation.currentness, eki.Currentness.UNKNOWN)
        self.assertIsNone(observation.security.remote_code_requested)


if __name__ == "__main__":
    unittest.main()
