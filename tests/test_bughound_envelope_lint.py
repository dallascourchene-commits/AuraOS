import unittest

from tools.bughound.envelope_lint import LintDisposition, lint_envelope


C1 = "1DbZyzpdBIuZUt9jvWogWIesJTHbEqVKGEnmaXO_deO8"


class BugHoundEnvelopeLintTests(unittest.TestCase):
    def test_canonical_google_doc_shape_is_structurally_parseable(self):
        text = f"""AURA COMMAND ENVELOPE — TEST
schema: AuraCommandEnvelopeV1-candidate
command_id: TEST-1
requested_effect: D0
effect_ceiling: D0
constraints: D0
authority_ref: Drive {C1}
"""
        r = lint_envelope(text)
        self.assertEqual(LintDisposition.STRUCTURALLY_PARSEABLE, r.disposition)
        self.assertEqual((C1,), r.exact_drive_ids)
        self.assertEqual((), r.findings)
        self.assertFalse(r.safe_to_autorepair)
        self.assertFalse(r.authority_resolved)
        self.assertFalse(r.execution_authorized)

    def test_near_miss_title_is_rejected(self):
        r = lint_envelope("AURA COMMAND ENVELOPE V1\ncommand_id: X\n")
        self.assertEqual(LintDisposition.NOT_ENVELOPE_TITLE, r.disposition)

    def test_hash_prefixed_title_is_rejected(self):
        r = lint_envelope("# AURA COMMAND — X\ncommand_id: X\n")
        self.assertEqual(LintDisposition.NOT_ENVELOPE_TITLE, r.disposition)

    def test_prose_continuation_is_line_format(self):
        r = lint_envelope("AURA COMMAND ENVELOPE — X\ncommand_id: X\nthis is prose\n")
        self.assertEqual(LintDisposition.LINE_FORMAT, r.disposition)

    def test_json_trailing_text_detected(self):
        r = lint_envelope('{"command_id":"X"}\nextra')
        self.assertEqual(LintDisposition.TRAILING_TEXT_AFTER_JSON, r.disposition)

    def test_json_array_is_not_object(self):
        r = lint_envelope('["X"]')
        self.assertEqual(LintDisposition.JSON_NOT_OBJECT, r.disposition)

    def test_json_object_structural_parse_does_not_grant_authority(self):
        r = lint_envelope(
            '{"command_id":"X","requested_effect":"D0","effect_ceiling":"D0",'
            f'"constraints":"D0","authority_ref":"Drive {C1}"}}'
        )
        self.assertEqual(LintDisposition.STRUCTURALLY_PARSEABLE, r.disposition)
        self.assertFalse(r.authority_resolved)
        self.assertFalse(r.execution_authorized)

    def test_forbidden_credentials_are_reported_without_repair(self):
        r = lint_envelope(
            f'{{"command_id":"X","requested_effect":"D0","effect_ceiling":"D0",'
            f'"constraints":"D0","authority_ref":"Drive {C1}",'
            '"envelope":{"constraints":{"credentials":"none"}}}'
        )
        codes = [f.code for f in r.findings]
        self.assertIn("FORBIDDEN_SENSITIVE_FIELD", codes)
        self.assertFalse(r.safe_to_autorepair)

    def test_non_exact_d0_is_reported(self):
        text = f"""AURA COMMAND ENVELOPE — X
command_id: X
requested_effect: D0 research only
effect_ceiling: D0
constraints: D0
authority_ref: Drive {C1}
"""
        r = lint_envelope(text)
        self.assertIn("D0_EXACT_DECLARATION_MISMATCH", [f.code for f in r.findings])

    def test_precise_drive_id_boundary_rejects_one_leading_prose_token(self):
        fake = "1-800-555-0199-555-0199-555-0199-555-0"
        r = lint_envelope(f"AURA COMMAND ENVELOPE — X\ncommand_id: X\nauthority_ref: {fake}\n")
        self.assertEqual((), r.exact_drive_ids)
        self.assertIn("AUTHORITY_REF_NO_EXACT_DRIVE_ID", [f.code for f in r.findings])

    def test_precise_drive_id_boundary_rejects_suffix_embedding(self):
        r = lint_envelope(
            f"AURA COMMAND ENVELOPE — X\ncommand_id: X\nauthority_ref: Drive {C1}_suffix\n"
        )
        self.assertEqual((), r.exact_drive_ids)
        self.assertIn("AUTHORITY_REF_NO_EXACT_DRIVE_ID", [f.code for f in r.findings])

    def test_bom_is_not_a_structural_failure(self):
        r = lint_envelope(
            "\ufeffAURA COMMAND ENVELOPE — X\n"
            "command_id: X\n"
            "requested_effect: D0\n"
            "effect_ceiling: D0\n"
            "constraints: D0\n"
            f"authority_ref: Drive {C1}\n"
        )
        self.assertEqual(LintDisposition.STRUCTURALLY_PARSEABLE, r.disposition)

    def test_receipt_digest_is_deterministic(self):
        text = f"AURA COMMAND ENVELOPE — X\ncommand_id: X\nauthority_ref: Drive {C1}\n"
        self.assertEqual(lint_envelope(text).receipt_digest, lint_envelope(text).receipt_digest)


if __name__ == "__main__":
    unittest.main()
