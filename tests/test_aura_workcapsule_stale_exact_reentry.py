from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_invalidation import (
    SELECTED_SOURCES,
    compile_reentry_invalidation,
)
from scripts.aura_workcapsule_source_reentry_observation import compile_source_reentry_observations
from scripts.aura_workcapsule_stale_exact_reentry import (
    EXACT_REENTRY_INVALID_PREFIX,
    REJECTED_CURRENTNESS_REQUIRED,
    SOURCE_OBSERVATION_INVALID_PREFIX,
    admit_stale_safe_exact_reentry,
    verify_stale_safe_exact_reentry,
)


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


class WorkCapsuleStaleExactReentryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-workcapsule-stale-exact-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        (self.root / "src/a.py").write_bytes(self.original)
        self.original_sha = hashlib.sha256(self.original).hexdigest()
        self.codemap = {
            "files": [{"path": "src/a.py", "digest8": "projection"}],
            "symbol_index": {
                "target": [
                    {
                        "file": "src/a.py",
                        "kind": "function",
                        "semantic_id": "src/a.py#function:target:stable",
                        "signature_hash": "sig-stable",
                        "line": 1,
                        "end_line": 2,
                    }
                ]
            },
        }
        self.anchors = {
            "version": "AURA_SOURCE_ANCHOR_MANIFEST_V1",
            "anchors": [
                {
                    "anchor_id": "target-anchor",
                    "mechanism": "fixture",
                    "path": "src/a.py",
                    "symbol": "target",
                    "kind": "function",
                    "semantic_id": "src/a.py#function:target:stable",
                    "signature_hash": "sig-stable",
                    "role": "fixture anchor",
                }
            ],
        }
        self.witness = {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": 42,
                    "expected_byte_len": len(self.original),
                    "expected_body_sha256": self.original_sha,
                    "witness_ref": "fixture://source-owner/42",
                    "checked_at": "2026-08-30T20:00:00-05:00",
                }
            ],
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-1",
            "graph_generation": 7,
            "graph_basis_identity": identity("graph-7"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:7:CURRENT",
        }
        self.capsule = {
            "capsule_id": "CAP-O24-1",
            "capsule_generation": 3,
            "parent_work_order_interface_binding_generation": 5,
            "execution_basis_identity": identity("basis-3"),
        }
        self.previous = compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=self.graph,
            source_witnesses=[
                {
                    "role": ACTIVE,
                    "file_id": 17,
                    "relative_path": "src/a.py",
                    "source_generation": 42,
                    "source_sha256": self.original_sha,
                    "source_byte_len": len(self.original),
                    "currentness": CURRENT,
                    "witness_ref": "fixture://prior-current/42",
                }
            ],
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def observation(self, *, witness=None):
        return compile_source_reentry_observations(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
        )

    def o8(self, observation):
        return compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observation["o7_source_witnesses"],
        )

    def verify(self, observation, receipt):
        return verify_stale_safe_exact_reentry(
            source_observation_receipt=observation,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )

    def test_stale_expected_identity_can_drive_exact_selected_reentry_without_currentness_laundering(self):
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        observation = self.observation()
        receipt = self.o8(observation)
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual([], self.verify(observation, receipt))

        admitted = admit_stale_safe_exact_reentry(
            source_observation_receipt=observation,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )
        self.assertTrue(admitted["exact_input_reproduction"])
        self.assertTrue(admitted["reentry_required"])
        self.assertEqual(1, admitted["stale_source_count"])
        self.assertFalse(admitted["stale_observed_bytes_bound_to_source_generation"])
        self.assertFalse(admitted["current_source_evidence_admitted"])
        self.assertFalse(admitted["source_currentness_minted_by_exact_reproduction"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_current_only_observation_is_not_a_rejected_currentness_admission(self):
        observation = self.observation()
        receipt = self.o8(observation)
        self.assertIn(REJECTED_CURRENTNESS_REQUIRED, self.verify(observation, receipt))

    def test_stale_observation_laundering_tamper_fails_before_exact_admission(self):
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        observation = self.observation()
        receipt = self.o8(observation)
        tampered = copy.deepcopy(observation)
        tampered["source_observations"][0]["observed_bytes_bound_to_source_generation"] = True
        violations = self.verify(tampered, receipt)
        self.assertTrue(
            any(item.startswith(SOURCE_OBSERVATION_INVALID_PREFIX) for item in violations)
        )

    def test_old_current_o8_receipt_cannot_verify_against_new_stale_evidence(self):
        current_observation = self.observation()
        old_receipt = self.o8(current_observation)
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        stale_observation = self.observation()
        violations = self.verify(stale_observation, old_receipt)
        self.assertTrue(any(item.startswith(EXACT_REENTRY_INVALID_PREFIX) for item in violations))

    def test_missing_witness_remains_unknown_and_exactly_requires_source_reentry(self):
        observation = self.observation(witness={"version": WITNESS_VERSION, "witnesses": []})
        receipt = self.o8(observation)
        self.assertEqual(SELECTED_SOURCES, receipt["minimum_reentry_scope"])
        self.assertEqual([], self.verify(observation, receipt))
        admitted = admit_stale_safe_exact_reentry(
            source_observation_receipt=observation,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )
        self.assertEqual(1, admitted["unresolved_source_count"])
        self.assertFalse(admitted["current_source_evidence_admitted"])

    def test_changed_expected_generation_is_reentry_evidence_not_current_observed_bytes(self):
        witness = copy.deepcopy(self.witness)
        witness["witnesses"][0]["source_generation"] = 43
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        observation = self.observation(witness=witness)
        receipt = self.o8(observation)
        self.assertEqual([], self.verify(observation, receipt))
        self.assertEqual(
            {"domain": "SOURCE", "value": 43},
            observation["source_observations"][0]["source_generation_coordinate"],
        )
        self.assertFalse(
            observation["source_observations"][0]["observed_bytes_bound_to_source_generation"]
        )


if __name__ == "__main__":
    unittest.main()
