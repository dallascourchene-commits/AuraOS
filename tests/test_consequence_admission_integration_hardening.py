import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))

from consequence_admission_kernel import (
    AdmissionError,
    AxisState,
    ConsequenceVector,
    ReadjudicationEnvelope,
    SourceExit,
)


def source(current=True):
    return SourceExit("drive:src", "owner:current", "gen", "semantic-root", current)


class IntegrationHardeningTests(unittest.TestCase):
    def test_malformed_omega8_value_fails_closed(self):
        values = [AxisState.VERIFIED] * 8
        values[3] = 99
        with self.assertRaises(AdmissionError):
            ConsequenceVector(tuple(values))

    def test_plain_int_that_matches_enum_value_still_fails_closed(self):
        values = [AxisState.VERIFIED] * 8
        values[3] = 2
        with self.assertRaises(AdmissionError):
            ConsequenceVector(tuple(values))

    def test_stale_source_exit_rejected_by_successor_envelope(self):
        envelope = ReadjudicationEnvelope(
            "P", "c", "policy", source(False), (), (), (), "receipt"
        )
        with self.assertRaises(AdmissionError):
            envelope.validate()

    def test_current_source_exit_remains_valid(self):
        envelope = ReadjudicationEnvelope(
            "P", "c", "policy", source(True), (), (), (), "receipt"
        )
        self.assertEqual(len(envelope.envelope_digest), 64)


if __name__ == "__main__":
    unittest.main()
