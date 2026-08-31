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
from scripts.aura_workcapsule_source_reentry_observation import (
    SOURCE_DOMAIN,
    compile_source_reentry_observations,
    verify_source_reentry_observations,
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


class WorkCapsuleSourceReentryObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-workcapsule-source-reentry-")
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
            "capsule_id": "CAP-O9-1",
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

    def compile(self, *, witness=None):
        return compile_source_reentry_observations(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
        )

    def test_current_owner_locator_projects_exact_source_identity(self) -> None:
        receipt = self.compile()
        self.assertEqual([], receipt["unresolved_prior_sources"])
        self.assertEqual(1, len(receipt["o7_source_witnesses"]))
        row = receipt["o7_source_witnesses"][0]
        self.assertEqual(CURRENT, row["currentness"])
        self.assertEqual(17, row["file_id"])
        self.assertEqual(42, row["source_generation"])
        observation = receipt["source_observations"][0]
        self.assertEqual({"domain": SOURCE_DOMAIN, "value": 42}, observation["source_generation_coordinate"])
        self.assertTrue(observation["observed_bytes_bound_to_source_generation"])
        self.assertEqual([], verify_source_reentry_observations(receipt))

    def test_stale_body_preserves_expected_dependency_identity_without_binding_observed_bytes(self) -> None:
        mutated = b"def target(x):\n    return x + 2\n"
        self.assertEqual(len(mutated), len(self.original))
        (self.root / "src/a.py").write_bytes(mutated)
        receipt = self.compile()
        row = receipt["o7_source_witnesses"][0]
        self.assertEqual("STALE", row["currentness"])
        self.assertEqual(17, row["file_id"])
        self.assertEqual(42, row["source_generation"])
        self.assertEqual(self.original_sha, row["source_sha256"])
        observation = receipt["source_observations"][0]
        self.assertFalse(observation["observed_bytes_bound_to_source_generation"])
        stale_owner = observation["stale_owner_receipts"][0]
        self.assertNotEqual(stale_owner["observed_body_sha256"], self.original_sha)
        self.assertEqual([], verify_source_reentry_observations(receipt))

        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=receipt["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])
        self.assertEqual([{"file_id": 17, "relative_path": "src/a.py"}], reentry["minimum_reentry_source_keys"])

    def test_missing_body_witness_remains_unknown_identity_and_o8_fails_closed(self) -> None:
        receipt = self.compile(witness={"version": WITNESS_VERSION, "witnesses": []})
        self.assertEqual([], receipt["o7_source_witnesses"])
        self.assertEqual(1, len(receipt["unresolved_prior_sources"]))
        unresolved = receipt["unresolved_prior_sources"][0]
        self.assertEqual("UNKNOWN", unresolved["currentness"])
        self.assertFalse(unresolved["identity_guessed"])
        self.assertEqual([], verify_source_reentry_observations(receipt))

        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=receipt["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])
        self.assertEqual(1, len(reentry["unresolved_active_sources"]))

    def test_changed_expected_source_generation_retains_source_domain_and_rebinds(self) -> None:
        witness = copy.deepcopy(self.witness)
        witness["witnesses"][0]["source_generation"] = 43
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        receipt = self.compile(witness=witness)
        row = receipt["o7_source_witnesses"][0]
        self.assertEqual(43, row["source_generation"])
        observation = receipt["source_observations"][0]
        self.assertEqual({"domain": SOURCE_DOMAIN, "value": 43}, observation["source_generation_coordinate"])
        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=receipt["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])

    def test_changed_file_id_cannot_alias_prior_dependency(self) -> None:
        witness = copy.deepcopy(self.witness)
        witness["witnesses"][0]["file_id"] = 18
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        receipt = self.compile(witness=witness)
        self.assertEqual(18, receipt["o7_source_witnesses"][0]["file_id"])
        reentry = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=receipt["o7_source_witnesses"],
        )
        self.assertEqual(SELECTED_SOURCES, reentry["minimum_reentry_scope"])
        self.assertEqual(1, len(reentry["unresolved_active_sources"]))
        self.assertEqual(1, len(reentry["unbound_observations"]))

    def test_multiple_anchors_same_file_collapse_to_one_coherent_source_observation(self) -> None:
        codemap = copy.deepcopy(self.codemap)
        codemap["symbol_index"]["second"] = [
            {
                "file": "src/a.py",
                "kind": "function",
                "semantic_id": "src/a.py#function:second:stable",
                "signature_hash": "sig-second",
                "line": 3,
                "end_line": 4,
            }
        ]
        anchors = copy.deepcopy(self.anchors)
        anchors["anchors"].append(
            {
                "anchor_id": "second-anchor",
                "mechanism": "fixture",
                "path": "src/a.py",
                "symbol": "second",
                "kind": "function",
                "semantic_id": "src/a.py#function:second:stable",
                "signature_hash": "sig-second",
                "role": "second fixture anchor",
            }
        )
        witness = copy.deepcopy(self.witness)
        second = copy.deepcopy(witness["witnesses"][0])
        second["anchor_id"] = "second-anchor"
        witness["witnesses"].append(second)
        receipt = compile_source_reentry_observations(
            root=self.root,
            codemap=codemap,
            anchor_manifest=anchors,
            witness_manifest=witness,
            previous_binding=self.previous,
        )
        self.assertEqual(1, len(receipt["o7_source_witnesses"]))
        self.assertEqual(1, len(receipt["source_observations"]))
        self.assertEqual([], verify_source_reentry_observations(receipt))

    def test_extra_hydration_path_is_recorded_without_dependency_promotion(self) -> None:
        other = b"def other():\n    return 2\n"
        (self.root / "src/b.py").write_bytes(other)
        codemap = copy.deepcopy(self.codemap)
        codemap["files"].append({"path": "src/b.py", "digest8": "bproj"})
        codemap["symbol_index"]["other"] = [
            {
                "file": "src/b.py",
                "kind": "function",
                "semantic_id": "src/b.py#function:other:stable",
                "signature_hash": "sig-other",
                "line": 1,
                "end_line": 2,
            }
        ]
        anchors = copy.deepcopy(self.anchors)
        anchors["anchors"].append(
            {
                "anchor_id": "other-anchor",
                "mechanism": "fixture",
                "path": "src/b.py",
                "symbol": "other",
                "kind": "function",
                "semantic_id": "src/b.py#function:other:stable",
                "signature_hash": "sig-other",
                "role": "other fixture anchor",
            }
        )
        witness = copy.deepcopy(self.witness)
        witness["witnesses"].append(
            {
                "anchor_id": "other-anchor",
                "file_id": 18,
                "source_generation": 1,
                "expected_byte_len": len(other),
                "expected_body_sha256": hashlib.sha256(other).hexdigest(),
                "witness_ref": "fixture://other/1",
                "checked_at": "2026-08-30T20:00:00-05:00",
            }
        )
        receipt = compile_source_reentry_observations(
            root=self.root,
            codemap=codemap,
            anchor_manifest=anchors,
            witness_manifest=witness,
            previous_binding=self.previous,
        )
        self.assertEqual(["src/b.py"], receipt["unbound_hydration_paths"])
        self.assertFalse(receipt["new_dependency_auto_promoted"])
        self.assertEqual(1, len(receipt["o7_source_witnesses"]))

    def test_stale_observed_bytes_cannot_be_laundered_as_generation_bound(self) -> None:
        (self.root / "src/a.py").write_bytes(b"def target(x):\n    return x + 2\n")
        receipt = self.compile()
        receipt["source_observations"][0]["observed_bytes_bound_to_source_generation"] = True
        violations = verify_source_reentry_observations(receipt)
        self.assertIn("STALE_OBSERVED_BYTES_LAUNDERED_AS_GENERATION_BOUND", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)

    def test_source_generation_domain_tamper_is_detected(self) -> None:
        receipt = self.compile()
        receipt["source_observations"][0]["source_generation_coordinate"]["domain"] = "PLACEMENT"
        violations = verify_source_reentry_observations(receipt)
        self.assertIn("OBSERVATION_SOURCE_GENERATION_DOMAIN_LOST", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)

    def test_authority_tamper_is_detected(self) -> None:
        receipt = self.compile()
        receipt["authority"]["execution_authorized"] = True
        violations = verify_source_reentry_observations(receipt)
        self.assertIn("AUTHORITY_MINTED_BY_SOURCE_REENTRY_PROJECTION", violations)
        self.assertIn("RECEIPT_IDENTITY_MISMATCH", violations)


if __name__ == "__main__":
    unittest.main()
