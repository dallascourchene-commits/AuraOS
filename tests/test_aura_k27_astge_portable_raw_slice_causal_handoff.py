from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    admit_raw_slice_causal_handoff,
    canonical_raw_slice_payload_bytes,
    verify_portable_raw_slice_projection,
    verify_raw_slice_against_causal_post_source,
)

FIXTURE = Path("tests/fixtures/o30_portable_raw_slice_projection.json")


def projection() -> dict:
    return json.loads(FIXTURE.read_text())


def reseal(item: dict) -> dict:
    item["payload_sha256"] = hashlib.sha256(
        canonical_raw_slice_payload_bytes(item["payload"])
    ).hexdigest()
    return item


def witness(**overrides) -> dict:
    row = {
        "role": "SOURCE",
        "file_id": 7,
        "relative_path": "src/a.py",
        "source_generation": 43,
        "source_sha256": "22" * 32,
        "source_byte_len": 18,
        "currentness": "CURRENT",
        "witness_ref": "ASTGE:CURRENT:src/a.py",
    }
    row.update(overrides)
    return row


class PortableRawSliceCausalHandoffTests(unittest.TestCase):
    def test_shared_vector_verifies_and_matches_causal_post_source_coordinate(self) -> None:
        item = projection()
        self.assertEqual([], verify_portable_raw_slice_projection(item))
        self.assertEqual(
            [],
            verify_raw_slice_against_causal_post_source(
                raw_slice_projection=item,
                post_source_witness=witness(),
            ),
        )
        receipt = admit_raw_slice_causal_handoff(
            raw_slice_projection=item,
            post_source_witness=witness(),
        )
        self.assertTrue(receipt["raw_slice_projection_verified"])
        self.assertTrue(receipt["post_source_coordinate_compatible"])
        self.assertFalse(receipt["causal_post_owner_reproved_by_this_function"])
        self.assertFalse(receipt["producer_authenticated"])
        self.assertFalse(receipt["semantic_handle_derived_from_raw_slice"])
        self.assertFalse(receipt["semantic_identity_proven_by_raw_slice"])
        self.assertFalse(receipt["effect_authority"])

    def test_payload_digest_tamper_is_rejected(self) -> None:
        item = projection()
        item["payload_sha256"] = "aa" * 32
        self.assertIn("PAYLOAD_DIGEST_MISMATCH", verify_portable_raw_slice_projection(item))

    def test_authority_or_semantic_widening_is_rejected(self) -> None:
        item = projection()
        item["payload"]["semantic_handle_derived_from_raw_slice"] = True
        self.assertIn(
            "CEILING_VIOLATION:semantic_handle_derived_from_raw_slice",
            verify_portable_raw_slice_projection(item),
        )

    def test_python_bool_cannot_impersonate_version_or_integer_coordinates(self) -> None:
        item = projection()
        item["payload"]["version"] = True
        self.assertIn("WRONG_VERSION", verify_portable_raw_slice_projection(item))

        item = projection()
        item["payload"]["source_generation"] = True
        self.assertIn(
            "INVALID_INTEGER:source_generation",
            verify_portable_raw_slice_projection(item),
        )

    def test_resealed_span_beyond_full_source_is_rejected(self) -> None:
        item = projection()
        item["payload"]["target_byte_end"] = 19
        item["payload"]["target_slice_byte_len"] = 15
        reseal(item)
        self.assertIn(
            "TARGET_SPAN_OUT_OF_SOURCE_BOUNDS",
            verify_portable_raw_slice_projection(item),
        )

    def test_independently_current_foreign_source_coordinate_is_rejected(self) -> None:
        item = projection()
        for changed, code in (
            ({"file_id": 8}, "FILE_ID_MISMATCH"),
            ({"relative_path": "src/b.py"}, "RELATIVE_PATH_MISMATCH"),
            ({"source_generation": 44}, "SOURCE_GENERATION_MISMATCH"),
            ({"source_sha256": "55" * 32}, "FULL_SOURCE_DIGEST_MISMATCH"),
            ({"source_byte_len": 19}, "FULL_SOURCE_LENGTH_MISMATCH"),
        ):
            violations = verify_raw_slice_against_causal_post_source(
                raw_slice_projection=item,
                post_source_witness=witness(**changed),
            )
            self.assertIn(code, violations)

    def test_noncurrent_or_widened_post_source_witness_is_rejected(self) -> None:
        item = projection()
        self.assertIn(
            "POST_SOURCE_NOT_CURRENT",
            verify_raw_slice_against_causal_post_source(
                raw_slice_projection=item,
                post_source_witness=witness(currentness="STALE"),
            ),
        )
        widened = witness()
        widened["authority"] = True
        self.assertEqual(
            ["POST_SOURCE_WITNESS_CLOSED_SCHEMA_VIOLATION"],
            verify_raw_slice_against_causal_post_source(
                raw_slice_projection=item,
                post_source_witness=widened,
            ),
        )

    def test_json_member_order_is_nonsemantic_but_caller_reseal_is_not_accepted(self) -> None:
        item = projection()
        reordered = copy.deepcopy(item)
        reordered["payload"] = dict(reversed(list(reordered["payload"].items())))
        self.assertEqual([], verify_portable_raw_slice_projection(reordered))
        reordered["payload_sha256"] = "66" * 32
        self.assertIn(
            "PAYLOAD_DIGEST_MISMATCH",
            verify_portable_raw_slice_projection(reordered),
        )


if __name__ == "__main__":
    unittest.main()
