from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.aura_astge_anchor_hydration import (
    CURRENT,
    STALE,
    UNKNOWN,
    WITNESS_VERSION,
    compile_hydration_admission,
)


class AnchorHydrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="aura-anchor-hydration-")
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.source = b"def target(x):\n    return x + 1\n"
        (self.root / "src/a.py").write_bytes(self.source)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def codemap(self, *, line: int = 3, semantic_id: str = "src/a.py#function:target:stable") -> dict:
        return {
            "files": [{"path": "src/a.py", "digest8": "projection"}],
            "symbol_index": {
                "target": [
                    {
                        "file": "src/a.py",
                        "kind": "function",
                        "semantic_id": semantic_id,
                        "signature_hash": "sig-stable",
                        "line": line,
                        "end_line": line + 1,
                    }
                ]
            },
        }

    def anchors(self) -> dict:
        return {
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

    def witness(self, *, digest: str | None = None, length: int | None = None) -> dict:
        return {
            "version": WITNESS_VERSION,
            "witnesses": [
                {
                    "anchor_id": "target-anchor",
                    "file_id": 17,
                    "source_generation": 42,
                    "expected_byte_len": len(self.source) if length is None else length,
                    "expected_body_sha256": digest or hashlib.sha256(self.source).hexdigest(),
                    "witness_ref": "fixture://source-owner/42",
                    "checked_at": "2026-08-30T19:00:00-05:00",
                }
            ],
        }

    def compile(self, witness: dict, *, codemap: dict | None = None, anchors: dict | None = None) -> dict:
        return compile_hydration_admission(
            root=self.root,
            codemap=codemap or self.codemap(),
            anchor_manifest=anchors or self.anchors(),
            witness_manifest=witness,
        )

    def test_exact_body_witness_emits_d9_compatible_locator(self) -> None:
        result = self.compile(self.witness())
        self.assertEqual({CURRENT: 1, STALE: 0, UNKNOWN: 0}, result["counts"])
        receipt = result["anchor_receipts"][0]
        self.assertTrue(receipt["anchor_projection_resolved"])
        self.assertTrue(receipt["hydration_admitted"])
        self.assertEqual(CURRENT, receipt["body_currentness_status"])
        self.assertFalse(receipt["codemap_digest8_currentness_authority"])
        self.assertFalse(receipt["semantic_identity_minted_by_bridge"])
        self.assertFalse(receipt["source_authority_minted"])
        self.assertFalse(receipt["project007_runtime_implemented"])
        self.assertEqual(
            {
                "file_id": 17,
                "relative_path": "src/a.py",
                "source_generation": 42,
                "byte_len": len(self.source),
                "sha256": hashlib.sha256(self.source).hexdigest(),
            },
            result["source_locators_v1"][0],
        )

    def test_missing_witness_is_unknown_and_cannot_hydrate(self) -> None:
        result = self.compile({"version": WITNESS_VERSION, "witnesses": []})
        self.assertEqual({CURRENT: 0, STALE: 0, UNKNOWN: 1}, result["counts"])
        receipt = result["anchor_receipts"][0]
        self.assertEqual(UNKNOWN, receipt["body_currentness_status"])
        self.assertFalse(receipt["hydration_admitted"])
        self.assertEqual([], result["source_locators_v1"])

    def test_digest_drift_is_stale_even_when_codemap_projection_is_unchanged(self) -> None:
        stale = self.witness(digest="0" * 64)
        result = self.compile(stale)
        self.assertEqual({CURRENT: 0, STALE: 1, UNKNOWN: 0}, result["counts"])
        receipt = result["anchor_receipts"][0]
        self.assertEqual(STALE, receipt["body_currentness_status"])
        self.assertEqual("SOURCE_BODY_DIGEST_DRIFT", receipt["reason"])
        self.assertFalse(receipt["hydration_admitted"])
        self.assertEqual([], result["source_locators_v1"])

    def test_length_drift_is_stale_before_digest_can_admit(self) -> None:
        result = self.compile(self.witness(length=len(self.source) + 1))
        receipt = result["anchor_receipts"][0]
        self.assertEqual(STALE, receipt["body_currentness_status"])
        self.assertEqual("SOURCE_BODY_LENGTH_DRIFT", receipt["reason"])
        self.assertFalse(receipt["hydration_admitted"])

    def test_line_projection_can_move_without_changing_anchor_or_body_identity(self) -> None:
        result = self.compile(self.witness(), codemap=self.codemap(line=99))
        receipt = result["anchor_receipts"][0]
        self.assertEqual(99, receipt["line"])
        self.assertEqual(CURRENT, receipt["body_currentness_status"])
        self.assertTrue(receipt["hydration_admitted"])

    def test_semantic_identity_drift_remains_hard_failure_of_existing_anchor_owner(self) -> None:
        with self.assertRaisesRegex(ValueError, "resolved to 0 CODEMAP symbols"):
            self.compile(
                self.witness(),
                codemap=self.codemap(semantic_id="src/a.py#function:target:changed"),
            )

    def test_unknown_anchor_witness_is_rejected_not_silently_ignored(self) -> None:
        witness = self.witness()
        witness["witnesses"][0]["anchor_id"] = "not-in-manifest"
        with self.assertRaisesRegex(ValueError, "unknown anchors"):
            self.compile(witness)

    def test_same_file_can_host_multiple_anchors_only_with_coherent_file_binding(self) -> None:
        codemap = self.codemap()
        codemap["symbol_index"]["second"] = [
            {
                "file": "src/a.py",
                "kind": "function",
                "semantic_id": "src/a.py#function:second:stable",
                "signature_hash": "sig-second",
                "line": 10,
                "end_line": 11,
            }
        ]
        anchors = self.anchors()
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
        witness = self.witness()
        second = dict(witness["witnesses"][0])
        second["anchor_id"] = "second-anchor"
        witness["witnesses"].append(second)
        result = self.compile(witness, codemap=codemap, anchors=anchors)
        self.assertEqual({CURRENT: 2, STALE: 0, UNKNOWN: 0}, result["counts"])
        self.assertEqual(1, len(result["source_locators_v1"]))

        witness["witnesses"][1]["file_id"] = 18
        with self.assertRaisesRegex(ValueError, "conflicting source-body witnesses"):
            self.compile(witness, codemap=codemap, anchors=anchors)

    def test_one_file_id_cannot_alias_two_paths(self) -> None:
        other = b"def other():\n    return 2\n"
        (self.root / "src/b.py").write_bytes(other)
        codemap = self.codemap()
        codemap["files"].append({"path": "src/b.py", "digest8": "otherproj"})
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
        anchors = self.anchors()
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
        witness = self.witness()
        witness["witnesses"].append(
            {
                "anchor_id": "other-anchor",
                "file_id": 17,
                "source_generation": 42,
                "expected_byte_len": len(other),
                "expected_body_sha256": hashlib.sha256(other).hexdigest(),
                "witness_ref": "fixture://source-owner/42-other",
                "checked_at": "2026-08-30T19:00:00-05:00",
            }
        )
        with self.assertRaisesRegex(ValueError, "file_id 17 has conflicting source bindings"):
            self.compile(witness, codemap=codemap, anchors=anchors)

    @unittest.skipUnless(os.name == "posix", "symlink behavior exercised on POSIX")
    def test_symlinked_anchor_path_is_rejected_before_body_currentness(self) -> None:
        (self.root / "real.py").write_bytes(self.source)
        (self.root / "src/a.py").unlink()
        (self.root / "src/a.py").symlink_to(self.root / "real.py")
        with self.assertRaisesRegex(ValueError, "contains a symlink"):
            self.compile(self.witness())

    def test_witness_schema_requires_provenance_and_full_body_digest(self) -> None:
        witness = self.witness()
        witness["witnesses"][0]["expected_body_sha256"] = "deadbeef"
        with self.assertRaisesRegex(ValueError, "64-character SHA-256"):
            self.compile(witness)
        witness = self.witness()
        witness["witnesses"][0]["witness_ref"] = ""
        with self.assertRaisesRegex(ValueError, "witness_ref must be nonempty"):
            self.compile(witness)

    def test_json_projection_is_deterministic_for_same_inputs(self) -> None:
        first = self.compile(self.witness())
        second = self.compile(self.witness())
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )


if __name__ == "__main__":
    unittest.main()
