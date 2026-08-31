from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_external_knowledge_ingress import (
    COORDINATE_SCHEMA,
    ExternalObservation,
    ExternalSubject,
    HydrationPayload,
    KnowledgeState,
    build_external_knowledge_node,
    classify_refresh,
    derive_coordinate_projection,
)


class ExternalKnowledgeIngressTests(unittest.TestCase):
    def subject(self, provider="GITHUB"):
        return ExternalSubject(
            provider=provider,
            source_kind="REPOSITORY" if provider == "GITHUB" else "PAPER",
            canonical_id="owner/repo" if provider == "GITHUB" else "2606.26511v1",
            canonical_uri="https://github.com/owner/repo" if provider == "GITHUB"
            else "https://arxiv.org/abs/2606.26511v1",
            sector="06_RUN" if provider == "GITHUB" else "08_RSH",
        )

    def observation(self, *, rev="abc123", content="a" * 64, verifier="v1"):
        return ExternalObservation(
            provider_revision=rev,
            content_digest=content,
            observed_at="2026-08-31T16:45:00Z",
            source_generated_at="2026-08-31T16:30:00Z",
            exact_source_uri="https://github.com/owner/repo/tree/abc123",
            verifier_generation=verifier,
            verified_fields=("canonical_id", "exact_source_uri", "provider_revision"),
            etag='"etag-a"',
            last_modified="Mon, 31 Aug 2026 16:30:00 GMT",
            license_id="Apache-2.0",
            security_flags=("REMOTE_CODE_UNPROVEN",),
        )

    def hydration(self):
        return (
            HydrationPayload(
                level="L0",
                data={"title": "repo", "thesis": "bounded agent toolkit"},
                derivation_method="PROVIDER_METADATA_EXTRACT",
            ),
            HydrationPayload(
                level="L1",
                data={"purpose": "agent tooling"},
                derivation_method="README_SUMMARY_UNVERIFIED",
            ),
            HydrationPayload(
                level="L2",
                data={"claims": ["typed tool interface"], "equations": []},
                derivation_method="SOURCE_BOUND_SYNTHESIS",
                source_excerpt_digest="b" * 64,
            ),
            HydrationPayload(
                level="L3",
                data={"falsifiers": ["remote code"], "dependencies": ["python"]},
                derivation_method="SECURITY_PROVENANCE_AUDIT",
            ),
            HydrationPayload(
                level="L4",
                data={"exact_source_uri": "https://github.com/owner/repo/tree/abc123"},
                derivation_method="IMMUTABLE_SOURCE_POINTER",
            ),
        )

    def current_node(self):
        return build_external_knowledge_node(
            subject=self.subject(),
            observation=self.observation(),
            knowledge_state=KnowledgeState.CURRENT_REFERENCE,
            hydration=self.hydration(),
            validator_generation="eki-validator-v1",
        )

    def test_stable_subject_changes_evidence_on_revision(self):
        a = self.current_node()
        b = build_external_knowledge_node(
            subject=self.subject(),
            observation=self.observation(rev="def456", content="c" * 64),
            knowledge_state=KnowledgeState.CURRENT_REFERENCE,
            hydration=self.hydration(),
            validator_generation="eki-validator-v1",
        )
        self.assertEqual(a.subject_key, b.subject_key)
        self.assertNotEqual(a.evidence_generation_key, b.evidence_generation_key)
        self.assertEqual(classify_refresh(previous=a, current=b), "CONTENT_GENERATION_CHANGED")

    def test_verifier_refresh_is_not_content_generation(self):
        a = self.current_node()
        b = build_external_knowledge_node(
            subject=self.subject(),
            observation=self.observation(verifier="v2"),
            knowledge_state=KnowledgeState.CURRENT_REFERENCE,
            hydration=self.hydration(),
            validator_generation="eki-validator-v2",
        )
        self.assertEqual(a.subject_key, b.subject_key)
        self.assertNotEqual(a.evidence_generation_key, b.evidence_generation_key)
        self.assertEqual(classify_refresh(previous=a, current=b), "METADATA_OR_VERIFIER_REFRESH")

    def test_observed_time_cannot_precede_source_generation(self):
        bad = replace(
            self.observation(),
            observed_at="2026-08-31T16:00:00Z",
            source_generated_at="2026-08-31T16:30:00Z",
        )
        with self.assertRaisesRegex(ValueError, "SOURCE_GENERATION_CANNOT_FOLLOW_OBSERVATION"):
            build_external_knowledge_node(
                subject=self.subject(),
                observation=bad,
                knowledge_state=KnowledgeState.CURRENT_REFERENCE,
                hydration=self.hydration(),
                validator_generation="v1",
            )

    def test_hydration_must_be_contiguous(self):
        with self.assertRaisesRegex(ValueError, "HYDRATION_MUST_BE_CONTIGUOUS_FROM_L0"):
            build_external_knowledge_node(
                subject=self.subject(),
                observation=self.observation(),
                knowledge_state=KnowledgeState.CURRENT_REFERENCE,
                hydration=(self.hydration()[0], self.hydration()[2]),
                validator_generation="v1",
            )

    def test_stale_source_cannot_remain_read_only_admissible(self):
        current = self.current_node()
        stale = replace(
            current,
            knowledge_state=KnowledgeState.STALE_REVERIFY_REQUIRED,
            read_only_reference_admissible=False,
        )
        stale.validate()
        with self.assertRaisesRegex(ValueError, "READ_ONLY_REFERENCE_REQUIRES_CURRENT_REFERENCE"):
            replace(stale, read_only_reference_admissible=True).validate()

    def test_ingress_cannot_mint_effect_authority(self):
        node = self.current_node()
        with self.assertRaisesRegex(ValueError, "INGRESS_CANNOT_MINT_TOOL_OR_EFFECT_AUTHORITY"):
            replace(node, code_execution_authorized=True).validate()
        with self.assertRaisesRegex(ValueError, "INGRESS_CANNOT_MINT_TOOL_OR_EFFECT_AUTHORITY"):
            replace(node, model_download_authorized=True).validate()
        with self.assertRaisesRegex(ValueError, "INGRESS_CANNOT_MINT_TOOL_OR_EFFECT_AUTHORITY"):
            replace(node, semantic_k27_authority=True).validate()

    def test_coordinates_are_deterministic_but_not_identity(self):
        node = self.current_node()
        p = derive_coordinate_projection(
            subject_key=node.subject_key,
            evidence_generation_key=node.evidence_generation_key,
            source_verified=True,
            source_current=True,
            exact_source_resolvable=True,
        )
        self.assertEqual(p.scheme, COORDINATE_SCHEMA)
        self.assertEqual(len(p.subject_trits_13d), 13)
        self.assertEqual(set(p.subject_trits_13d) <= {0, 1, 2}, True)
        self.assertEqual(p.tesseract_vertex, (1, 1, 1, 0))
        self.assertNotEqual(node.subject_key, "".join(map(str, p.subject_trits_13d)))

    def test_k27_and_13d_change_do_not_grant_authority(self):
        node = self.current_node()
        self.assertFalse(node.semantic_k27_authority)
        self.assertFalse(node.provider_effect_authorized)
        self.assertFalse(node.native_private_transformer_kv_accessed)
        self.assertTrue(node.tool_use_requires_separate_admission)

    def test_arxiv_provider_gets_revision_invalidators(self):
        subject = self.subject("ARXIV")
        observation = replace(
            self.observation(rev="2606.26511v2"),
            exact_source_uri="https://arxiv.org/abs/2606.26511v2",
        )
        node = build_external_knowledge_node(
            subject=subject,
            observation=observation,
            knowledge_state=KnowledgeState.CURRENT_REFERENCE,
            hydration=self.hydration(),
            validator_generation="v1",
        )
        self.assertIn("NEW_VERSION", node.invalidation_triggers)
        self.assertIn("WITHDRAWAL", node.invalidation_triggers)

    def test_node_digest_deterministic(self):
        a = self.current_node()
        b = self.current_node()
        self.assertEqual(a.node_digest, b.node_digest)


if __name__ == "__main__":
    unittest.main()
