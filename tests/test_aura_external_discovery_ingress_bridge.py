from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_external_discovery import DiscoveryRecord
from tools.aura_external_discovery_ingress_bridge import (
    discovery_to_l0_node,
    promote_if_same_current_generation,
)
from tools.aura_external_knowledge_ingress import KnowledgeState


def github_record(*, sha: str = "a" * 40, metadata_digest: str = "b" * 64) -> DiscoveryRecord:
    return DiscoveryRecord(
        provider="GITHUB",
        source_kind="REPOSITORY",
        canonical_id="owner/repo",
        canonical_uri="https://github.com/owner/repo",
        title="owner/repo",
        provider_revision=sha,
        source_generated_at="2026-08-31T16:30:00Z",
        exact_source_uri=f"https://github.com/owner/repo/tree/{sha}",
        provider_metadata_digest=metadata_digest,
        metadata={"license": "MIT", "archived": False},
        revision_strength="EXACT_COMMIT_SHA",
    )


class DiscoveryIngressBridgeTests(unittest.TestCase):
    def test_discovery_is_metadata_verified_not_current(self):
        node = discovery_to_l0_node(github_record(), observed_at="2026-08-31T16:45:00Z")
        self.assertEqual(node.knowledge_state, KnowledgeState.METADATA_VERIFIED)
        self.assertFalse(node.read_only_reference_admissible)
        self.assertTrue(node.tool_use_requires_separate_admission)

    def test_matching_second_observation_promotes_read_only(self):
        record = github_record()
        node = discovery_to_l0_node(record, observed_at="2026-08-31T16:45:00Z")
        current = promote_if_same_current_generation(
            node,
            record,
            observed_at="2026-08-31T16:46:00Z",
        )
        self.assertEqual(current.knowledge_state, KnowledgeState.CURRENT_REFERENCE)
        self.assertTrue(current.read_only_reference_admissible)
        self.assertEqual(node.subject_key, current.subject_key)
        self.assertNotEqual(node.evidence_generation_key, current.evidence_generation_key)
        self.assertEqual(node.observation.provider_revision, current.observation.provider_revision)
        self.assertEqual(node.observation.content_digest, current.observation.content_digest)
        self.assertFalse(current.code_execution_authorized)
        self.assertFalse(current.provider_effect_authorized)

    def test_changed_generation_requires_reverify(self):
        first = github_record()
        node = discovery_to_l0_node(first, observed_at="2026-08-31T16:45:00Z")
        changed = github_record(sha="c" * 40, metadata_digest="d" * 64)
        changed = replace(changed, exact_source_uri="https://github.com/owner/repo/tree/" + "c" * 40)
        result = promote_if_same_current_generation(
            node,
            changed,
            observed_at="2026-08-31T16:46:00Z",
        )
        self.assertEqual(result.knowledge_state, KnowledgeState.STALE_REVERIFY_REQUIRED)
        self.assertFalse(result.read_only_reference_admissible)

    def test_changed_subject_invalidates(self):
        node = discovery_to_l0_node(github_record(), observed_at="2026-08-31T16:45:00Z")
        other = replace(
            github_record(),
            canonical_id="other/repo",
            canonical_uri="https://github.com/other/repo",
            exact_source_uri="https://github.com/other/repo/tree/" + "a" * 40,
        )
        result = promote_if_same_current_generation(
            node,
            other,
            observed_at="2026-08-31T16:46:00Z",
        )
        self.assertEqual(result.knowledge_state, KnowledgeState.INVALIDATED)

    def test_weak_revision_source_is_not_metadata_verified(self):
        weak = replace(
            github_record(),
            provider="SEMANTIC_SCHOLAR",
            source_kind="PAPER",
            canonical_id="P1",
            canonical_uri="https://www.semanticscholar.org/paper/P1",
            exact_source_uri="https://www.semanticscholar.org/paper/P1",
            revision_strength="SYNTHETIC_METADATA_GENERATION_NO_NATIVE_UPDATED_AT",
            metadata={"license": None},
        )
        node = discovery_to_l0_node(weak, observed_at="2026-08-31T16:45:00Z")
        self.assertEqual(node.knowledge_state, KnowledgeState.SOURCE_RESOLVED)
        self.assertFalse(node.read_only_reference_admissible)


if __name__ == "__main__":
    unittest.main()
