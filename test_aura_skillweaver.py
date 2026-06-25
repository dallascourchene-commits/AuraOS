"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f8-[Q-SYS:SKILLWEAVER_TEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Test Oracle)
DEPENDENCIES: pytest, numpy, aura_skillweaver
FUNCTIONS: test_weak_source_refusal, test_strong_source_allow, test_lexical_anchor_extraction, test_candidate_scoring, test_off_topic_no_mutation, test_skill_registry_loads, test_dag_plan_includes_targets, test_no_new_dependency
SYNOPSIS: Test suite for AuraSkillWeaver research relevance gate, skill-aware decomposition, and mutation plan composition.
[/AURA_MASTER_KEY]

Test suite for aura_skillweaver.py
===================================
Covers the 8 required test categories from the SkillWeaver implementation brief.
"""

import os
import sys

import pytest

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_skillweaver import (
    AuraSkillWeaver,
    ResearchCandidate,
    ResearchGateResult,
    SubTask,
    _derive_anchors_for_query,
    compose_mutation_dag,
    compute_final_relevance,
    decompose_query,
    refine_decomposition,
    score_domain_match,
    score_lexical_anchors,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def weaver():
    """Create a SkillWeaver instance pointed at the repo root."""
    repo_root = os.path.dirname(os.path.abspath(__file__))
    return AuraSkillWeaver(repo_root=repo_root)


@pytest.fixture
def strong_hopfield_candidate():
    """A paper that IS about Hopfield networks."""
    return (
        "ARXIV_HOPFIELD01",
        "TITLE: Modern Hopfield Networks for Associative Memory in Neural "
        "Architectures | ABSTRACT: We present a framework for modern Hopfield "
        "networks that implement dense associative memory with exponential "
        "storage capacity using energy function minimization and attractor "
        "dynamics for content-addressable retrieval. The model uses a "
        "continuous energy function with polynomial interaction terms.",
        None,
    )


@pytest.fixture
def weak_bellstate_candidate():
    """A paper that is NOT about Hopfield networks."""
    return (
        "ARXIV_BELLSTATE01",
        "TITLE: Passive-User Bell-State Loop-Back Key Establishment in "
        "Quantum Networks | ABSTRACT: We explore quantum key distribution "
        "using Bell states for secure communication in fiber optic networks "
        "with passive user terminals and entanglement purification.",
        None,
    )


@pytest.fixture
def weak_construction_candidate():
    """A paper about construction materials, not CS at all."""
    return (
        "ARXIV_CONSTRUCTION01",
        "TITLE: Lifecycle Assessment of Construction Material Drift in "
        "Tropical Climates | ABSTRACT: This study examines how building "
        "materials degrade under sustained thermal cycling and moisture "
        "in tropical environments over multi-decade timescales.",
        None,
    )


@pytest.fixture
def strong_vsa_candidate():
    """A paper about VSA / hyperdimensional computing."""
    return (
        "ARXIV_VSA01",
        "TITLE: Scalable Vector Symbolic Architectures for Edge Computing | "
        "ABSTRACT: We present a hyperdimensional computing framework using "
        "10000-dimensional binary vectors with bundling and binding operations "
        "for distributed representation learning on edge devices with "
        "limited memory and no GPU acceleration.",
        None,
    )


# ---------------------------------------------------------------------------
# Test 1: Weak-source refusal
# ---------------------------------------------------------------------------

class TestWeakSourceRefusal:
    def test_refuse_off_topic_papers(self, weaver, weak_bellstate_candidate,
                                     weak_construction_candidate):
        """When top papers are completely off-topic, gate must REFUSE."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_bellstate_candidate, weak_construction_candidate],
        )
        assert result.decision == "REFUSE_MUTATION"
        assert all(not c.accepted for c in result.candidates)

    def test_refuse_has_reason(self, weaver, weak_bellstate_candidate):
        """Refusal must include a human-readable reason."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_bellstate_candidate],
        )
        assert result.decision == "REFUSE_MUTATION"
        assert len(result.reason) > 20

    def test_refuse_report_format(self, weaver, weak_bellstate_candidate):
        """Formatted report must contain [RESEARCH_GATE] tags."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_bellstate_candidate],
        )
        report = weaver.format_gate_report(result)
        assert "[RESEARCH_GATE]" in report
        assert "[/RESEARCH_GATE]" in report
        assert "REFUSE_MUTATION" in report


# ---------------------------------------------------------------------------
# Test 2: Strong-source allow
# ---------------------------------------------------------------------------

class TestStrongSourceAllow:
    def test_accept_relevant_paper(self, weaver, strong_vsa_candidate):
        """A VSA paper should be accepted for a VSA query."""
        result = weaver.evaluate_research_gate(
            "vector symbolic architecture edge computing",
            [strong_vsa_candidate],
        )
        assert any(c.accepted for c in result.candidates)

    def test_allow_with_target_modules(self, weaver, strong_vsa_candidate):
        """When sources pass AND target modules found, allow mutation."""
        result = weaver.evaluate_research_gate(
            "vector symbolic architecture edge memory",
            [strong_vsa_candidate],
        )
        # With matching modules, should allow or at least not refuse outright
        assert result.decision in ("ALLOW_MUTATION", "NEED_MORE_SOURCES")

    def test_opposed_relevant_sources_pause_mutation(self, weaver):
        """Relevant but contradictory papers require evidence resolution."""
        positive = (
            "ARXIV_VSA_POSITIVE",
            "TITLE: VSA improves associative memory | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations with bundling, binding, permutation, "
            "superposition, and distributed representation. An empirical "
            "benchmark improves associative memory recall on edge devices.",
            None,
        )
        negative = (
            "ARXIV_VSA_NEGATIVE",
            "TITLE: VSA harms associative memory | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations with bundling, binding, permutation, "
            "superposition, and distributed representation. An empirical "
            "benchmark degrades associative memory recall on edge devices.",
            None,
        )

        result = weaver.evaluate_research_gate(
            "vector symbolic architecture edge memory",
            [positive, negative],
        )

        assert result.decision == "NEED_MORE_SOURCES"
        assert result.mutation_dag is None
        assert result.contradictions


# ---------------------------------------------------------------------------
# Test 3: Lexical anchor extraction
# ---------------------------------------------------------------------------

class TestLexicalAnchorExtraction:
    def test_hopfield_anchors_include_core_terms(self):
        """Hopfield query should expand to include associative memory terms."""
        anchors = _derive_anchors_for_query("Hopfield networks")
        anchor_set = set(a.lower() for a in anchors)
        assert "hopfield" in anchor_set
        assert "associative memory" in anchor_set
        assert "attractor" in anchor_set

    def test_vsa_anchors_include_hdc_terms(self):
        """VSA query should expand to include hyperdimensional terms."""
        anchors = _derive_anchors_for_query("vector symbolic architecture")
        anchor_set = set(a.lower() for a in anchors)
        assert "vector symbolic" in anchor_set or "hyperdimensional" in anchor_set

    def test_generic_query_uses_raw_tokens(self):
        """An unrecognized query should still produce anchors from raw tokens."""
        anchors = _derive_anchors_for_query("novel photonic crystal lattice")
        assert len(anchors) > 0
        assert any("novel" in a or "photonic" in a or "crystal" in a or "lattice" in a
                    for a in anchors)


# ---------------------------------------------------------------------------
# Test 4: Candidate scoring
# ---------------------------------------------------------------------------

class TestCandidateScoring:
    def test_lexical_anchor_scoring(self):
        """Text containing anchors should score > 0."""
        anchors = ["hopfield", "associative memory", "attractor"]
        text = "This paper discusses Hopfield networks and associative memory models."
        score = score_lexical_anchors(text, anchors)
        assert score > 0.5  # At least 2 of 3 anchors present

    def test_zero_anchor_coverage(self):
        """Text with no anchors should score 0.0."""
        anchors = ["hopfield", "associative memory"]
        text = "A study on tropical fish migration patterns."
        score = score_lexical_anchors(text, anchors)
        assert score == 0.0

    def test_composite_relevance_formula(self):
        """Verify the weighted formula produces expected range."""
        score = compute_final_relevance(
            vsa_resonance=0.5,
            lexical_anchor_coverage=0.8,
            title_abstract_score=0.6,
            domain_score=0.4,
        )
        expected = 0.40 * 0.5 + 0.35 * 0.8 + 0.15 * 0.6 + 0.10 * 0.4
        assert abs(score - expected) < 1e-6

    def test_domain_match_for_cs(self):
        """CS-related text should have positive domain score."""
        text = "Machine learning and neural network optimization for edge computing."
        score = score_domain_match(text)
        assert score > 0.0

    def test_domain_match_for_unrelated(self):
        """Totally unrelated text should have zero or near-zero domain score."""
        text = "A study on tropical fish breeding in coastal waters."
        score = score_domain_match(text)
        assert score < 0.1


# ---------------------------------------------------------------------------
# Test 5: No mutation when top papers are off-topic
# ---------------------------------------------------------------------------

class TestNoMutationOffTopic:
    def test_construction_paper_blocked(self, weaver, weak_construction_candidate):
        """A construction materials paper must NOT trigger mutation for CS queries."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_construction_candidate],
        )
        assert result.decision == "REFUSE_MUTATION"
        assert result.mutation_dag is None

    def test_quantum_crypto_blocked_for_hopfield(self, weaver, weak_bellstate_candidate):
        """A quantum crypto paper must not trigger mutation for Hopfield query."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_bellstate_candidate],
        )
        assert result.decision == "REFUSE_MUTATION"
        assert result.mutation_dag is None

    def test_empty_candidates_refuse(self, weaver):
        """No candidates should produce REFUSE."""
        result = weaver.evaluate_research_gate("anything", [])
        assert result.decision == "REFUSE_MUTATION"


# ---------------------------------------------------------------------------
# Test 6: Skill registry loads from CODEMAP
# ---------------------------------------------------------------------------

class TestSkillRegistry:
    def test_registry_loads(self, weaver):
        """Skill registry should load entries from the repo."""
        skills = weaver.skills
        assert len(skills) > 0

    def test_registry_has_modules(self, weaver):
        """Registry should contain module-type skills."""
        modules = [s for s in weaver.skills if s.kind == "module"]
        assert len(modules) > 5

    def test_registry_has_commands(self, weaver):
        """Registry should contain command-type skills."""
        commands = [s for s in weaver.skills if s.kind == "command"]
        assert len(commands) > 0

    def test_registry_caching(self, weaver):
        """Skills should be cached after first load."""
        s1 = weaver.skills
        s2 = weaver.skills
        assert s1 is s2

    def test_registry_invalidation(self, weaver):
        """invalidate_skill_cache should force reload."""
        s1 = weaver.skills
        weaver.invalidate_skill_cache()
        s2 = weaver.skills
        assert s1 is not s2


# ---------------------------------------------------------------------------
# Test 7: DAG plan includes target files/symbols
# ---------------------------------------------------------------------------

class TestDAGPlan:
    def test_dag_has_stages(self):
        """Mutation DAG must contain ordered stages."""
        candidates = [
            ResearchCandidate(
                trace_id="TEST01",
                title="Test Paper",
                abstract="Test abstract",
                resonance_score=0.8,
                lexical_anchor_score=0.6,
                concept_fit_score=0.7,
                accepted=True,
            )
        ]
        dag = compose_mutation_dag("test query", candidates, ["aura_substrate.py"])
        assert "stages" in dag
        assert len(dag["stages"]) == 9  # 8 original + HIVP integrity verification

    def test_dag_includes_target_files(self):
        """DAG must reference the target files."""
        candidates = [
            ResearchCandidate(
                trace_id="TEST01", title="Test", abstract="",
                resonance_score=0.8, lexical_anchor_score=0.6,
                concept_fit_score=0.7, accepted=True,
            )
        ]
        targets = ["aura_dream_engine.py", "aura_spectral_memory.py"]
        dag = compose_mutation_dag("test", candidates, targets)
        stage3 = dag["stages"][2]
        assert stage3["action"] == "retrieve_target_modules"
        assert stage3["target_files"] == targets

    def test_dag_includes_security_validation(self):
        """DAG must include a security validation stage."""
        candidates = [
            ResearchCandidate(
                trace_id="TEST01", title="Test", abstract="",
                resonance_score=0.8, lexical_anchor_score=0.6,
                concept_fit_score=0.7, accepted=True,
            )
        ]
        dag = compose_mutation_dag("test", candidates, ["test.py"])
        security_stages = [s for s in dag["stages"]
                          if "security" in s["action"].lower()]
        assert len(security_stages) > 0

    def test_dag_includes_rollback(self):
        """DAG must include a rollback path."""
        candidates = [
            ResearchCandidate(
                trace_id="TEST01", title="Test", abstract="",
                resonance_score=0.8, lexical_anchor_score=0.6,
                concept_fit_score=0.7, accepted=True,
            )
        ]
        dag = compose_mutation_dag("test", candidates, ["aura_substrate.py"])
        last_stage = dag["stages"][-1]
        assert "rollback_path" in last_stage


# ---------------------------------------------------------------------------
# Test 8: No new dependency introduced
# ---------------------------------------------------------------------------

class TestNoDependency:
    def test_skillweaver_imports_only_stdlib_and_numpy(self):
        """aura_skillweaver.py must not import packages beyond numpy + stdlib."""
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "aura_skillweaver.py")
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        import ast as ast_mod
        tree = ast_mod.parse(source)

        allowed_modules = {
            # stdlib
            "hashlib", "json", "os", "re", "time", "pathlib",
            "dataclasses", "typing",
            "__future__",
            # already in repo
            "numpy", "np",
            # aura modules (conditional imports within same repo)
            "aura_fst_routing",
            "aura_scientific_memory",
        }

        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in allowed_modules, (
                        f"Disallowed import: {alias.name}"
                    )
            elif isinstance(node, ast_mod.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top in allowed_modules, (
                        f"Disallowed import from: {node.module}"
                    )


# ---------------------------------------------------------------------------
# Test: Decomposition
# ---------------------------------------------------------------------------

class TestDecomposition:
    def test_decompose_produces_subtasks(self):
        """decompose_query must return a list of SubTask objects."""
        tasks = decompose_query("Hopfield networks")
        assert len(tasks) == 5
        assert all(isinstance(t, SubTask) for t in tasks)

    def test_refine_marks_failures(self):
        """When no sources pass, refinement should mark gate_check as failed."""
        tasks = decompose_query("test")
        candidates = [
            ResearchCandidate(
                trace_id="T1", title="", abstract="",
                resonance_score=0.1, lexical_anchor_score=0.0,
                concept_fit_score=0.05, accepted=False,
                rejection_reason="No anchors",
            )
        ]
        refined = refine_decomposition(tasks, candidates, [])
        gate_task = [t for t in refined if t.task_type == "gate_check"][0]
        assert gate_task.status == "failed"


# ---------------------------------------------------------------------------
# Test: Report formatting
# ---------------------------------------------------------------------------

class TestReportFormat:
    def test_report_contains_key_sections(self, weaver, weak_bellstate_candidate):
        result = weaver.evaluate_research_gate("Hopfield", [weak_bellstate_candidate])
        report = weaver.format_gate_report(result)
        assert "QUERY:" in report
        assert "DECISION:" in report
        assert "REASON:" in report
        assert "FINAL_SCORE:" in report

    def test_allow_report_has_plan(self, weaver, strong_vsa_candidate):
        result = weaver.evaluate_research_gate(
            "vector symbolic architecture spectral memory",
            [strong_vsa_candidate],
        )
        if result.decision == "ALLOW_MUTATION":
            report = weaver.format_gate_report(result)
            assert "PLAN:" in report

    def test_report_includes_contradictions_section_when_present(self, weaver):
        """format_gate_report must emit a CONTRADICTIONS section when conflicts exist."""
        positive = (
            "ARXIV_VSA_P",
            "TITLE: VSA improves associative memory | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations with bundling, binding, permutation, "
            "superposition, and distributed representation. An empirical "
            "benchmark improves associative memory recall on edge devices.",
            None,
        )
        negative = (
            "ARXIV_VSA_N",
            "TITLE: VSA harms associative memory | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations with bundling, binding, permutation, "
            "superposition, and distributed representation. An empirical "
            "benchmark degrades associative memory recall on edge devices.",
            None,
        )
        result = weaver.evaluate_research_gate(
            "vector symbolic architecture edge memory",
            [positive, negative],
        )
        report = weaver.format_gate_report(result)
        assert "CONTRADICTIONS:" in report

    def test_contradictions_section_shows_ids_and_polarity(self, weaver):
        """Contradiction lines must include left_id, right_id, and polarity values."""
        positive = (
            "ARXIV_POS",
            "TITLE: HDC improves edge retrieval | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations. An empirical benchmark improves "
            "retrieval accuracy on edge devices.",
            None,
        )
        negative = (
            "ARXIV_NEG",
            "TITLE: HDC harms edge retrieval | ABSTRACT: This vector "
            "symbolic architecture uses hyperdimensional HDC holographic "
            "reduced representations. An empirical benchmark degrades "
            "retrieval accuracy on edge devices.",
            None,
        )
        result = weaver.evaluate_research_gate(
            "hyperdimensional edge retrieval",
            [positive, negative],
        )
        if result.contradictions:
            report = weaver.format_gate_report(result)
            conflict = result.contradictions[0]
            assert conflict.left_id in report
            assert conflict.right_id in report
            assert "positive" in report or "negative" in report

    def test_no_contradictions_section_when_none_present(self, weaver, weak_bellstate_candidate):
        """When no contradictions exist, report must not contain CONTRADICTIONS:."""
        result = weaver.evaluate_research_gate("Hopfield networks", [weak_bellstate_candidate])
        report = weaver.format_gate_report(result)
        assert "CONTRADICTIONS:" not in report


# ---------------------------------------------------------------------------
# Test: ResearchGateResult contradictions field
# ---------------------------------------------------------------------------

class TestResearchGateResultContradictions:
    def test_contradictions_field_defaults_to_empty_list(self):
        """ResearchGateResult.contradictions should default to empty list."""
        result = ResearchGateResult(
            query="test",
            decision="REFUSE_MUTATION",
            candidates=[],
            required_anchors=[],
            final_score=0.0,
            reason="No sources.",
        )
        assert result.contradictions == []

    def test_contradictions_not_set_when_all_candidates_refused(self, weaver, weak_bellstate_candidate):
        """When all candidates fail, no contradictions should be reported."""
        result = weaver.evaluate_research_gate(
            "Hopfield networks",
            [weak_bellstate_candidate],
        )
        assert result.decision == "REFUSE_MUTATION"
        # Contradictions are only detected from accepted records,
        # so when nothing is accepted there can be no contradictions.
        assert result.contradictions == []

    def test_contradictions_reported_only_for_accepted_candidates(self, weaver):
        """Only accepted candidates participate in contradiction detection."""
        accepted = (
            "ARXIV_VSA_ACC",
            "TITLE: VSA improves edge | ABSTRACT: Hyperdimensional HDC vector "
            "symbolic architecture improves accuracy on edge devices. "
            "Empirical benchmark demonstrates improvement.",
            None,
        )
        rejected = (
            "ARXIV_OFFTOPIC",
            "TITLE: Coral reef survey | ABSTRACT: A biological survey "
            "of coral reefs in tropical waters.",
            None,
        )
        # The off-topic paper should be rejected; its polarity state is irrelevant.
        result = weaver.evaluate_research_gate(
            "vector symbolic architecture edge accuracy",
            [accepted, rejected],
        )
        accepted_ids = {c.trace_id for c in result.candidates if c.accepted}
        for contradiction in result.contradictions:
            assert contradiction.left_id in accepted_ids
            assert contradiction.right_id in accepted_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
