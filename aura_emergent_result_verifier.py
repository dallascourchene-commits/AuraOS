"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa40-[Q-SYS:EMERGENT_RESULT_VERIFIER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Read-Only Verified Cluster Report)
DEPENDENCIES: __future__, dataclasses, hashlib, json, re, typing
FUNCTIONS: EmergentVerificationConfig, EmergentVerificationResult, EmergentCandidateCluster,
           EmergentCandidateVerdict, RepresentativeScore,
           verify_emergent_connections, cluster_emergent_connections,
           score_focus, score_evidence, score_representative,
           canonicalize_aura_path, cluster_key_for_connection,
           render_verified_emergent_report
SYNOPSIS: Verify, cluster, deduplicate, MMR-rerank, and render emergent capability candidates
after aura_emergent_potential_repl discovers them. Advisory layers (J-Space, ST3GG egress,
symbolic trace memory) improve focus/cluster explanations but never replace exact source spans,
source hashes, tests, or verifier gates as patch authority.
SAFETY: NO_PATCHES | NO_CODE_WRITES | NO_UNIFIED_DIFF | NO_AUTOWIRING | REPORT_ONLY
[/AURA_MASTER_KEY]
"""
# Design note: this module deliberately does NOT import aura_emergent_potential_repl at module
# level to avoid the circular import that would arise when the REPL imports this verifier.
# All connection objects are accepted as Any / dict-like; callers pass real EmergentConnection
# instances and they are handled via attribute/key access helpers below.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Version / safety constants
# ---------------------------------------------------------------------------

VERIFIER_VERSION = "AURA_EMERGENT_RESULT_VERIFIER_V1"
PATCH_AUTHORITY_POLICY = "exact_source_spans_and_hashes_only"
READ_ONLY_CONSTRAINTS = (
    "NO_PATCHES",
    "NO_CODE_WRITES",
    "NO_UNIFIED_DIFF",
    "NO_AUTOWIRING",
    "REPORT_ONLY",
)
AUDIT_ROUTE = "EMERGENT_CAPABILITY_AUDIT"
STATUS_FUTURE_PATCHABLE = "FUTURE_PATCHABLE"
STATUS_NEEDS_GROUNDING = "NEEDS_GROUNDING"

# ---------------------------------------------------------------------------
# Focus scoring: generic stop terms removed before any token overlap scoring
# ---------------------------------------------------------------------------

_FOCUS_STOP_TERMS: frozenset[str] = frozenset(
    {
        "aura", "capability", "emergent", "future", "potential",
        "high", "leverage", "exact", "system", "code", "the",
        "and", "for", "with", "from", "that", "this",
    }
)

# Role-specific "strong" terms carry 2× weight
_STRONG_ROLE_TERMS: dict[str, frozenset[str]] = {
    "st3gg":      frozenset({"st3gg", "token", "compression", "fidelity", "benchmark", "codec", "budget"}),
    "topology":   frozenset({"topological", "source_span", "codetopo", "codemap", "context_anchor"}),
    "localizer":  frozenset({"localize", "ground", "fallback", "fault", "localization"}),
    "router":     frozenset({"route", "router", "model", "provider", "budget_route"}),
    "capsule":    frozenset({"capsule", "compile", "action", "builder_context", "actcapsule"}),
    "research":   frozenset({"research", "manifest", "paper", "acceptance_test", "ingest"}),
    "empirical":  frozenset({"empirical", "define_empirical", "ucb", "scoreable", "candidate_tree"}),
    "verifier":   frozenset({"verify", "verification", "quality_gate", "pytest", "test_gap"}),
    "benchmark":  frozenset({"benchmark", "efficiency", "metric", "score", "harness"}),
}

_ALL_STRONG_TERMS: frozenset[str] = frozenset().union(*_STRONG_ROLE_TERMS.values())

# ---------------------------------------------------------------------------
# Representative symbol preference / penalty rules
# ---------------------------------------------------------------------------

# Preferred symbols by pattern — checked with startswith/exact match
_PREFERRED_SYMBOL_PATTERNS: tuple[str, ...] = (
    "ground_coding_arena_intent",
    "topological_context_fallback_candidates",
    "CodeTopoAnchor",
    "ArchitectModelRouter",
    "AuraCodingArenaRouter",
    "AutoRouter",
    "route_model",
    "ActCapsule",
    "AgentIRCompiler",
    "compile_action_capsule",
    "convert_",
    "build_builder_context_packet",
    "ingest_research_manifest",
    "run_manifest_ingest_bridge",
    "define_empirical_task",
    "ResonantTestOracle",
    "run_test",
    "score_",
)

# Hard-penalised symbols — score multiplied by 0.10 unless focus explicitly mentions override
_PENALISED_SYMBOL_PATTERNS: tuple[str, ...] = (
    "parse_emerge_command",
    "to_dict",
    "from_dict",
    "__init__",
    "main",
)

# These prefixes indicate mock/fixture/demo symbols
_MOCK_PREFIXES: tuple[str, ...] = ("Mock", "mock_", "Fake", "fake_", "demo_", "fixture_")

# Focus terms that unlock penalised symbols
_PENALISE_OVERRIDE_TERMS: frozenset[str] = frozenset(
    {"command", "parser", "repl", "cli", "syntax", "parse"}
)
_TEST_OVERRIDE_TERMS: frozenset[str] = frozenset({"test", "mock", "fixture", "tests"})
_EXTERNAL_OVERRIDE_TERMS: frozenset[str] = frozenset(
    {"external", "api", "hotswap", "rollback", "network", "deployment"}
)

# MMR: similarity thresholds used to compute pairwise cluster similarity
_SIM_SAME_ABILITY = 0.90
_SIM_SAME_ROLE_PAIR = 0.70
_SIM_SAME_FILE = 0.40
_SIM_SHARED_SYMBOL = 0.30
_SIM_DEFAULT = 0.10

# ST3GG egress minimum savings ratio to enable compact output
_ST3GG_MIN_SAVINGS_RATIO = 0.20

# Trace memory event types
_TRACE_EVENT_VERIFIED_CLUSTER = "emergent_verified_cluster"
_TRACE_EVENT_SUPPRESSED = "emergent_suppressed_duplicate"
_TRACE_EVENT_REJECTED = "emergent_rejected_candidate"
_TRACE_EVENT_FUTURE_POTENTIAL = "emergent_future_potential"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EmergentVerificationConfig:
    max_clusters: int = 8
    max_alternates_per_cluster: int = 3
    min_focus_score: float = 0.20
    min_evidence_score: float = 0.50
    mmr_lambda: float = 0.72
    suppress_mirrored_paths: bool = True
    reject_weak_representatives: bool = True
    allow_test_symbols: bool = False
    # J-Space advisory weight added to final_score (capped internally)
    jspace_advisory_weight: float = 0.10
    # ST3GG egress: only compress when savings >= threshold
    st3gg_min_savings_ratio: float = _ST3GG_MIN_SAVINGS_RATIO
    # Trace memory: best-effort recording path (None = skip)
    trace_memory_root: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepresentativeScore:
    symbol: str
    file: str
    score: float
    reasons: list[str] = field(default_factory=list)
    is_preferred: bool = False
    is_penalized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentCandidateVerdict:
    connection_id: str
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    focus_score: float = 0.0
    evidence_score: float = 0.0
    representative_score: float = 0.0
    novelty_score: float = 0.0
    jspace_focus_score: float = 0.0
    jspace_active_concepts: list[str] = field(default_factory=list)
    jspace_route_context: str = ""
    jspace_warnings: list[str] = field(default_factory=list)
    final_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentCandidateCluster:
    cluster_id: str
    cluster_title: str
    emergent_ability: str
    source_role: str
    target_role: str
    missing_wire: str
    best_connection: dict[str, Any]
    alternates: list[dict[str, Any]] = field(default_factory=list)
    suppressed_duplicate_count: int = 0
    rejected_count: int = 0
    verifier_notes: list[str] = field(default_factory=list)
    final_score: float = 0.0
    safe_to_patch: bool = False
    # J-Space advisory fields
    jspace_advisory_concepts: list[str] = field(default_factory=list)
    jspace_route_context: str = ""
    # ST3GG egress fields
    st3gg_egress_enabled: bool = False
    st3gg_savings_ratio: float = 0.0
    st3gg_pointer: str = ""
    original_report_hash: str = ""
    # Trace memory IDs
    trace_atom_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentVerificationResult:
    version: str = VERIFIER_VERSION
    raw_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    suppressed_duplicate_count: int = 0
    cluster_count: int = 0
    clusters: list[EmergentCandidateCluster] = field(default_factory=list)
    rejected_candidates: list[EmergentCandidateVerdict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    # Advisory overlay summaries
    jspace_summary: dict[str, Any] = field(default_factory=dict)
    st3gg_egress: dict[str, Any] = field(default_factory=dict)
    trace_atom_ids: list[str] = field(default_factory=list)
    verifier_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "raw_count": self.raw_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "suppressed_duplicate_count": self.suppressed_duplicate_count,
            "cluster_count": self.cluster_count,
            "clusters": [c.to_dict() for c in self.clusters],
            "rejected_candidates": [v.to_dict() for v in self.rejected_candidates],
            "warnings": self.warnings,
            "summary": self.summary,
            "jspace_summary": self.jspace_summary,
            "st3gg_egress": self.st3gg_egress,
            "trace_atom_ids": self.trace_atom_ids,
            "verifier_summary": self.verifier_summary,
        }


# ---------------------------------------------------------------------------
# Internal attribute helpers (work with both dataclass and dict connections)
# ---------------------------------------------------------------------------

def _get(obj: Any, key: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _src(connection: Any) -> dict[str, str]:
    val = _get(connection, "source", {})
    return val if isinstance(val, dict) else {}


def _tgt(connection: Any) -> dict[str, str]:
    val = _get(connection, "target", {})
    return val if isinstance(val, dict) else {}


def _evidence(connection: Any) -> list[dict[str, Any]]:
    val = _get(connection, "evidence", [])
    return list(val) if val else []


def _connection_dict(connection: Any) -> dict[str, Any]:
    if isinstance(connection, dict):
        return connection
    try:
        return asdict(connection)
    except Exception:
        return {k: getattr(connection, k, None) for k in (
            "connection_id", "source", "target", "missing_wire",
            "emergent_ability", "evidence", "confidence",
            "implementation_feasibility", "verifier_readiness",
            "token_reduction_potential", "safety_risk", "cost_risk",
            "status", "required_tests", "future_patch_capsule_hint",
            "emergence_score", "score_breakdown",
        )}


# ---------------------------------------------------------------------------
# Path canonicalization
# ---------------------------------------------------------------------------

def canonicalize_aura_path(path: str) -> str:
    """
    Collapse mirrored paths such as ``AuraOS/foo.py`` → ``foo.py``.

    Rules applied in order:
    1. Backslash → forward slash.
    2. Strip leading ``./``.
    3. Strip ``AuraOS/`` prefix (the repo's top-level mirror directory).
    4. Strip any remaining leading slash.
    """
    if not path:
        return path
    p = path.replace("\\", "/")
    p = re.sub(r"^\./", "", p)
    p = re.sub(r"^AuraOS/", "", p, flags=re.IGNORECASE)
    p = p.lstrip("/")
    return p


def _canonical_file(file_path: str) -> str:
    return canonicalize_aura_path(str(file_path or ""))


# ---------------------------------------------------------------------------
# Cluster key
# ---------------------------------------------------------------------------

_ROLE_NORMALISE: dict[str, str] = {
    "localizer": "localizer",
    "localize": "localizer",
    "localization": "localizer",
    "repo_localizer": "localizer",
    "grounding": "localizer",
    "fallback_candidate": "localizer",
    "model_router": "model_router",
    "router": "model_router",
    "route": "model_router",
    "routing": "model_router",
    "topology": "topology",
    "topological": "topology",
    "codetopo": "topology",
    "codemap": "topology",
    "research_manifest": "research_manifest",
    "research": "research_manifest",
    "empirical_lab": "empirical_lab",
    "empirical": "empirical_lab",
    "coding_arena": "coding_arena",
    "arena": "coding_arena",
    "capsule_compiler": "capsule_compiler",
    "capsule": "capsule_compiler",
    "compiler": "capsule_compiler",
    "test_runner": "test_runner",
    "verifier": "test_runner",
    "memory": "memory",
    "external_api": "external_api",
    "hotswap": "hotswap",
}


def _normalize_role(role: str) -> str:
    key = role.lower().strip()
    return _ROLE_NORMALISE.get(key, key)


def cluster_key_for_connection(connection: Any) -> tuple[str, str, str, str]:
    """
    Derive a cluster key: ``(emergent_ability, src_role, tgt_role, missing_wire)``.

    Role strings are normalised via ``_normalize_role`` so that synonymous roles
    (e.g. ``localizer`` / ``repo_localizer`` / ``grounding``) land in the same cluster.
    """
    ability = str(_get(connection, "emergent_ability", ""))
    missing = str(_get(connection, "missing_wire", ""))
    src = _src(connection)
    tgt = _tgt(connection)
    src_role = _normalize_role(str(src.get("role", "") or src.get("subsystem", "") or ""))
    tgt_role = _normalize_role(str(tgt.get("role", "") or tgt.get("subsystem", "") or ""))
    return (ability, src_role, tgt_role, missing)


# ---------------------------------------------------------------------------
# Focus scoring
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


def _focus_tokens(focus: str) -> list[str]:
    raw = _tokenize(focus)
    return [t for t in raw if t not in _FOCUS_STOP_TERMS and len(t) >= 3]


def _candidate_text(connection: Any) -> str:
    parts = [
        str(_get(connection, "emergent_ability", "")),
        str(_get(connection, "missing_wire", "")),
        str(_src(connection).get("file", "")),
        str(_src(connection).get("symbol", "")),
        str(_src(connection).get("role", "")),
        str(_tgt(connection).get("file", "")),
        str(_tgt(connection).get("symbol", "")),
        str(_tgt(connection).get("role", "")),
        str(_get(connection, "status", "")),
    ]
    ev_list = _evidence(connection)
    for ev in ev_list[:3]:
        if isinstance(ev, dict):
            parts.append(str(ev.get("source_hash", "")))
            parts.append(str(ev.get("file", "")))
    return " ".join(p for p in parts if p)


def score_focus(connection: Any, focus: str) -> float:
    """
    Compute a weighted focus-alignment score in [0.0, 1.0].

    - Tokens matching a strong role-specific term receive 2× weight.
    - Generic stop terms are removed before scoring.
    - Returns 1.0 (no penalty) when focus is empty.
    """
    if not focus or not focus.strip():
        return 1.0
    focus_toks = set(_focus_tokens(focus))
    if not focus_toks:
        return 1.0
    cand_text = _candidate_text(connection)
    cand_toks = set(_tokenize(cand_text))
    if not cand_toks:
        return 0.0
    matched_weight = 0.0
    for tok in focus_toks:
        if tok in cand_toks:
            if tok in _ALL_STRONG_TERMS:
                matched_weight += 2.0
            else:
                matched_weight += 1.0
    # Maximum achievable weight (all focus tokens strong)
    max_weight = sum(2.0 if t in _ALL_STRONG_TERMS else 1.0 for t in focus_toks)
    raw = matched_weight / max_weight if max_weight > 0 else 0.0
    return min(1.0, raw)


# ---------------------------------------------------------------------------
# Evidence scoring
# ---------------------------------------------------------------------------

def score_evidence(connection: Any) -> float:
    """
    Compute an evidence completeness score in [0.0, 1.0].

    Criteria (each contributes equally):
    - At least one evidence entry exists.
    - Any evidence entry has a non-empty ``source_hash``.
    - Any evidence entry has a non-empty ``start_line`` / ``end_line`` (span).
    - At least one required test is listed.
    - No evidence entry is flagged as mock/test-only.
    - Safety risk is not ``"BLOCKED"`` or ``"TOO_RISKY"``.
    """
    ev_list = _evidence(connection)
    criteria_pass = 0
    total_criteria = 6

    # 1. evidence list not empty
    if ev_list:
        criteria_pass += 1

    # 2. source_hash present in any evidence entry
    if any(bool(ev.get("source_hash") if isinstance(ev, dict) else "") for ev in ev_list):
        criteria_pass += 1

    # 3. source span (start_line or span_text) present
    span_ok = any(
        (isinstance(ev, dict) and (ev.get("start_line") or ev.get("span_text") or ev.get("source_span")))
        for ev in ev_list
    )
    if span_ok:
        criteria_pass += 1

    # 4. required tests listed
    req_tests = _get(connection, "required_tests", [])
    if req_tests:
        criteria_pass += 1

    # 5. no evidence flagged as mock/demo only
    is_mock = any(
        isinstance(ev, dict) and any(
            str(ev.get("kind", "")).lower().startswith(p.lower())
            for p in ("mock", "demo", "fixture", "fake")
        )
        for ev in ev_list
    )
    if not is_mock:
        criteria_pass += 1

    # 6. not explicitly blocked
    safety = str(_get(connection, "safety_risk", "")).upper()
    status = str(_get(connection, "status", "")).upper()
    if safety not in ("BLOCKED", "TOO_RISKY") and status not in ("TOO_RISKY", "DREAM_ONLY"):
        criteria_pass += 1

    return criteria_pass / total_criteria


# ---------------------------------------------------------------------------
# Representative scoring
# ---------------------------------------------------------------------------

def score_representative(connection: Any, *, focus: str = "", config: EmergentVerificationConfig | None = None) -> RepresentativeScore:
    """
    Score a connection's source symbol as a representative for its role.

    Returns a ``RepresentativeScore`` with a value in [0.0, 1.0].
    """
    cfg = config or EmergentVerificationConfig()
    src = _src(connection)
    symbol = str(src.get("symbol", "") or "")
    file_path = _canonical_file(str(src.get("file", "") or ""))
    score = 0.5  # baseline
    reasons: list[str] = []
    is_preferred = False
    is_penalized = False

    # ---- Preferred symbol check ----
    for pat in _PREFERRED_SYMBOL_PATTERNS:
        if symbol.startswith(pat) or symbol == pat:
            score = min(1.0, score + 0.40)
            reasons.append(f"preferred_symbol:{pat}")
            is_preferred = True
            break

    # ---- Penalty check ----
    focus_toks_lower = set(_tokenize(focus)) if focus else set()
    for pat in _PENALISED_SYMBOL_PATTERNS:
        if symbol == pat or symbol.startswith(pat):
            can_override = bool(focus_toks_lower & _PENALISE_OVERRIDE_TERMS)
            if not can_override:
                score = score * 0.10
                reasons.append(f"penalized_symbol:{pat}")
                is_penalized = True
            else:
                reasons.append(f"penalized_symbol_overridden_by_focus:{pat}")
            break

    # ---- Mock / test / fixture penalty ----
    if any(symbol.startswith(p) for p in _MOCK_PREFIXES):
        can_override = bool(focus_toks_lower & _TEST_OVERRIDE_TERMS)
        if not can_override and not cfg.allow_test_symbols:
            score = score * 0.10
            reasons.append("penalized_mock_or_fixture")
            is_penalized = True
        else:
            reasons.append("mock_allowed_by_focus_or_config")

    # Test file as source penalty
    if file_path.startswith("test_") or "/test_" in file_path:
        can_override = bool(focus_toks_lower & _TEST_OVERRIDE_TERMS)
        if not can_override and not cfg.allow_test_symbols:
            score = score * 0.30
            reasons.append("penalized_test_file_as_source")
            is_penalized = True

    # External API penalty unless explicitly requested
    src_file_lower = file_path.lower()
    is_external = any(ext in src_file_lower for ext in ("api_rotator", "mcp_gateway", "hotswap", "liquid_internet"))
    if is_external:
        can_override = bool(focus_toks_lower & _EXTERNAL_OVERRIDE_TERMS)
        if not can_override:
            score = score * 0.60
            reasons.append("penalized_external_api_path")

    return RepresentativeScore(
        symbol=symbol,
        file=file_path,
        score=min(1.0, max(0.0, score)),
        reasons=reasons,
        is_preferred=is_preferred,
        is_penalized=is_penalized,
    )


# ---------------------------------------------------------------------------
# J-Space advisory scoring
# ---------------------------------------------------------------------------

def _jspace_score(connection: Any, focus: str, config: EmergentVerificationConfig) -> tuple[float, list[str], str, list[str]]:
    """
    Compute optional J-Space advisory contribution.

    Returns (jspace_score_delta, active_concepts, route_context, warnings).
    score_delta is in [0.0, config.jspace_advisory_weight].
    J-Space never provides patch authority — score is advisory only.
    """
    try:
        from aura_jspace_codec import active_concepts_from_packet, build_jspace_packet  # local import to avoid circular
    except Exception:
        return 0.0, [], "", ["jspace_codec_unavailable"]

    warnings: list[str] = []
    # Re-use existing jspace_route if the connection packet already carries it
    jpacket_raw: dict[str, Any] | None = None
    if isinstance(connection, dict):
        jpacket_raw = connection.get("jspace_packet") or connection.get("jspace_route")
    else:
        jpacket_raw = getattr(connection, "jspace_packet", None) or getattr(connection, "jspace_route", None)

    if not jpacket_raw:
        # Build a lightweight advisory packet from connection metadata
        ability = str(_get(connection, "emergent_ability", ""))
        safety = str(_get(connection, "safety_risk", "low"))
        frame = {
            "intent": "verify" if "verif" in ability.lower() else "benchmark" if "benchmark" in ability.lower() else "explain",
            "artifact": "python_module",
            "action": "inspect",
            "scope": "subsystem",
            "risk": safety if safety in ("low", "medium", "high", "live") else "medium",
            "grounding": ("file_exists", "symbol_exists") if _evidence(connection) else (),
            "tests": "existing" if _get(connection, "required_tests", []) else "none",
            "quality": "accuracy_first",
            "cost": "no_model",
        }
        decision = {
            "route": "EMERGENT_CAPABILITY_AUDIT",
            "model": "no_model",
            "context": "AUDIT",
            "reason": "emergent_capability_audit",
            "verifier": True,
        }
        try:
            jpacket_raw = build_jspace_packet(frame, decision)
        except Exception as exc:
            warnings.append(f"jspace_build_failed:{exc}")
            return 0.0, [], "", warnings

    # Extract active concepts
    try:
        concepts_raw = active_concepts_from_packet(jpacket_raw)
        active_concepts = [str(c.get("label", c) if isinstance(c, dict) else c) for c in (concepts_raw or [])][:10]
    except Exception:
        active_concepts = []

    route_context = ""
    if isinstance(jpacket_raw, dict):
        route_context = str(jpacket_raw.get("output_compact", "") or jpacket_raw.get("next_state", ""))
    else:
        try:
            route_context = str(getattr(jpacket_raw, "output_compact", "") or getattr(jpacket_raw, "next_state", ""))
        except Exception:
            pass

    # Score: count focus tokens that also appear in active concepts
    focus_toks = set(_focus_tokens(focus))
    concept_toks: set[str] = set()
    for c in active_concepts:
        concept_toks.update(_tokenize(c))
    overlap = focus_toks & concept_toks if focus_toks else set()
    raw_ratio = len(overlap) / len(focus_toks) if focus_toks else 0.5
    delta = raw_ratio * config.jspace_advisory_weight
    return min(config.jspace_advisory_weight, delta), active_concepts, route_context, warnings


# ---------------------------------------------------------------------------
# Verdict per connection
# ---------------------------------------------------------------------------

def _verdict_for(
    connection: Any,
    *,
    focus: str,
    config: EmergentVerificationConfig,
) -> EmergentCandidateVerdict:
    conn_id = str(_get(connection, "connection_id", ""))
    focus_s = score_focus(connection, focus)
    evidence_s = score_evidence(connection)
    rep_s = score_representative(connection, focus=focus, config=config)

    jspace_delta, jspace_concepts, jspace_route_ctx, jspace_warns = _jspace_score(connection, focus, config)

    # Novelty is computed later during MMR; here we default to 1.0
    novelty_s = 1.0

    # Weighted composite (before novelty and J-Space adjustment)
    # focus: 35%, evidence: 40%, representative: 25%
    base_score = 0.35 * focus_s + 0.40 * evidence_s + 0.25 * rep_s.score
    final = min(1.0, base_score + jspace_delta)

    reasons: list[str] = []
    warnings_out: list[str] = list(jspace_warns)
    accepted = True

    if focus_s < config.min_focus_score:
        reasons.append(f"focus_score_below_threshold:{focus_s:.2f}<{config.min_focus_score}")
        accepted = False

    if evidence_s < config.min_evidence_score:
        reasons.append(f"evidence_score_below_threshold:{evidence_s:.2f}<{config.min_evidence_score}")
        accepted = False

    if config.reject_weak_representatives and rep_s.is_penalized and not rep_s.is_preferred:
        reasons.append(f"weak_representative:{rep_s.symbol}")
        accepted = False

    if accepted:
        reasons.append("verdict_accepted")

    return EmergentCandidateVerdict(
        connection_id=conn_id,
        accepted=accepted,
        reasons=reasons,
        warnings=warnings_out,
        focus_score=round(focus_s, 4),
        evidence_score=round(evidence_s, 4),
        representative_score=round(rep_s.score, 4),
        novelty_score=round(novelty_s, 4),
        jspace_focus_score=round(jspace_delta, 4),
        jspace_active_concepts=jspace_concepts,
        jspace_route_context=jspace_route_ctx,
        jspace_warnings=warnings_out,
        final_score=round(final, 4),
    )


# ---------------------------------------------------------------------------
# MMR diversity selection
# ---------------------------------------------------------------------------

def _cluster_similarity(a: EmergentCandidateCluster, b: EmergentCandidateCluster) -> float:
    if a.emergent_ability and a.emergent_ability == b.emergent_ability:
        return _SIM_SAME_ABILITY
    a_key = (a.source_role, a.target_role)
    b_key = (b.source_role, b.target_role)
    if a_key == b_key and a_key != ("", ""):
        return _SIM_SAME_ROLE_PAIR
    a_src = _canonical_file(a.best_connection.get("source", {}).get("file", ""))
    b_src = _canonical_file(b.best_connection.get("source", {}).get("file", ""))
    a_tgt = _canonical_file(a.best_connection.get("target", {}).get("file", ""))
    b_tgt = _canonical_file(b.best_connection.get("target", {}).get("file", ""))
    if (a_src and a_src == b_src) or (a_tgt and a_tgt == b_tgt):
        return _SIM_SAME_FILE
    a_sym = a.best_connection.get("source", {}).get("symbol", "")
    b_sym = b.best_connection.get("source", {}).get("symbol", "")
    if a_sym and a_sym == b_sym:
        return _SIM_SHARED_SYMBOL
    return _SIM_DEFAULT


def _mmr_select(clusters: list[EmergentCandidateCluster], *, lam: float, k: int) -> list[EmergentCandidateCluster]:
    """Maximal Marginal Relevance selection over cluster list."""
    if not clusters or k <= 0:
        return []
    remaining = list(clusters)
    selected: list[EmergentCandidateCluster] = []
    while remaining and len(selected) < k:
        if not selected:
            best = max(remaining, key=lambda c: c.final_score)
        else:
            def mmr_score(c: EmergentCandidateCluster) -> float:
                max_sim = max(_cluster_similarity(c, s) for s in selected)
                return lam * c.final_score - (1.0 - lam) * max_sim
            best = max(remaining, key=mmr_score)
        selected.append(best)
        remaining.remove(best)
    return selected


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def cluster_emergent_connections(
    connections: Sequence[Any],
    *,
    focus: str = "",
    config: EmergentVerificationConfig | None = None,
) -> list[EmergentCandidateCluster]:
    """
    Group accepted connections into architectural clusters, then MMR-rerank.

    Clusters are keyed by ``(emergent_ability, src_role, tgt_role, missing_wire)``.
    Within each cluster:
    - Best representative = highest ``final_score``.
    - Up to ``config.max_alternates_per_cluster`` alternates.
    - Remaining candidates count as suppressed duplicates.
    """
    cfg = config or EmergentVerificationConfig()
    groups: dict[tuple[str, str, str, str], list[tuple[Any, EmergentCandidateVerdict]]] = {}
    rejected_in_cluster: dict[tuple[str, str, str, str], int] = {}

    for conn in connections:
        key = cluster_key_for_connection(conn)
        verdict = _verdict_for(conn, focus=focus, config=cfg)
        if not verdict.accepted:
            rejected_in_cluster[key] = rejected_in_cluster.get(key, 0) + 1
            continue
        groups.setdefault(key, []).append((conn, verdict))

    clusters: list[EmergentCandidateCluster] = []
    for key, members in groups.items():
        ability, src_role, tgt_role, missing_wire = key
        members.sort(key=lambda x: -x[1].final_score)
        best_conn, best_verdict = members[0]
        alternates = [_connection_dict(c) for c, _ in members[1: 1 + cfg.max_alternates_per_cluster]]
        suppressed = max(0, len(members) - 1 - cfg.max_alternates_per_cluster)
        rejected = rejected_in_cluster.get(key, 0)

        notes: list[str] = []
        ev_score = best_verdict.evidence_score
        if ev_score >= 0.83:
            notes.append("high_evidence")
        elif ev_score >= 0.50:
            notes.append("medium_evidence")
        else:
            notes.append("low_evidence")
        if best_verdict.representative_score >= 0.80:
            notes.append("good_representative")
        if best_verdict.jspace_focus_score > 0:
            notes.append(f"jspace_advisory_delta:{best_verdict.jspace_focus_score:.3f}")
        if suppressed:
            notes.append(f"suppressed_duplicates:{suppressed}")

        # Determine safe_to_patch from the best connection's status
        status = str(_get(best_conn, "status", "")).upper()
        patchable = status == "FUTURE_PATCHABLE" and ev_score >= cfg.min_evidence_score

        cluster_id = _stable_id(f"{ability}:{src_role}:{tgt_role}:{missing_wire}")

        cluster = EmergentCandidateCluster(
            cluster_id=cluster_id,
            cluster_title=ability or f"{src_role} -> {tgt_role}",
            emergent_ability=ability,
            source_role=src_role,
            target_role=tgt_role,
            missing_wire=missing_wire,
            best_connection=_connection_dict(best_conn),
            alternates=alternates,
            suppressed_duplicate_count=suppressed,
            rejected_count=rejected,
            verifier_notes=notes,
            final_score=round(best_verdict.final_score, 4),
            safe_to_patch=patchable,
            jspace_advisory_concepts=best_verdict.jspace_active_concepts,
            jspace_route_context=best_verdict.jspace_route_context,
        )
        clusters.append(cluster)

    clusters.sort(key=lambda c: -c.final_score)
    return _mmr_select(clusters, lam=cfg.mmr_lambda, k=cfg.max_clusters)


# ---------------------------------------------------------------------------
# ST3GG egress (advisory, optional)
# ---------------------------------------------------------------------------

def _st3gg_egress_for_report(
    report_text: str,
    *,
    config: EmergentVerificationConfig,
) -> dict[str, Any]:
    """
    Optionally compress the human report through ST3GG Arena egress.

    Returns metadata dict; never raises — fails closed.
    Safety: compact output is a recall pointer only.
    Exact source spans from the original report are NOT replaced.
    """
    disabled: dict[str, Any] = {
        "st3gg_egress_enabled": False,
        "st3gg_savings_ratio": 0.0,
        "st3gg_pointer": "",
        "original_report_hash": "",
    }
    if not report_text:
        return disabled
    original_hash = _hash_text(report_text)
    try:
        from aura_arena_st3gg_egress import compress_report_st3gg  # optional; may not exist
        _compressed, savings_ratio, pointer = compress_report_st3gg(report_text)
        if savings_ratio < config.st3gg_min_savings_ratio:
            return {**disabled, "original_report_hash": original_hash}
        return {
            "st3gg_egress_enabled": True,
            "st3gg_savings_ratio": round(savings_ratio, 4),
            "st3gg_pointer": str(pointer),
            "original_report_hash": original_hash,
        }
    except Exception:
        return {**disabled, "original_report_hash": original_hash}


# ---------------------------------------------------------------------------
# Symbolic trace memory recording (best-effort, optional)
# ---------------------------------------------------------------------------

def _record_trace_events(
    result: EmergentVerificationResult,
    *,
    config: EmergentVerificationConfig,
) -> list[str]:
    """
    Append verified cluster / rejected / suppressed events to symbolic trace memory.

    Best-effort: never raises. Returns list of recorded atom_ids.
    """
    memory_root = config.trace_memory_root
    if not memory_root:
        return []
    atom_ids: list[str] = []
    try:
        from aura_symbolic_trace_memory import record_trace_event  # local import
        for cluster in result.clusters:
            payload = {
                "event_type": _TRACE_EVENT_VERIFIED_CLUSTER,
                "task_id": f"emergent_audit:{cluster.cluster_id}",
                "summary": cluster.cluster_title,
                "node_id": cluster.cluster_id,
                "route": AUDIT_ROUTE,
                "status": "future_patchable" if cluster.safe_to_patch else "grounded",
                "source_hash": _hash_text(json.dumps(cluster.best_connection, default=str)),
                "raw_ref": "",
                "replaceability_score": cluster.final_score,
                "metadata": {
                    "emergent_ability": cluster.emergent_ability,
                    "suppressed": cluster.suppressed_duplicate_count,
                    "alternates": len(cluster.alternates),
                },
            }
            atom = record_trace_event(payload, memory_root)
            aid = str(getattr(atom, "atom_id", "") or "")
            if aid:
                atom_ids.append(aid)
                cluster.trace_atom_ids.append(aid)

        for verdict in result.rejected_candidates:
            payload = {
                "event_type": _TRACE_EVENT_REJECTED,
                "task_id": f"emergent_reject:{verdict.connection_id}",
                "summary": f"rejected:{','.join(verdict.reasons[:2])}",
                "node_id": verdict.connection_id,
                "route": AUDIT_ROUTE,
                "status": "rejected",
                "source_hash": _hash_text(verdict.connection_id),
                "raw_ref": "",
                "replaceability_score": verdict.evidence_score,
                "metadata": {"reasons": verdict.reasons},
            }
            atom = record_trace_event(payload, memory_root)
            aid = str(getattr(atom, "atom_id", "") or "")
            if aid:
                atom_ids.append(aid)

    except Exception:
        pass  # fail closed — trace memory is never required for report generation
    return atom_ids


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def verify_emergent_connections(
    connections: Sequence[Any],
    *,
    focus: str = "",
    config: EmergentVerificationConfig | None = None,
) -> EmergentVerificationResult:
    """
    Full verification pipeline:

    1. Canonicalize paths.
    2. Score each connection (focus / evidence / representative / J-Space advisory).
    3. Build a verdict per connection.
    4. Cluster accepted connections by architectural pattern.
    5. MMR-rerank clusters for diversity.
    6. Optionally record to trace memory (best-effort).
    7. Return ``EmergentVerificationResult``.

    No patches, no writes (except optional trace-memory append), no network calls.
    """
    cfg = config or EmergentVerificationConfig()
    conn_list = list(connections or [])
    raw_count = len(conn_list)

    # Step 1: canonicalize paths inside each connection dict
    canon_connections: list[Any] = []
    for conn in conn_list:
        cd = _connection_dict(conn)
        if "source" in cd and isinstance(cd["source"], dict):
            cd["source"] = dict(cd["source"])
            cd["source"]["file"] = _canonical_file(str(cd["source"].get("file", "")))
        if "target" in cd and isinstance(cd["target"], dict):
            cd["target"] = dict(cd["target"])
            cd["target"]["file"] = _canonical_file(str(cd["target"].get("file", "")))
        canon_connections.append(cd)

    # Step 2 & 3: score each connection and collect verdicts
    verdicts: list[EmergentCandidateVerdict] = []
    accepted_connections: list[Any] = []
    rejected_verdicts: list[EmergentCandidateVerdict] = []

    for conn in canon_connections:
        verdict = _verdict_for(conn, focus=focus, config=cfg)
        verdicts.append(verdict)
        if verdict.accepted:
            accepted_connections.append(conn)
        else:
            rejected_verdicts.append(verdict)

    # Step 4 & 5: cluster and MMR-rerank
    clusters = cluster_emergent_connections(accepted_connections, focus=focus, config=cfg)

    total_suppressed = sum(c.suppressed_duplicate_count for c in clusters)
    total_rejected = len(rejected_verdicts)

    # Build J-Space summary
    all_jspace_concepts: list[str] = []
    for cluster in clusters:
        all_jspace_concepts.extend(cluster.jspace_advisory_concepts)
    unique_concepts = list(dict.fromkeys(all_jspace_concepts))[:20]
    jspace_summary = {
        "advisory_only": True,
        "patch_authority": PATCH_AUTHORITY_POLICY,
        "active_concepts_sample": unique_concepts,
        "warning": "J-Space concepts improve focus alignment but are NOT patch evidence.",
    }

    result = EmergentVerificationResult(
        version=VERIFIER_VERSION,
        raw_count=raw_count,
        accepted_count=len(accepted_connections),
        rejected_count=total_rejected,
        suppressed_duplicate_count=total_suppressed,
        cluster_count=len(clusters),
        clusters=clusters,
        rejected_candidates=rejected_verdicts,
        warnings=[],
        summary={
            "raw_count": raw_count,
            "accepted_count": len(accepted_connections),
            "rejected_count": total_rejected,
            "suppressed_count": total_suppressed,
            "cluster_count": len(clusters),
            "focus": focus or "(none)",
            "patch_authority": PATCH_AUTHORITY_POLICY,
            "constraints": list(READ_ONLY_CONSTRAINTS),
        },
        jspace_summary=jspace_summary,
        verifier_summary=(
            f"{len(clusters)} verified cluster(s) from {raw_count} raw candidates; "
            f"{total_suppressed} suppressed; {total_rejected} rejected."
        ),
    )

    # Step 6: trace memory (best-effort)
    atom_ids = _record_trace_events(result, config=cfg)
    result.trace_atom_ids = atom_ids

    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_verified_emergent_report(
    report_or_result: EmergentVerificationResult | dict[str, Any],
    *,
    config: EmergentVerificationConfig | None = None,
) -> str:
    """
    Render verified clusters as a human-readable markdown report.

    Includes:
    - Summary table
    - Verified High-Leverage Clusters (best representative + alternates + metadata)
    - J-Space advisory concepts (if available)
    - ST3GG egress metadata (if enabled)
    - Trace node IDs (if recorded)
    - Safety note: REPORT_ONLY
    """
    cfg = config or EmergentVerificationConfig()

    if isinstance(report_or_result, dict):
        clusters_list = (
            report_or_result.get("clusters")
            or report_or_result.get("verified_clusters")
            or []
        )
        result = EmergentVerificationResult(
            version=str(report_or_result.get("version", VERIFIER_VERSION)),
            raw_count=int(
                report_or_result.get(
                    "raw_count",
                    report_or_result.get("raw_candidate_count", 0),
                )
            ),
            accepted_count=int(report_or_result.get("accepted_count", 0)),
            rejected_count=int(
                report_or_result.get(
                    "rejected_count",
                    report_or_result.get("rejected_candidate_count", 0),
                )
            ),
            suppressed_duplicate_count=int(
                report_or_result.get("suppressed_duplicate_count", 0)
            ),
            cluster_count=int(
                report_or_result.get("cluster_count", len(clusters_list))
            ),
            clusters=[],
            warnings=list(report_or_result.get("warnings", [])),
            summary=dict(report_or_result.get("summary", {})),
            jspace_summary=dict(report_or_result.get("jspace_summary", {})),
            st3gg_egress=dict(report_or_result.get("st3gg_egress", {})),
            trace_atom_ids=list(report_or_result.get("trace_atom_ids", [])),
            verifier_summary=str(report_or_result.get("verifier_summary", "")),
        )
        result.clusters = [
            EmergentCandidateCluster(**_coerce_cluster(c))
            for c in clusters_list
            if isinstance(c, dict)
        ]
    else:
        result = report_or_result

    lines: list[str] = []
    lines.append("# Emergent Properties and Future Potential")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"* **Total raw candidates:** {result.raw_count}")
    lines.append(f"* **Accepted connections:** {result.accepted_count}")
    lines.append(f"* **Verified clusters:** {result.cluster_count}")
    lines.append(f"* **Suppressed duplicates:** {result.suppressed_duplicate_count}")
    lines.append(f"* **Rejected weak candidates:** {result.rejected_count}")
    patchable = sum(1 for c in result.clusters if c.safe_to_patch)
    too_risky = sum(1 for c in result.clusters if not c.safe_to_patch)
    lines.append(f"* **Future-patchable clusters:** {patchable}")
    lines.append(f"* **Non-patchable clusters:** {too_risky}")
    lines.append(f"* **Constraints:** {' | '.join(READ_ONLY_CONSTRAINTS)}")
    if result.verifier_summary:
        lines.append(f"* **Verifier:** {result.verifier_summary}")
    lines.append("")

    if result.clusters:
        lines.append("## Verified High-Leverage Clusters")
        lines.append("")
        for idx, cluster in enumerate(result.clusters, 1):
            best = cluster.best_connection
            src = best.get("source", {}) if isinstance(best, dict) else {}
            tgt = best.get("target", {}) if isinstance(best, dict) else {}
            src_file = str(src.get("file", "?"))
            src_sym = str(src.get("symbol", "?"))
            tgt_file = str(tgt.get("file", "?"))
            tgt_sym = str(tgt.get("symbol", "?"))
            status = str(best.get("status", "UNKNOWN") if isinstance(best, dict) else "UNKNOWN")
            score = cluster.final_score
            missing = cluster.missing_wire or str(best.get("missing_wire", "") if isinstance(best, dict) else "")

            lines.append(f"### {idx}. {cluster.cluster_title}")
            lines.append("")
            lines.append("* **Best wire:**")
            lines.append(f"  `{src_file}:{src_sym}`")
            lines.append("  ->")
            lines.append(f"  `{tgt_file}:{tgt_sym}`")
            lines.append(f"* **Missing wire:** {missing}")
            lines.append(f"* **Why it matters:** {cluster.emergent_ability}")
            # Evidence
            ev_list = best.get("evidence", []) if isinstance(best, dict) else []
            if ev_list:
                first_ev = ev_list[0] if isinstance(ev_list[0], dict) else {}
                sh = first_ev.get("source_hash", "")
                span = first_ev.get("start_line", "")
                ev_str = f"source_hash={sh[:12]}..." if sh else "no source hash"
                if span:
                    ev_str = f"span:L{span}, {ev_str}"
                lines.append(f"* **Evidence:** {ev_str}")
            else:
                lines.append("* **Evidence:** none recorded")
            req_tests = best.get("required_tests", []) if isinstance(best, dict) else []
            if req_tests:
                lines.append(f"* **Required tests:** {', '.join(req_tests[:3])}")
            # Alternates
            if cluster.alternates:
                lines.append(f"* **Alternates ({len(cluster.alternates)}):**")
                for alt in cluster.alternates[:3]:
                    asrc = alt.get("source", {}) if isinstance(alt, dict) else {}
                    atgt = alt.get("target", {}) if isinstance(alt, dict) else {}
                    lines.append(f"  - `{asrc.get('file','?')}:{asrc.get('symbol','?')}` -> `{atgt.get('file','?')}:{atgt.get('symbol','?')}`")
            if cluster.suppressed_duplicate_count:
                lines.append(f"* **Suppressed duplicates:** {cluster.suppressed_duplicate_count}")
            if cluster.verifier_notes:
                lines.append(f"* **Verifier notes:** {', '.join(cluster.verifier_notes)}")
            # J-Space advisory
            if cluster.jspace_advisory_concepts:
                jc = cluster.jspace_advisory_concepts[:5]
                lines.append(f"* **J-Space advisory concepts (not patch evidence):** {', '.join(jc)}")
            if cluster.jspace_route_context:
                lines.append(f"* **J-Space route context:** `{cluster.jspace_route_context}`")
            # ST3GG egress
            if cluster.st3gg_egress_enabled:
                lines.append(f"* **ST3GG egress:** enabled (savings={cluster.st3gg_savings_ratio:.0%})")
                lines.append(f"* **ST3GG pointer:** `{cluster.st3gg_pointer}`")
                lines.append(f"* **Original report hash:** `{cluster.original_report_hash}`")
            # Trace
            if cluster.trace_atom_ids:
                lines.append(f"* **Trace atom IDs:** {', '.join(cluster.trace_atom_ids[:3])}")
            lines.append(f"* **Status:** {status}")
            lines.append(f"* **Score:** {score:.3f}")
            lines.append("")
    else:
        lines.append("_No clusters met the verification threshold._")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"* {w}")
        lines.append("")

    # J-Space global summary
    js = result.jspace_summary
    if js.get("active_concepts_sample"):
        lines.append("## J-Space Advisory Summary")
        lines.append("")
        lines.append("> J-Space concepts are **advisory only** — not patch authority.  ")
        concepts_str = ", ".join(js["active_concepts_sample"][:8])
        lines.append(f"> Active concept sample: {concepts_str}")
        lines.append("")

    # ST3GG egress global
    st = result.st3gg_egress
    if st.get("st3gg_egress_enabled"):
        lines.append("## ST3GG Egress")
        lines.append("")
        lines.append(f"* Savings ratio: {st.get('st3gg_savings_ratio', 0):.0%}")
        lines.append(f"* Recall pointer: `{st.get('st3gg_pointer', '')}`")
        lines.append(f"* Original report hash: `{st.get('original_report_hash', '')}`")
        lines.append("* ⚠️  ST3GG compact output is an advisory recall handle. Exact source spans remain authoritative.")
        lines.append("")

    # Global trace atoms
    if result.trace_atom_ids:
        lines.append("## Trace Memory")
        lines.append("")
        lines.append(f"Recorded {len(result.trace_atom_ids)} trace atom(s):")
        for aid in result.trace_atom_ids[:6]:
            lines.append(f"* `{aid}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ⛔ Safety — REPORT ONLY")
    lines.append("")
    lines.append(
        "This report has **no patch authority**. Exact source spans and source hashes "
        "are the only patch evidence. J-Space, ST3GG, VSA, MUSIC, and trace-memory "
        "outputs are advisory only. A human must select one cluster and initiate patch "
        "planning separately."
    )
    lines.append("")
    lines.append(f"Constraints: `{'` | `'.join(READ_ONLY_CONSTRAINTS)}`")
    lines.append("")

    report_text = "\n".join(lines)

    # Populate ST3GG egress metadata if not already set
    if not result.st3gg_egress or not result.st3gg_egress.get("original_report_hash"):
        st3gg_meta = _st3gg_egress_for_report(report_text, config=cfg)
        result.st3gg_egress.update(st3gg_meta)
        # Apply the same metadata to each cluster
        for cluster in result.clusters:
            cluster.st3gg_egress_enabled = st3gg_meta["st3gg_egress_enabled"]
            cluster.st3gg_savings_ratio = st3gg_meta["st3gg_savings_ratio"]
            cluster.st3gg_pointer = st3gg_meta["st3gg_pointer"]
            cluster.original_report_hash = st3gg_meta["original_report_hash"]

    return report_text


# ---------------------------------------------------------------------------
# Benchmark hook
# ---------------------------------------------------------------------------

def emergent_audit_benchmark_metrics(result: EmergentVerificationResult, *, focus: str = "") -> dict[str, Any]:
    """
    Return efficiency benchmark metrics for an emergent audit result.

    These metrics can be registered into ``aura_efficiency_tasks`` as an
    ``emergent_audit`` task category. No network calls, no writes.
    """
    diversity = _compute_diversity_score(result.clusters)
    # Focus adherence: average focus_score across accepted cluster best connections
    if result.clusters:
        adherence_scores = []
        for cluster in result.clusters:
            best = cluster.best_connection
            if isinstance(best, dict):
                fs = score_focus(best, focus)
                adherence_scores.append(fs)
        focus_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.0
    else:
        focus_adherence = 0.0
    # Evidence completeness: average across clusters
    if result.clusters:
        ev_scores = [score_evidence(c.best_connection) for c in result.clusters]
        evidence_completeness = sum(ev_scores) / len(ev_scores)
    else:
        evidence_completeness = 0.0
    # Rough report token estimate
    report_text = render_verified_emergent_report(result)
    token_estimate = _estimate_tokens(report_text)

    return {
        "raw_candidate_count": result.raw_count,
        "verified_cluster_count": result.cluster_count,
        "suppressed_duplicate_count": result.suppressed_duplicate_count,
        "rejected_weak_candidate_count": result.rejected_count,
        "focus_adherence_score": round(focus_adherence, 4),
        "report_token_estimate": token_estimate,
        "evidence_completeness_score": round(evidence_completeness, 4),
        "diversity_score": round(diversity, 4),
        "patch_authority": PATCH_AUTHORITY_POLICY,
        "constraints": list(READ_ONLY_CONSTRAINTS),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stable_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _estimate_tokens(text: str) -> int:
    # Lightweight local estimate without network or LLM calls
    try:
        from aura_efficiency_metrics import estimate_text_tokens
        return estimate_text_tokens(text)
    except Exception:
        return max(1, len(re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]", text or "")))


def _compute_diversity_score(clusters: list[EmergentCandidateCluster]) -> float:
    """Fraction of cluster pairs with low mutual similarity — higher is more diverse."""
    if len(clusters) < 2:
        return 1.0
    pairs = 0
    diverse_pairs = 0
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            pairs += 1
            if _cluster_similarity(clusters[i], clusters[j]) < 0.50:
                diverse_pairs += 1
    return diverse_pairs / pairs if pairs else 1.0


def _coerce_cluster(d: dict[str, Any]) -> dict[str, Any]:
    """Safely coerce a plain dict back to EmergentCandidateCluster kwargs."""
    import dataclasses
    defaults = EmergentCandidateCluster.__dataclass_fields__  # type: ignore[attr-defined]
    out: dict[str, Any] = {}
    for fname, fld in defaults.items():
        if fname in d:
            out[fname] = d[fname]
        else:
            if fld.default is not dataclasses.MISSING:
                out[fname] = fld.default
            elif fld.default_factory is not dataclasses.MISSING:
                out[fname] = fld.default_factory()
            else:
                # Fallback defaults for missing fields
                if fld.type is str:
                    out[fname] = ""
                elif fld.type is int:
                    out[fname] = 0
                elif fld.type is float:
                    out[fname] = 0.0
                elif fld.type is bool:
                    out[fname] = False
                elif getattr(fld.type, "__origin__", None) is dict:
                    out[fname] = {}
                elif getattr(fld.type, "__origin__", None) is list:
                    out[fname] = []
                else:
                    out[fname] = None
    return out
