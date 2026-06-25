"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fa-[Q-SYS:RESONANT_ORACLE_TEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Test Oracle Verification)
DEPENDENCIES: pytest, numpy, aura_resonant_test_oracle
FUNCTIONS: test_exact_equality_resonates_1, test_mismatch_resonates_low, test_contains_hit, test_contains_miss, test_structure_match, test_type_match, test_type_mismatch, test_suite_aggregation, test_lukasiewicz_implication, test_oracle_efficiency_equation
SYNOPSIS: Test suite for Claims N7/N26/N29 -- Resonant Test Oracle, Lukasiewicz t-norm, and fractal resonance operations at the test-assertion scale.
[/AURA_MASTER_KEY]
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_resonant_test_oracle import (
    ResonantTestOracle,
    _cosine_resonance,
    _lukasiewicz_implication,
    _text_to_phasor,
    resonate_contains,
    resonate_equal,
    resonate_structure,
    resonate_type,
    run_resonant_suite,
)

# ── N26: Resonant Test Oracle ──

class TestResonantEquality:
    def test_exact_match_resonates_1(self):
        r = resonate_equal("exact", 42, 42)
        assert r.resonance == 1.0
        assert r.zone == "pass"
        assert r.passed

    def test_string_exact_match(self):
        r = resonate_equal("str_exact", "hello world", "hello world")
        assert r.resonance == 1.0

    def test_mismatch_resonates_low(self):
        r = resonate_equal("mismatch", "quantum computing", "tropical fish")
        assert r.resonance < 0.5
        assert r.zone == "fracture"
        assert not r.passed

    def test_near_match_intermediate(self):
        r = resonate_equal("near", "hello world", "hello worlds")
        # Different strings but similar content -- not 1.0, not 0.0
        assert 0.0 < r.resonance < 1.0


class TestResonantContains:
    def test_contains_hit(self):
        r = resonate_contains("has_it", "The Hopfield network uses energy", "Hopfield")
        assert r.resonance == 1.0
        assert r.zone == "pass"

    def test_contains_miss(self):
        r = resonate_contains("missing", "Tropical fish migration study", "Hopfield")
        assert r.resonance < 0.9

    def test_partial_token_overlap(self):
        r = resonate_contains("partial", "vector symbolic architecture on edge", "vector architecture")
        # "vector" and "architecture" are both present
        assert r.resonance > 0.5


class TestResonantStructure:
    def test_all_keys_present(self):
        r = resonate_structure("full", ["a", "b", "c"], {"a": 1, "b": 2, "c": 3})
        assert r.resonance > 0.8
        assert r.zone == "pass"

    def test_missing_keys(self):
        r = resonate_structure("missing", ["a", "b", "c", "d"], {"a": 1})
        assert r.resonance < 0.5

    def test_empty_expected(self):
        r = resonate_structure("empty", [], {"x": 1})
        assert r.resonance == 1.0


class TestResonantType:
    def test_exact_type(self):
        r = resonate_type("is_list", list, [1, 2, 3])
        assert r.resonance == 1.0

    def test_subclass(self):
        r = resonate_type("is_dict", dict, {"a": 1})
        assert r.resonance >= 0.95

    def test_wrong_type(self):
        r = resonate_type("not_dict", dict, [1, 2, 3])
        assert r.resonance < 0.85  # Below warning threshold


class TestSuiteAggregation:
    def test_suite_collects_assertions(self):
        oracle = ResonantTestOracle("test_suite")
        oracle.assert_equal("a", 1, 1)
        oracle.assert_equal("b", 2, 2)
        result = oracle.result()
        assert len(result.assertions) == 2
        assert result.mean_resonance == 1.0
        assert result.fracture_count == 0

    def test_suite_detects_fractures(self):
        oracle = ResonantTestOracle("fracture_suite")
        oracle.assert_equal("good", 1, 1)
        oracle.assert_equal("bad", "quantum", "fish")
        result = oracle.result()
        assert result.fracture_count >= 1
        assert result.mean_resonance < 1.0

    def test_suite_efficiency(self):
        oracle = ResonantTestOracle("eff_suite")
        oracle.assert_equal("a", 1, 1)
        oracle.assert_equal("b", 2, 2)
        result = oracle.result()
        assert result.efficiency > 0  # Should be positive for passing suite

    def test_run_resonant_suite(self):
        def my_tests(oracle):
            oracle.assert_equal("t1", "abc", "abc")
            oracle.assert_type("t2", str, "hello")
        result = run_resonant_suite("my_suite", my_tests)
        assert result.suite_name == "my_suite"
        assert result.pass_count == 2

    def test_report_format(self):
        oracle = ResonantTestOracle("fmt_suite")
        oracle.assert_equal("good", 1, 1)
        oracle.assert_equal("bad", "x", "y")
        report = oracle.format_report()
        assert "[RESONANT_TEST_ORACLE]" in report
        assert "[/RESONANT_TEST_ORACLE]" in report
        assert "MEAN_RESONANCE" in report


# ── N7: Lukasiewicz t-norm ──

class TestLukasiewicz:
    def test_implication_both_true(self):
        # min(1, 1 - 1 + 1) = 1
        assert _lukasiewicz_implication(1.0, 1.0) == 1.0

    def test_implication_false_implies_true(self):
        # min(1, 1 - 0 + 1) = 1
        assert _lukasiewicz_implication(0.0, 1.0) == 1.0

    def test_implication_true_implies_false(self):
        # min(1, 1 - 1 + 0) = 0
        assert _lukasiewicz_implication(1.0, 0.0) == 0.0

    def test_implication_partial(self):
        # min(1, 1 - 0.7 + 0.3) = 0.6
        result = _lukasiewicz_implication(0.7, 0.3)
        assert abs(result - 0.6) < 0.01


# ── Phasor codec consistency ──

class TestPhasorCodec:
    def test_deterministic(self):
        a = _text_to_phasor("hello")
        b = _text_to_phasor("hello")
        assert np.allclose(a, b)

    def test_different_inputs_quasi_orthogonal(self):
        a = _text_to_phasor("quantum computing")
        b = _text_to_phasor("tropical fish")
        res = _cosine_resonance(a, b)
        assert res < 0.1  # Quasi-orthogonal

    def test_self_resonance_near_one(self):
        a = _text_to_phasor("hello world")
        res = _cosine_resonance(a, a)
        assert res > 0.99

    def test_no_new_deps(self):
        """aura_resonant_test_oracle.py uses only numpy + stdlib."""
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "aura_resonant_test_oracle.py")
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        import ast as ast_mod
        tree = ast_mod.parse(source)

        allowed = {
            "__future__", "hashlib", "json", "os", "time",
            "dataclasses", "typing", "numpy", "np",
        }

        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in allowed, f"Disallowed import: {alias.name}"
            elif isinstance(node, ast_mod.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in allowed, f"Disallowed from-import: {node.module}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
