from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import WITNESS_VERSION
from scripts.aura_workcapsule_context_binding import ACTIVE, CURRENT, compile_workcapsule_context_binding
from scripts.aura_workcapsule_raw_owner_stale_safe_exact_reentry import (
    RAW_OWNER_EXPECTED_REENTRY_MISMATCH,
    STALE_SAFE_INVALID_PREFIX,
    admit_raw_owner_stale_safe_exact_reentry,
    verify_raw_owner_stale_safe_exact_reentry,
)
from scripts.aura_workcapsule_source_bound_exact_reentry import (
    compile_expected_source_bound_reentry,
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


class WorkCapsuleRawOwnerStaleSafeExactReentryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-raw-owner-stale-safe-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.original = b"def target(x):\n    return x + 1\n"
        self.path = self.root / "src/a.py"
        self.path.write_bytes(self.original)
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
                    "checked_at": "2026-08-31T01:00:00Z",
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
            "capsule_id": "CAP-RAW-STALE-1",
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

    def expected(self, *, witness=None):
        return compile_expected_source_bound_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
        )

    def verify(self, receipt, *, witness=None):
        return verify_raw_owner_stale_safe_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=witness if witness is not None else self.witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )

    def test_raw_stale_owner_evidence_roundtrips_without_currentness_laundering(self):
        self.path.write_bytes(b"def target(x):\n    return x + 2\n")
        projected, receipt = self.expected()
        self.assertEqual("STALE", projected["source_observations"][0]["currentness"])
        self.assertEqual([], self.verify(receipt))
        admitted = admit_raw_owner_stale_safe_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.witness,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )
        self.assertTrue(admitted["raw_source_owner_recompiled"])
        self.assertTrue(admitted["source_owner_bound_exact_reproduction"])
        self.assertTrue(admitted["rejected_currentness_invariant_proven"])
        self.assertTrue(admitted["reentry_required"])
        self.assertFalse(admitted["source_observation_receipt_accepted_from_caller"])
        self.assertFalse(admitted["observed_source_witnesses_accepted_from_caller"])
        self.assertFalse(admitted["stale_observed_bytes_bound_to_source_generation"])
        self.assertFalse(admitted["current_source_evidence_admitted"])
        self.assertFalse(admitted["source_currentness_minted_by_exact_reproduction"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_raw_unknown_owner_evidence_remains_unresolved_and_requires_reentry(self):
        empty = {"version": WITNESS_VERSION, "witnesses": []}
        projected, receipt = self.expected(witness=empty)
        self.assertEqual(1, len(projected["unresolved_prior_sources"]))
        self.assertFalse(projected["unresolved_prior_sources"][0]["identity_guessed"])
        self.assertEqual([], self.verify(receipt, witness=empty))
        admitted = admit_raw_owner_stale_safe_exact_reentry(
            root=self.root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=empty,
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            reentry_receipt=receipt,
        )
        self.assertEqual(1, admitted["unresolved_source_count"])
        self.assertTrue(admitted["reentry_required"])
        self.assertFalse(admitted["current_source_evidence_admitted"])

    def test_current_only_raw_evidence_is_outside_rejected_currentness_membrane(self):
        _projected, receipt = self.expected()
        violations = self.verify(receipt)
        self.assertIn(
            STALE_SAFE_INVALID_PREFIX + "REJECTED_CURRENTNESS_REQUIRED",
            violations,
        )

    def test_old_current_receipt_cannot_survive_new_raw_stale_evidence(self):
        _projected, old_receipt = self.expected()
        self.path.write_bytes(b"def target(x):\n    return x + 2\n")
        violations = self.verify(old_receipt)
        self.assertIn(RAW_OWNER_EXPECTED_REENTRY_MISMATCH, violations)
        self.assertTrue(any(item.startswith(STALE_SAFE_INVALID_PREFIX) for item in violations))

    def test_public_boundary_has_no_source_observation_or_source_witness_injection_slot(self):
        params = inspect.signature(verify_raw_owner_stale_safe_exact_reentry).parameters
        self.assertNotIn("source_observation_receipt", params)
        self.assertNotIn("observed_source_witnesses", params)
        self.assertIn("root", params)
        self.assertIn("witness_manifest", params)


if __name__ == "__main__":
    unittest.main()
