import unittest

from tools.project006.workercrystal_reference.workercrystal_acceptance_g6 import (
    ContractViolation,
    canonical_json_bytes,
)


MAX_JCS_SAFE_INTEGER = (1 << 53) - 1


class JCSSafeIntegerTests(unittest.TestCase):
    def test_maximum_safe_generation_is_canonicalizable(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"generation": MAX_JCS_SAFE_INTEGER}),
            b'{"generation":9007199254740991}',
        )

    def test_generation_above_safe_integer_range_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            canonical_json_bytes({"generation": MAX_JCS_SAFE_INTEGER + 1})


if __name__ == "__main__":
    unittest.main()
