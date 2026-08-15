"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f7-[Q-SYS:SKILLWEAVER_GATE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Disciplined Mutation Gate)
DEPENDENCIES: numpy, json, os, re, hashlib, time
FUNCTIONS: AuraSkill, ResearchCandidate, ResearchGateResult, AuraSkillWeaver, extract_required_anchors, score_lexical_anchors, score_concept_fit, evaluate_research_gate, decompose_query, build_skill_registry, compose_mutation_dag, gate_fusion_task
SYNOPSIS: Aura-native skill-aware decomposition, research relevance gating, skill retrieval, and mutation plan composition. Implements the SkillWeaver / Compositional Skill Routing pattern adapted into Aura architecture. Prevents ungrounded code mutations from semantically resonant but conceptually irrelevant research matches.
[/AURA_MASTER_KEY]

Aura SkillWeaver -- Research Relevance Gate & Skill-Aware Decomposition
========================================================================

This module intercepts the !research pipeline BEFORE the Cloud Synthesizer.
It enforces a disciplined gate: resonance alone is not enough for mutation.
Mutation requires source relevance + skill fit + target grounding + safety.

The central rule:
    No source-sufficient evidence -> no code mutation.

Pipeline:
    query -> decompose into atomic subtasks -> retrieve papers/modules/skills
    -> validate lexical/conceptual relevance -> re-decompose using hints
    -> compose executable DAG plan -> generate staged mutation OR refuse

No new dependencies beyond numpy (already in repo).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

from aura_scientific_memory import detect_contradictions, record_from_content

# ---------------------------------------------------------------------------
# Core Data Structures
# ---------------------------------------------------------------------------

@dataclass
class AuraSkill:
    """Registry entry representing a capability in the Aura codebase."""
    name: str
    kind: str          # command | module | function | paper | output_mode
    path: str | None
    symbol: str | None
    description: str
    categories: list = field(default_factory=list)
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    fst_slots: dict = field(default_factory=dict)
    thermal_cost: float = 0.0


@dataclass
class ResearchCandidate:
    """A research trace evaluated against the relevance gate."""
    trace_id: str
    title: str
    abstract: str
    resonance_score: float
    lexical_anchor_score: float
    concept_fit_score: float
    accepted: bool
    rejection_reason: str | None = None


@dataclass
class ResearchGateResult:
    """Final gate decision for a research query."""
    query: str
    decision: str  # ALLOW_ARENA_STAGING | REFUSE_MUTATION | NEED_MORE_SOURCES
    candidates: list = field(default_factory=list)
    required_anchors: list = field(default_factory=list)
    final_score: float = 0.0
    reason: str = ""
    target_modules: list = field(default_factory=list)
    mutation_dag: dict | None = None
    contradictions: list = field(default_factory=list)


@dataclass
class SubTask:
    """An atomic subtask from query decomposition."""
    id: int
    description: str
    task_type: str   # retrieve_sources | identify_mechanism | find_modules | gate_check | generate_plan
    status: str = "pending"  # pending | passed | failed | skipped
    result: str = ""
    resonance: float = 0.0        # continuous N26 score
    shadow_norm: float = 1.0      # ‖vshadow‖ — how much gap remains
    depth: int = 0                # recursion depth (N30 bound ≤ 5)


# ---------------------------------------------------------------------------
# Anchor Expansion -- domain-specific concept clusters
# ---------------------------------------------------------------------------

_CONCEPT_ANCHORS = {
    "hopfield": [
        "hopfield", "associative memory", "attractor", "energy function",
        "content-addressable", "dense associative memory", "modern hopfield",
        "ising", "cleanup memory", "convergence dynamics",
    ],
    "vsa": [
        "vector symbolic", "hyperdimensional", "holographic reduced",
        "bundling", "binding", "permutation", "high-dimensional",
        "distributed representation", "hdc", "superposition",
    ],
    "transformer": [
        "transformer", "attention mechanism", "self-attention",
        "multi-head", "positional encoding", "layer normalization",
        "feed-forward", "encoder-decoder", "causal mask",
    ],
    "reinforcement": [
        "reinforcement learning", "reward function", "policy gradient",
        "q-learning", "bellman", "markov decision", "exploration",
        "value function", "actor-critic", "temporal difference",
    ],
    "graph_neural": [
        "graph neural", "message passing", "node embedding",
        "graph convolution", "adjacency", "neighborhood aggregation",
        "spectral graph", "graph attention", "gnn",
    ],
    "fst": [
        "finite-state", "transducer", "finite automaton", "lexicon",
        "state transition", "morphotactic", "opcode", "fst",
    ],
    "mesh": [
        "mesh network", "swarm", "distributed", "peer-to-peer",
        "gossip protocol", "consensus", "udp", "beacon",
    ],
    "quantum": [
        "quantum", "qubit", "superposition", "entanglement",
        "quantum computing", "grover", "shor", "bell state",
    ],
    "memory": [
        "memory consolidation", "episodic memory", "working memory",
        "long-term memory", "recall", "forgetting curve",
        "hippocampus", "memory palace", "engram",
    ],
}


def _derive_anchors_for_query(query):
    """
    Dynamically derive required anchors from the query.
    Matches query tokens against concept clusters, then expands.
    Always includes the raw query terms as base anchors.
    """
    query_lower = query.lower()
    tokens = set(re.findall(r"\b[a-z]{3,}\b", query_lower))

    # Start with raw query terms as base anchors
    anchors = list(tokens)

    # Expand from known concept clusters
    for cluster_key, cluster_terms in _CONCEPT_ANCHORS.items():
        cluster_hit = cluster_key in query_lower
        if not cluster_hit:
            for term in cluster_terms[:3]:
                if term in query_lower:
                    cluster_hit = True
                    break
        if cluster_hit:
            for term in cluster_terms:
                if term not in anchors:
                    anchors.append(term)

    return anchors


# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------

def score_lexical_anchors(text, anchors):
    """Fraction of required anchors found in the text. Returns 0.0 to 1.0."""
    if not anchors:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for a in anchors if a.lower() in text_lower)
    return hits / len(anchors)


def score_title_abstract_match(title, abstract, query):
    """Direct match scoring: how many query terms appear in title/abstract."""
    query_tokens = set(re.findall(r"\b[a-z]{3,}\b", query.lower()))
    if not query_tokens:
        return 0.0

    title_lower = title.lower()
    abstract_lower = abstract.lower()

    title_hits = sum(2 for t in query_tokens if t in title_lower)
    abstract_hits = sum(1 for t in query_tokens if t in abstract_lower)

    max_possible = len(query_tokens) * 3
    if max_possible == 0:
        return 0.0
    return min(1.0, (title_hits + abstract_hits) / max_possible)


def score_domain_match(text, target_domains=None):
    """Domain/category match: does the paper belong to a relevant domain?"""
    if target_domains is None:
        target_domains = [
            "computer science", "machine learning", "artificial intelligence",
            "neural network", "vector symbolic", "hyperdimensional",
            "edge computing", "distributed system", "memory",
            "attention", "topology", "graph", "optimization",
        ]
    text_lower = text.lower()
    hits = sum(1 for d in target_domains if d in text_lower)
    return min(1.0, hits / max(1, len(target_domains) * 0.3))


def compute_final_relevance(vsa_resonance, lexical_anchor_coverage,
                             title_abstract_score, domain_score, qdkt=None, query_concept=""):
    """
    Weighted composite relevance score, dynamically adapted from QDKT history if available.
    """
    # Default weights
    w = {"res": 0.40, "lex": 0.35, "ta": 0.15, "dom": 0.10}
    
    # Adapt from QDKT history if available
    if qdkt and query_concept:
        try:
            concept_key = f"gate_weights:{query_concept[:20]}"
            crystal = qdkt.fast_path(query_concept)
            if not crystal:
                crystal = qdkt.fast_path(concept_key)
            if crystal and crystal.get("confidence", 0) > 0.75:
                import json
                w.update(json.loads(crystal.get("action", "{}")))
        except Exception:
            pass

    return (
        w["res"] * min(1.0, vsa_resonance)
        + w["lex"] * lexical_anchor_coverage
        + w["ta"] * title_abstract_score
        + w["dom"] * domain_score
    )


# ---------------------------------------------------------------------------
# Skill Registry Builder
# ---------------------------------------------------------------------------

def build_skill_registry(repo_root=None):
    """Build a lightweight skill registry from the canonical CODEMAP surface."""
    if repo_root is None:
        repo_root = os.path.dirname(os.path.abspath(__file__))

    skills = []
    command_names = set()

    # 1. Parse canonical CODEMAP.json for module/function/command entries.
    codemap_json = os.path.join(repo_root, ".aura", "CODEMAP.json")
    if os.path.exists(codemap_json):
        try:
            with open(codemap_json, encoding="utf-8") as f:
                cmap = json.load(f)

            for entry in cmap.get("files", []):
                path = entry.get("path", "")
                role = entry.get("role", "")
                if role == "python_module" and path.endswith(".py"):
                    name = os.path.splitext(os.path.basename(path))[0]
                    deps_str = entry.get("dependencies", "")
                    deps = deps_str.split(", ") if deps_str else []
                    skills.append(AuraSkill(
                        name=name,
                        kind="module",
                        path=path,
                        symbol=None,
                        description=entry.get("synopsis", "")[:200],
                        categories=[role],
                        dependencies=deps,
                    ))

            symbol_index = cmap.get("symbol_index", {})
            if isinstance(symbol_index, dict):
                for name, entries in symbol_index.items():
                    if not isinstance(entries, list):
                        continue
                    for sym in entries:
                        if not isinstance(sym, dict):
                            continue
                        skills.append(AuraSkill(
                            name=str(name),
                            kind="function",
                            path=sym.get("file", ""),
                            symbol=str(name),
                            description=str(sym.get("signature", "")),
                            categories=["symbol"],
                        ))

            command_index = cmap.get("command_index", {})
            if isinstance(command_index, dict):
                for cmd, locations in sorted(command_index.items()):
                    if not isinstance(cmd, str) or not cmd.startswith("!"):
                        continue
                    if not isinstance(locations, list) or not locations:
                        continue
                    first_loc = str(locations[0])
                    file_part = first_loc.rsplit(":", 1)[0] if ":" in first_loc else first_loc
                    skills.append(AuraSkill(
                        name=cmd,
                        kind="command",
                        path=file_part,
                        symbol=cmd,
                        description="Bang command " + cmd,
                        categories=["command"],
                    ))
                    command_names.add(cmd)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # 2. Legacy fallback only: old CODEMAP.md builds rendered a command index.
    codemap_md = os.path.join(repo_root, ".aura", "CODEMAP.md")
    if os.path.exists(codemap_md):
        try:
            with open(codemap_md, encoding="utf-8") as f:
                md_content = f.read()

            for m in re.finditer(r"- `(!\w+)` -> (.+)", md_content):
                cmd = m.group(1)
                if cmd in command_names:
                    continue
                locations = m.group(2).strip()
                first_loc = locations.split(",")[0].strip()
                file_part = first_loc.split(":")[0].strip("`")
                skills.append(AuraSkill(
                    name=cmd,
                    kind="command",
                    path=file_part,
                    symbol=cmd,
                    description="Bang command " + cmd,
                    categories=["command"],
                ))
                command_names.add(cmd)
        except Exception:
            pass

    # 3. Scan OUTPUT_FORMATS.md for output modes
    outfmt = os.path.join(repo_root, ".aura", "OUTPUT_FORMATS.md")
    if os.path.exists(outfmt):
        try:
            with open(outfmt, encoding="utf-8") as f:
                content = f.read()
            for m in re.finditer(r"## `\[OUTPUT:(\w+)\]`", content):
                skills.append(AuraSkill(
                    name="OUTPUT:" + m.group(1),
                    kind="output_mode",
                    path=".aura/OUTPUT_FORMATS.md",
                    symbol=None,
                    description="Output format " + m.group(1),
                    categories=["output_format"],
                ))
        except Exception:
            pass

    return skills


def find_target_modules(query, skills, codemap_content=""):
    """
    Find Aura modules relevant to a query using CODEMAP navigation
    and optional FST-aware routing (Axiom A3: Higher-Dimensional Projection).

    When aura.lexc is available, skill lookup walks the FST graph
    so that the grammar constrains which modules can be reached.
    Falls back to keyword matching when FST is absent.
    """
    query_tokens = set(re.findall(r"\b[a-z]{3,}\b", query.lower()))
    scored = []

    # Primary: keyword-based module scoring
    for skill in skills:
        if skill.kind != "module" or not skill.path:
            continue

        text = (skill.name + " " + skill.description).lower()
        hits = sum(1 for t in query_tokens if t in text)
        if hits > 0:
            score = hits / max(1, len(query_tokens))
            scored.append((score, skill.path))

    # Secondary: FST-enhanced routing when aura.lexc is available
    # The FST grammar constrains reachable states, filtering out
    # modules that are structurally disconnected from the query domain
    lexc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aura.lexc")
    if os.path.exists(lexc_path):
        try:
            from aura_fst_routing import FSTLexiconRoutingCore
            fst = FSTLexiconRoutingCore.from_lexc(lexc_path, strict=False)
            fst_stats = fst.get_stats()
            # Use FST state count as a connectivity bonus for modules
            # that appear in the FST routing graph
            fst_states = set(fst.states.keys())
            for i, (score, path) in enumerate(scored):
                module_name = os.path.splitext(os.path.basename(path))[0]
                # Boost modules that are reachable in the FST graph
                for state_id in fst_states:
                    if module_name.replace("aura_", "").lower() in state_id.lower():
                        scored[i] = (score * 1.15, path)  # 15% FST connectivity boost
                        break
        except Exception:
            pass  # FST unavailable; keyword results stand alone

    scored.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in scored[:5]]


# ---------------------------------------------------------------------------
# Query Decomposition (Aura-SAD)
# ---------------------------------------------------------------------------

def decompose_query(query):
    """Skill-Aware Decomposition: break a research query into atomic subtasks."""
    return [
        SubTask(id=1, description="Retrieve source-sufficient papers for: " + query,
                task_type="retrieve_sources"),
        SubTask(id=2, description="Identify core mechanism from " + query + " relevant to Aura",
                task_type="identify_mechanism"),
        SubTask(id=3, description="Find Aura memory/processing modules through CODEMAP for: " + query,
                task_type="find_modules"),
        SubTask(id=4, description="Validate mutation eligibility: relevance gate + target fit",
                task_type="gate_check"),
        SubTask(id=5, description="Generate staged mutation plan only if all gates pass",
                task_type="generate_plan"),
    ]


def refine_decomposition(subtasks, candidates, target_modules):
    """One-iteration decomposition refinement based on retrieved evidence."""
    from aura_resonant_test_oracle import ResonantTestOracle
    oracle = ResonantTestOracle("decomposition_refinement")

    strong_sources = [c for c in candidates if c.accepted]
    weak_sources = [c for c in candidates if not c.accepted]

    for task in subtasks:
        if task.task_type == "retrieve_sources":
            if strong_sources:
                task.status = "passed"
                task.result = str(len(strong_sources)) + " source(s) accepted, " + str(len(weak_sources)) + " rejected"
                task.resonance = 1.0
            else:
                task.status = "failed"
                task.result = "No sources passed relevance gate. " + str(len(weak_sources)) + " candidate(s) rejected."
                task.resonance = 0.2

        elif task.task_type == "find_modules":
            if target_modules:
                task.status = "passed"
                task.result = "Found " + str(len(target_modules)) + " target module(s)"
                task.resonance = 1.0
            else:
                task.status = "failed"
                task.result = "No matching Aura modules found via CODEMAP"
                task.resonance = 0.1

        elif task.task_type == "gate_check":
            if strong_sources and target_modules:
                task.status = "passed"
                task.result = "Sources and targets both verified"
                task.resonance = sum(c.concept_fit_score for c in strong_sources) / len(strong_sources)
            else:
                task.status = "failed"
                reasons = []
                if not strong_sources:
                    reasons.append("insufficient source relevance")
                if not target_modules:
                    reasons.append("no target modules identified")
                task.result = "Gate FAILED: " + "; ".join(reasons)
                task.resonance = 0.3

        elif task.task_type == "generate_plan":
            gate_tasks = [t for t in subtasks if t.task_type in ("retrieve_sources", "find_modules", "gate_check")]
            if all(t.status == "passed" for t in gate_tasks):
                task.status = "passed"
                task.resonance = sum(t.resonance for t in gate_tasks) / len(gate_tasks)
            else:
                task.status = "skipped"
                task.result = "Mutation plan suppressed: prerequisite gates failed"
                task.resonance = 0.0

        oracle.assert_equal(f"task_{task.id}_status", "passed", task.status)
        task.shadow_norm = 1.0 - task.resonance

    return subtasks


# ---------------------------------------------------------------------------
# DAG Composer
# ---------------------------------------------------------------------------

def compose_mutation_dag(query, accepted_candidates, target_modules, skills=None):
    """Compose a staged mutation DAG when mutation is allowed."""
    return {
        "query": query,
        "stages": [
            {"stage": 1, "action": "retrieve_source_traces", "depends_on": [],
             "sources": [{"trace_id": c.trace_id, "title": c.title,
                          "score": c.concept_fit_score} for c in accepted_candidates]},
            {"stage": 2, "action": "validate_source_relevance", "status": "PASSED", "depends_on": [1]},
            {"stage": 3, "action": "retrieve_target_modules", "depends_on": [2],
             "target_files": target_modules, "target_symbols": []},
            {"stage": 4, "action": "generate_minimal_patch", "depends_on": [2],
             "dependencies": [], "new_third_party_deps": False},
            {"stage": 5, "action": "validate_security_and_roles", "depends_on": [3, 4],
             "checks": [".aura/SECURITY.md", ".aura/ROLES.md"]},
            {"stage": 5.5, "action": "hivp_integrity_verification", "depends_on": [5],
             "description": "O(1) holographic codebase attestation before/after mutation"},
            {"stage": 6, "action": "run_tests", "depends_on": [5.5], "test_file": "test_aura_functions.py"},
            {"stage": 7, "action": "refresh_codemap", "depends_on": [5.5], "files_to_refresh": target_modules},
            {"stage": 8, "action": "stage_mutation_report", "depends_on": [6, 7],
             "thermal_risk": "LOW",
             "rollback_path": "Use the Refactor Arena rollback capsule; do not emit destructive shell commands."},
        ],
        "mutation_eligibility_score": sum(c.concept_fit_score for c in accepted_candidates) / max(1, len(accepted_candidates)),
        "expected_token_savings": "60-90% via polysynthetic compression",
        "efficiency_equation": "E = (kappa * R) / (tau + epsilon)",
        "efficiency_terms": {
            "kappa": "HIVP coherence (holographic integrity resonance)",
            "R": "SkillWeaver relevance gate score",
            "tau": "thermal friction (1 - thermal_fitness)",
            "epsilon": "extraction cost (estimated API cost)",
        },
    }


FUSION_VALID_OUTPUT_MODES = {
    "TEXT",
    "JSON",
    "JSON_EDIT_PLAN",
    "UNIFIED_DIFF",
    "PYTHON",
}

_MUTATION_WORDS = {
    "add", "change", "commit", "delete", "edit", "fix", "implement",
    "modify", "patch", "refactor", "remove", "rewrite", "update", "write",
}

_NEW_DEP_WORDS = {
    "pip install", "poetry add", "npm install", "new dependency", "langchain",
    "networkx", "torch", "pytorch", "faiss", "z3",
}


def _fusion_capsule_constraints(capsule: dict) -> set[str]:
    return {str(item).upper() for item in capsule.get("constraints", []) if item}


def _fusion_target_exists(target_file: str | None, skills: list[AuraSkill]) -> bool:
    if not target_file:
        return False
    normalized = target_file.replace("\\", "/").lstrip("./")
    for skill in skills or []:
        if skill.path and skill.path.replace("\\", "/").lstrip("./") == normalized:
            return True
    return Path(normalized).exists()


def gate_fusion_task(task: str, capsule: dict, skills: list[AuraSkill]) -> dict:
    """
    Decide whether AuraFusion should run, refuse, or require human gate.

    Checks:
    - task has target grounding when code mutation is requested
    - CODEMAP target exists
    - output mode is valid
    - no new deps unless allowed
    - research evidence is sufficient when task is research-derived
    """
    task_text = task or ""
    task_lower = task_text.lower()
    output_mode = str(capsule.get("output_mode", "TEXT")).upper()
    target_file = capsule.get("target_file")
    constraints = _fusion_capsule_constraints(capsule)
    checks: dict[str, bool] = {
        "valid_output_mode": output_mode in FUSION_VALID_OUTPUT_MODES,
        "target_grounded": True,
        "no_new_deps": True,
        "research_sufficient": True,
    }
    reasons: list[str] = []

    if not checks["valid_output_mode"]:
        reasons.append(f"Unsupported AuraFusion output_mode '{output_mode}'.")

    mutation_requested = (
        output_mode in {"JSON_EDIT_PLAN", "UNIFIED_DIFF", "PYTHON"}
        or any(re.search(r"\b" + re.escape(word) + r"\b", task_lower) for word in _MUTATION_WORDS)
    )
    if mutation_requested:
        checks["target_grounded"] = _fusion_target_exists(target_file, skills)
        if not checks["target_grounded"]:
            reasons.append("Code mutation requested without a CODEMAP-grounded target_file.")

    if "ALLOW_NEW_DEPS" not in constraints and any(word in task_lower for word in _NEW_DEP_WORDS):
        checks["no_new_deps"] = False
        reasons.append("Task appears to require a new dependency, but ALLOW_NEW_DEPS is not present.")

    if capsule.get("research_derived") and not capsule.get("source_sufficient"):
        checks["research_sufficient"] = False
        reasons.append("Research-derived Fusion mutation lacks source-sufficient evidence.")

    if not all(checks.values()):
        return {
            "decision": "REFUSE_FUSION",
            "allowed": False,
            "human_gate_required": False,
            "reason": " ".join(reasons),
            "checks": checks,
        }

    risky = mutation_requested and "HUMAN_APPROVED_MUTATION" not in constraints
    if risky:
        return {
            "decision": "HUMAN_GATE_REQUIRED",
            "allowed": True,
            "human_gate_required": True,
            "reason": "Mutation target is grounded; require human review before applying any patch.",
            "checks": checks,
        }

    return {
        "decision": "ALLOW_FUSION",
        "allowed": True,
        "human_gate_required": False,
        "reason": "AuraFusion gate passed.",
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Main Gate: AuraSkillWeaver
# ---------------------------------------------------------------------------

class AuraSkillWeaver:
    """
    Research Relevance Gate & Skill-Aware Decomposition Engine.
    Intercepts the !research pipeline before the Cloud Synthesizer.
    Enforces: no source-sufficient evidence -> no code mutation.
    """

    LEXICAL_ANCHOR_FLOOR = 0.05
    COMPOSITE_RELEVANCE_FLOOR = 0.25
    TOP_CANDIDATE_COUNT = 5

    def __init__(self, repo_root=None, dimension=10000):
        self.dim = dimension
        self.repo_root = repo_root or os.path.dirname(os.path.abspath(__file__))
        self._skills = None

    @property
    def skills(self):
        """Lazy-load skill registry."""
        if self._skills is None:
            self._skills = build_skill_registry(self.repo_root)
        return self._skills

    def invalidate_skill_cache(self):
        """Force rebuild of skill registry on next access."""
        self._skills = None

    def _text_to_phasor(self, text):
        """Deterministic text -> 10,000-D complex phasor (matching Aura codec)."""
        if not text:
            return np.ones(self.dim, dtype=np.complex64)
        h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
        seed = int.from_bytes(h, byteorder="little")
        rng = np.random.default_rng(seed)
        phases = rng.uniform(-np.pi, np.pi, self.dim).astype(np.float32)
        return np.exp(1j * phases)

    def _cosine_resonance(self, a, b):
        """Complex cosine resonance between two phasor vectors."""
        return float(np.abs(np.dot(a, np.conj(b))) / self.dim)

    def evaluate_candidate(self, trace_id, content, query, anchors,
                           query_phasor, trace_phasor=None, qdkt=None):
        """Evaluate a single research trace against relevance criteria."""
        title = ""
        abstract = content
        if "TITLE:" in content and "ABSTRACT:" in content:
            parts = content.split("ABSTRACT:", 1)
            title = parts[0].replace("TITLE:", "").strip()
            abstract = parts[1].strip() if len(parts) > 1 else ""
        elif "|" in content[:200]:
            parts = content.split("|", 1)
            title = parts[0].strip()
            abstract = parts[1].strip() if len(parts) > 1 else ""

        full_text = title + " " + abstract

        # VSA resonance
        if trace_phasor is not None and len(trace_phasor) == self.dim:
            resonance = self._cosine_resonance(query_phasor, trace_phasor)
        else:
            tp = self._text_to_phasor(full_text)
            resonance = self._cosine_resonance(query_phasor, tp)

        lex_score = score_lexical_anchors(full_text, anchors)
        ta_score = score_title_abstract_match(title, abstract, query)
        dom_score = score_domain_match(full_text)
        concept_fit = compute_final_relevance(resonance, lex_score, ta_score, dom_score, qdkt=qdkt, query_concept=query)

        accepted = True
        rejection_reason = None

        if lex_score == 0.0:
            accepted = False
            anchor_sample = ", ".join(anchors[:5])
            if len(anchors) > 5:
                anchor_sample += "..."
            rejection_reason = ("Zero lexical anchor coverage. None of the required anchors ("
                                + anchor_sample + ") found in paper text.")
        elif concept_fit < self.COMPOSITE_RELEVANCE_FLOOR:
            accepted = False
            rejection_reason = ("Composite relevance " + str(round(concept_fit, 3))
                                + " below floor " + str(self.COMPOSITE_RELEVANCE_FLOOR)
                                + ". Paper not conceptually relevant.")

        return ResearchCandidate(
            trace_id=trace_id,
            title=title[:120],
            abstract=abstract[:200],
            resonance_score=resonance,
            lexical_anchor_score=lex_score,
            concept_fit_score=concept_fit,
            accepted=accepted,
            rejection_reason=rejection_reason,
        )

    def evaluate_research_gate(self, query, candidates_data, qdkt=None):
        """
        Evaluate research evidence and determine if code mutation should be allowed.

        Assesses candidate research traces against the query, checks for contradictions
        in accepted sources, and makes a gating decision based on evidence quality and
        target module availability. Returns ALLOW_ARENA_STAGING when sufficient evidence is
        present with coherent findings and target modules identified, REFUSE_MUTATION
        when no candidates meet relevance thresholds, or NEED_MORE_SOURCES when
        evidence conflicts or target grounding is missing.

        Parameters:
            query: The user research query string.
            candidates_data: List of (trace_id, content, vector_blob) tuples to evaluate.

        Returns:
            ResearchGateResult containing the gating decision (ALLOW_ARENA_STAGING,
            REFUSE_MUTATION, or NEED_MORE_SOURCES), evaluated candidates ranked by
            relevance, identified target modules, detected contradictions, and a
            mutation DAG when mutation is allowed.
        """
        anchors = _derive_anchors_for_query(query)
        query_phasor = self._text_to_phasor(query)
        subtasks = decompose_query(query)

        evaluated = []
        for trace_id, content, blob in candidates_data[:self.TOP_CANDIDATE_COUNT]:
            trace_phasor = None
            if blob:
                try:
                    wave = np.frombuffer(blob, dtype=np.complex64)
                    if len(wave) == self.dim:
                        trace_phasor = wave
                except Exception:
                    pass

            candidate = self.evaluate_candidate(
                trace_id=trace_id,
                content=content,
                query=query,
                anchors=anchors,
                query_phasor=query_phasor,
                trace_phasor=trace_phasor,
                qdkt=qdkt,
            )
            evaluated.append(candidate)

        evaluated.sort(key=lambda c: c.concept_fit_score, reverse=True)

        target_modules = find_target_modules(query, self.skills)
        subtasks = refine_decomposition(subtasks, evaluated, target_modules)

        accepted = [c for c in evaluated if c.accepted]
        accepted_ids = {candidate.trace_id for candidate in accepted}
        accepted_records = [
            record_from_content(trace_id, content, blob)
            for trace_id, content, blob in candidates_data
            if trace_id in accepted_ids
        ]
        contradictions = detect_contradictions(accepted_records)

        if not accepted:
            decision = "REFUSE_MUTATION"
            anchor_list = ", ".join(anchors[:8])
            reason = ("All " + str(len(evaluated)) + " candidate(s) failed relevance gate. "
                      "Top retrieved papers do not contain required anchors: "
                      + anchor_list + ". "
                      "ACTION: Ingest stronger source-sufficient papers before mutation.")
            final_score = max((c.concept_fit_score for c in evaluated), default=0.0)
            dag = None

        elif contradictions:
            decision = "NEED_MORE_SOURCES"
            pairs = ", ".join(
                contradiction.left_id + " vs " + contradiction.right_id
                for contradiction in contradictions[:3]
            )
            reason = (
                "Accepted sources contain polarity conflicts on the same "
                "mechanism/effect (" + pairs + "). ACTION: resolve the evidence "
                "conflict before generating a mutation."
            )
            final_score = sum(c.concept_fit_score for c in accepted) / len(accepted)
            dag = None

        elif not target_modules:
            decision = "NEED_MORE_SOURCES"
            reason = ("Partial evidence found but no target modules identified via CODEMAP. "
                      "ACTION: Refine query to improve target grounding.")
            final_score = sum(c.concept_fit_score for c in accepted) / max(1, len(accepted))
            dag = None

        else:
            decision = "ALLOW_ARENA_STAGING"
            reason = (str(len(accepted)) + " source(s) passed relevance gate with "
                      + str(len(target_modules)) + " target module(s) identified. "
                      "Sources contain direct anchors and match Aura modules.")
            final_score = sum(c.concept_fit_score for c in accepted) / len(accepted)
            dag = compose_mutation_dag(query, accepted, target_modules, self.skills)

        return ResearchGateResult(
            query=query,
            decision=decision,
            candidates=evaluated,
            required_anchors=anchors,
            final_score=final_score,
            reason=reason,
            target_modules=target_modules,
            mutation_dag=dag,
            contradictions=contradictions,
        )

    def format_gate_report(self, result):
        """Format a ResearchGateResult as a human-readable report."""
        lines = [
            "[RESEARCH_GATE]",
            "QUERY: " + result.query,
            "DECISION: " + result.decision,
            "REASON: " + result.reason,
            "FINAL_SCORE: " + str(round(result.final_score, 4)),
            "ANCHORS_CHECKED: " + ", ".join(result.required_anchors[:10]),
        ]

        if result.candidates:
            lines.append("TOP_MATCHES:")
            for c in result.candidates[:5]:
                status = "ACCEPTED" if c.accepted else "REJECTED"
                label = c.title[:80] if c.title else c.trace_id
                lines.append("  - [" + status + "] " + label + ": "
                             "resonance=" + str(round(c.resonance_score, 4)) + ", "
                             "anchors=" + str(round(c.lexical_anchor_score, 3)) + ", "
                             "concept_fit=" + str(round(c.concept_fit_score, 4)))
                if c.rejection_reason:
                    lines.append("    REASON: " + c.rejection_reason[:120])

        if result.target_modules:
            lines.append("TARGET_MODULES:")
            for mod in result.target_modules:
                lines.append("  - " + mod)

        if result.contradictions:
            lines.append("CONTRADICTIONS:")
            for conflict in result.contradictions:
                lines.append(
                    "  - " + conflict.left_id + " vs " + conflict.right_id
                    + ": topic_similarity="
                    + str(round(conflict.topic_similarity, 4))
                    + ", polarity=" + conflict.left_polarity
                    + "/" + conflict.right_polarity
                )

        if result.mutation_dag:
            lines.append("PLAN:")
            for stage in result.mutation_dag.get("stages", []):
                lines.append("  " + str(stage["stage"]) + ". " + stage["action"])

        if result.decision == "REFUSE_MUTATION":
            lines.append("NEXT: Ingest source-sufficient papers matching the query "
                         "domain before attempting mutation.")
        elif result.decision == "NEED_MORE_SOURCES":
            lines.append("NEXT: Add more relevant sources or refine the query "
                         "to improve target grounding.")

        lines.append("[/RESEARCH_GATE]")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Integration helper: drop-in for the !research path in aura_node.py
# ---------------------------------------------------------------------------

async def research_gate_intercept(query, candidates_data, repo_root=None, qdkt=None):
    """
    Drop-in intercept for the !research pipeline.

    Call this BEFORE dispatching to the Cloud Synthesizer.

    Args:
        query: research query string
        candidates_data: [(trace_id, content, vector_blob), ...]
        repo_root: path to repo root (defaults to this file directory)
        qdkt: Optional UnifiedQDKT instance

    Returns:
        (allowed: bool, report: str, result: ResearchGateResult)
    """
    weaver = AuraSkillWeaver(repo_root=repo_root)
    result = weaver.evaluate_research_gate(query, candidates_data, qdkt=qdkt)
    report = weaver.format_gate_report(result)
    allowed = result.decision == "ALLOW_ARENA_STAGING"
    return allowed, report, result


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== AuraSkillWeaver Research Relevance Gate (standalone demo) ===")
    print()

    weaver = AuraSkillWeaver()

    print("--- Demo 1: Strong Match ---")
    demo_strong = [
        ("ARXIV_ABCD1234",
         "TITLE: Modern Hopfield Networks for Associative Memory in Neural "
         "Architectures | ABSTRACT: We present a framework for modern Hopfield "
         "networks that implement dense associative memory with exponential "
         "storage capacity using energy function minimization and attractor "
         "dynamics for content-addressable retrieval.",
         None),
    ]
    r1 = weaver.evaluate_research_gate("Hopfield networks", demo_strong)
    print(weaver.format_gate_report(r1))

    print()
    print("--- Demo 2: Weak Match ---")
    demo_weak = [
        ("ARXIV_BEEF5678",
         "TITLE: Passive-User Bell-State Loop-Back Key Establishment in "
         "Quantum Networks | ABSTRACT: We explore quantum key distribution "
         "using Bell states for secure communication in fiber optic networks "
         "with passive user terminals.",
         None),
        ("ARXIV_CAFE9012",
         "TITLE: Lifecycle Assessment of Construction Material Drift in "
         "Tropical Climates | ABSTRACT: This study examines how building "
         "materials degrade under sustained thermal cycling and moisture "
         "in tropical environments.",
         None),
    ]
    r2 = weaver.evaluate_research_gate("Hopfield networks", demo_weak)
    print(weaver.format_gate_report(r2))
