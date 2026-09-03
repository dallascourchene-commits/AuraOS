from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum, IntEnum
from hashlib import sha256
from typing import Iterable, Mapping, Sequence
import json


class HydrationLevel(IntEnum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class CorpusRole(str, Enum):
    TRAIN_HYDRATE = "TRAIN_HYDRATE"
    BLIND_EVAL = "BLIND_EVAL"
    DIAGNOSTIC = "DIAGNOSTIC"
    QUARANTINED = "QUARANTINED"


class Audience(str, Enum):
    SOLVER = "SOLVER"
    TRAINER = "TRAINER"
    EVALUATOR = "EVALUATOR"


class Purpose(str, Enum):
    TRAIN = "TRAIN"
    BLIND_EVAL = "BLIND_EVAL"
    DIAGNOSTIC = "DIAGNOSTIC"


class OracleClass(str, Enum):
    NONE = "NONE"
    PATCH_COUNTERFACTUAL = "PATCH_COUNTERFACTUAL"
    REPRODUCIBLE_TRIGGER = "REPRODUCIBLE_TRIGGER"
    REACH_TRIGGER_DETECT = "REACH_TRIGGER_DETECT"
    POV_TEST = "POV_TEST"
    REFERENCE_MATCH = "REFERENCE_MATCH"


@dataclass(frozen=True)
class CorpusDescriptor:
    corpus_id: str
    canonical_url: str
    source_generation: str
    role: CorpusRole
    max_hydration: HydrationLevel
    languages: tuple[str, ...]
    real_world: bool
    synthetic: bool
    paired_vulnerable_fixed: bool
    line_ground_truth: bool
    trace_ground_truth: bool
    reproducible: bool
    oracle_class: OracleClass
    independent_ground_truth: bool
    solver_gold_fields: tuple[str, ...]
    evaluator_gold_fields: tuple[str, ...]
    tool_domains: tuple[str, ...]
    city_lanes: tuple[str, ...]
    contamination_family: str
    notes: str

    @property
    def url_sha256(self) -> str:
        return sha256(self.canonical_url.encode("utf-8")).hexdigest()

    @property
    def k27_xyz(self) -> tuple[int, int, int]:
        b = bytes.fromhex(self.url_sha256)
        return (b[0] % 27, b[1] % 27, b[2] % 27)


@dataclass(frozen=True)
class ToolCapability:
    tool_id: str
    city_lane: str
    domain: str
    max_level: HydrationLevel
    may_execute_local: bool
    may_use_network: bool
    may_use_credentials: bool
    authority: bool
    description: str


@dataclass(frozen=True)
class Admission:
    corpus_id: str
    purpose: Purpose
    requested_level: HydrationLevel
    disposition: str
    reason: str
    testing_authorized: bool = False
    live_target_authorized: bool = False
    credentials_authorized: bool = False
    submission_authorized: bool = False
    payment_authorized: bool = False
    external_effect: bool = False


@dataclass(frozen=True)
class HydrationView:
    corpus_id: str
    level: HydrationLevel
    audience: Audience
    fields: tuple[str, ...]
    withheld: tuple[str, ...]
    url_sha256: str
    k27_xyz: tuple[int, int, int]
    authority: bool = False


@dataclass(frozen=True)
class BenchmarkObservation:
    case_id: str
    known_vulnerable: bool
    predicted_positive: bool
    independently_supported: bool
    localized_files: tuple[str, ...] = ()
    ground_truth_files: tuple[str, ...] = ()
    trace_edges_hit: int = 0
    trace_edges_total: int = 0
    reproduced: bool = False
    counterfactual_clean: bool = False
    repeat_hits: int = 0
    repeats: int = 1
    tool_calls: int = 0
    tokens: int = 0
    elapsed_ms: int = 0


PUBLIC_FIELDS = (
    "corpus_id",
    "source_generation",
    "canonical_url",
    "languages",
    "role",
)
L1_FIELDS = PUBLIC_FIELDS + (
    "case_identity",
    "repo_identity",
    "cve_ghsa",
    "cwe",
    "severity",
)
L2_FIELDS = L1_FIELDS + (
    "vulnerable_snapshot",
    "semantic_root_cause",
    "changed_file_function_metadata",
)
L3_FIELDS = L2_FIELDS + (
    "candidate_entrypoints",
    "critical_operation_types",
    "dependency_trace_schema",
)
L4_FIELDS = L3_FIELDS + (
    "sealed_oracle_handle",
    "vulnerable_fixed_counterfactual",
    "independent_replay_receipt",
)
LEVEL_FIELDS = {
    HydrationLevel.L0: PUBLIC_FIELDS,
    HydrationLevel.L1: L1_FIELDS,
    HydrationLevel.L2: L2_FIELDS,
    HydrationLevel.L3: L3_FIELDS,
    HydrationLevel.L4: L4_FIELDS,
}


CORPORA: tuple[CorpusDescriptor, ...] = (
    CorpusDescriptor(
        "NIST_JULIET_CPP",
        "https://samate.nist.gov/SARD/test-suites/116",
        "JULIET_CPP_1.3.1",
        CorpusRole.TRAIN_HYDRATE,
        HydrationLevel.L3,
        ("C", "C++"),
        False, True, True, True, True, False, OracleClass.PATCH_COUNTERFACTUAL, True,
        (), ("labels", "good_bad_variant", "expected_flow"),
        ("STATIC_AST", "DATAFLOW", "CWE_CALIBRATION"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING"),
        "JULIET", "Synthetic breadth/calibration; never final real-world superiority evidence."
    ),
    CorpusDescriptor(
        "CVEFIXES",
        "https://github.com/secureIT-project/CVEfixes",
        "1.0.8",
        CorpusRole.TRAIN_HYDRATE,
        HydrationLevel.L2,
        ("MULTI",),
        True, False, True, False, False, False, OracleClass.PATCH_COUNTERFACTUAL, False,
        (), ("fix_commit", "changed_lines", "cve_linkage"),
        ("GIT_DIFF", "ROOT_CAUSE_MINING", "CWE_CALIBRATION"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING"),
        "CVEFIXES", "Large vulnerability/fix mining corpus; patch association is not an executable reproduction oracle."
    ),
    CorpusDescriptor(
        "PRIMEVUL",
        "https://github.com/DLVulDet/PrimeVul",
        "v0.1",
        CorpusRole.TRAIN_HYDRATE,
        HydrationLevel.L2,
        ("C", "C++"),
        True, False, True, True, False, False, OracleClass.PATCH_COUNTERFACTUAL, True,
        (), ("labels", "paired_patch", "chronological_split_metadata"),
        ("FUNCTION_CLASSIFICATION", "PAIRED_DIFF", "CALIBRATION"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING"),
        "PRIMEVUL", "Useful for training/calibration with paired vulnerable/patched functions; not repo-level L4 proof."
    ),
    CorpusDescriptor(
        "ARVO",
        "https://arxiv.org/abs/2606.17283",
        "ARVO_2026_PAPER_GENERATION",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L4,
        ("C", "C++", "OSS_FUZZ"),
        True, False, True, True, True, True, OracleClass.REPRODUCIBLE_TRIGGER, True,
        ("patch", "poc", "trigger", "oracle_output", "fixed_reference"),
        ("patch", "poc", "trigger", "oracle_output", "fixed_reference", "reproduction_receipt"),
        ("STATIC", "DYNAMIC", "FUZZ", "REPRODUCTION", "PATCH_COUNTERFACTUAL"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING", "DETROIT_WORKSHOP", "FEDERAL_CAPITAL"),
        "ARVO", "Primary L4 real-world reproducibility lane; gold remains evaluator-only during discovery."
    ),
    CorpusDescriptor(
        "VULNGYM",
        "https://arxiv.org/abs/2608.02001",
        "VULNGYM_2026_PAPER_GENERATION",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L3,
        ("MULTI_REPOSITORY",),
        True, False, True, True, True, False, OracleClass.PATCH_COUNTERFACTUAL, True,
        ("entry_points", "critical_operations", "vulnerability_trace", "patch"),
        ("entry_points", "critical_operations", "vulnerability_trace", "patch"),
        ("REPOSITORY_EXPLORATION", "LOCALIZATION", "TRACE_CONSTRUCTION"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING", "FEDERAL_CAPITAL"),
        "VULNGYM", "Primary repository-level localization and causal-trace diagnostic lane."
    ),
    CorpusDescriptor(
        "CISCO_VLB",
        "https://github.com/cisco-foundation-ai/vulnerability-localization-benchmark",
        "DATASET_CARD_CURRENT_2026-09-03",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L3,
        ("JavaScript", "Python", "Java", "Go", "Rust", "PHP"),
        True, False, True, True, False, False, OracleClass.PATCH_COUNTERFACTUAL, True,
        ("ground_truth_files", "post_push_diff"),
        ("ground_truth_files", "post_push_diff"),
        ("REPOSITORY_EXPLORATION", "LOCALIZATION", "PATCHED_NEGATIVE"),
        ("ATHENS_RESEARCH_ARCHIVES", "SAN_FRANCISCO_ENGINEERING", "FEDERAL_CAPITAL"),
        "CISCO_VLB", "Blind pre-patch localization plus patched negative-control phase."
    ),
    CorpusDescriptor(
        "MAGMA",
        "https://arxiv.org/abs/2009.01120",
        "MAGMA_GROUND_TRUTH_V1",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L4,
        ("C", "C++"),
        True, False, False, False, True, True, OracleClass.REACH_TRIGGER_DETECT, True,
        ("bug_markers", "trigger_conditions", "known_bug_locations"),
        ("bug_markers", "trigger_conditions", "known_bug_locations", "reach_trigger_detect"),
        ("FUZZ", "COVERAGE", "DYNAMIC_ORACLE"),
        ("DETROIT_WORKSHOP", "FEDERAL_CAPITAL"),
        "MAGMA", "Ground-truth fuzzing lane; benchmark runner may see instrumentation, solver may not."
    ),
    CorpusDescriptor(
        "VUL4J",
        "https://github.com/tuhh-softsec/Vul4J",
        "CURRENT_2026-09-03",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L4,
        ("Java",),
        True, False, True, True, True, True, OracleClass.POV_TEST, True,
        ("pov_test", "patch", "ground_truth_files"),
        ("pov_test", "patch", "ground_truth_files", "reproduction_status"),
        ("BUILD", "TEST", "STATIC", "REPRODUCTION"),
        ("SAN_FRANCISCO_ENGINEERING", "DETROIT_WORKSHOP", "FEDERAL_CAPITAL"),
        "VUL4J", "Java L4 lane; only cases that independently reproduce in the current local environment receive L4 credit."
    ),
    CorpusDescriptor(
        "SNYK_VULNBENCH_JS",
        "https://github.com/snyk-labs/snyk-vulnbench",
        "JS_1.0_2026-06-29",
        CorpusRole.DIAGNOSTIC,
        HydrationLevel.L3,
        ("JavaScript",),
        True, False, False, True, True, False, OracleClass.REFERENCE_MATCH, False,
        ("reference_findings",),
        ("reference_findings", "repeatability_results"),
        ("REPEATABILITY", "SOURCE_TO_SINK", "EFFICIENCY"),
        ("SAN_FRANCISCO_ENGINEERING", "NEW_YORK_COMMERCE", "FEDERAL_CAPITAL"),
        "SNYK_VULNBENCH", "Different-J repeatability/reference-agreement diagnostic; reference agreement is not universal independent truth."
    ),
    CorpusDescriptor(
        "SEC_BENCH",
        "https://github.com/SEC-bench/SEC-bench",
        "NEURIPS_2025_CURRENT_2026-09-03",
        CorpusRole.BLIND_EVAL,
        HydrationLevel.L4,
        ("MULTI",),
        True, False, True, True, True, True, OracleClass.REPRODUCIBLE_TRIGGER, True,
        ("repro_harness", "patch", "oracle_output", "cve_metadata"),
        ("repro_harness", "patch", "oracle_output", "cve_metadata"),
        ("REPOSITORY_EXPLORATION", "BUILD", "REPRODUCTION", "PATCH_COUNTERFACTUAL"),
        ("SAN_FRANCISCO_ENGINEERING", "DETROIT_WORKSHOP", "FEDERAL_CAPITAL"),
        "SEC_BENCH", "Use only repository-only detection/local reproduction tasks in isolated local containers; no live target actions."
    ),
)

CORPUS_BY_ID: Mapping[str, CorpusDescriptor] = {c.corpus_id: c for c in CORPORA}

TOOLS: tuple[ToolCapability, ...] = (
    ToolCapability("SOURCE_INDEXER", "ATHENS_RESEARCH_ARCHIVES", "PROVENANCE", HydrationLevel.L2, False, False, False, False,
                   "Exact source/version/license/digest indexing and deduplication."),
    ToolCapability("STATIC_CODE_GRAPH", "SAN_FRANCISCO_ENGINEERING", "STATIC", HydrationLevel.L3, False, False, False, False,
                   "AST/CFG/call/data-dependency graph adapters over local source snapshots."),
    ToolCapability("PATCH_DIFFER", "SAN_FRANCISCO_ENGINEERING", "DIFF", HydrationLevel.L3, False, False, False, False,
                   "Evaluator/trainer patch-delta analysis; hidden from blind solver when it would leak ground truth."),
    ToolCapability("LOCAL_BUILD_TEST", "DETROIT_WORKSHOP", "REPRODUCTION", HydrationLevel.L4, True, False, False, False,
                   "Ephemeral local build/test runner for disclosed benchmark artifacts only."),
    ToolCapability("LOCAL_FUZZ_ORACLE", "DETROIT_WORKSHOP", "FUZZ", HydrationLevel.L4, True, False, False, False,
                   "Local coverage/reach/trigger/detect measurement against benchmark-owned targets."),
    ToolCapability("CORPUS_CUSTOMS", "GENEVA_EMBASSY", "PROVENANCE", HydrationLevel.L1, False, False, False, False,
                   "License/source/currentness/schema customs; cannot grant testing authority."),
    ToolCapability("BENCHMARK_ADJUDICATOR", "FEDERAL_CAPITAL", "EVALUATION", HydrationLevel.L4, False, False, False, False,
                   "Sealed evaluator truth, contamination checks, scoring and independent receipt binding."),
    ToolCapability("COST_REPEATABILITY_LEDGER", "NEW_YORK_COMMERCE", "ECONOMICS", HydrationLevel.L3, False, False, False, False,
                   "Tracks repeated-run stability and resource cost; never infers private bounty duplicate status or payout."),
)


def descriptor(corpus_id: str) -> CorpusDescriptor:
    try:
        return CORPUS_BY_ID[corpus_id]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_CORPUS:{corpus_id}") from exc


def admit_dataset(corpus_id: str, purpose: Purpose, requested_level: HydrationLevel) -> Admission:
    c = descriptor(corpus_id)
    if c.role == CorpusRole.QUARANTINED:
        return Admission(corpus_id, purpose, requested_level, "HOLD_QUARANTINED", "corpus requires explicit separate sandbox disposition")
    if requested_level > c.max_hydration:
        return Admission(corpus_id, purpose, requested_level, "HOLD_LEVEL_UNEARNED", f"max={c.max_hydration.name}")
    if purpose == Purpose.TRAIN and c.role != CorpusRole.TRAIN_HYDRATE:
        return Admission(corpus_id, purpose, requested_level, "HOLD_EVAL_CONTAMINATION", "blind/diagnostic corpora are not training memory")
    if purpose == Purpose.BLIND_EVAL:
        if c.role != CorpusRole.BLIND_EVAL:
            return Admission(corpus_id, purpose, requested_level, "HOLD_NOT_BLIND_EVAL", f"role={c.role.value}")
        if not c.real_world:
            return Admission(corpus_id, purpose, requested_level, "HOLD_NOT_REAL_WORLD", "synthetic corpus cannot establish real-world performance")
        if not c.independent_ground_truth:
            return Admission(corpus_id, purpose, requested_level, "HOLD_TRUTH_NOT_INDEPENDENT", "reference agreement is not independent ground truth")
        if requested_level == HydrationLevel.L4:
            if not (c.reproducible and c.oracle_class not in (OracleClass.NONE, OracleClass.REFERENCE_MATCH)):
                return Admission(corpus_id, purpose, requested_level, "HOLD_L4_ORACLE_UNPROVEN", "L4 requires local reproducible independent oracle")
    if purpose == Purpose.DIAGNOSTIC and c.role == CorpusRole.TRAIN_HYDRATE:
        return Admission(corpus_id, purpose, requested_level, "ADMIT_DIAGNOSTIC_ONLY", "training corpus diagnostic; no real-world superiority credit")
    return Admission(corpus_id, purpose, requested_level, "ADMIT_LOCAL_ONLY", "metadata/source analysis or isolated benchmark execution only")


def hydration_view(corpus_id: str, level: HydrationLevel, audience: Audience) -> HydrationView:
    c = descriptor(corpus_id)
    if level > c.max_hydration:
        raise ValueError("HYDRATION_LEVEL_UNEARNED")
    base = list(LEVEL_FIELDS[level])
    withheld: set[str] = set()
    if audience == Audience.SOLVER and c.role in (CorpusRole.BLIND_EVAL, CorpusRole.DIAGNOSTIC):
        withheld.update(c.solver_gold_fields)
    if audience == Audience.TRAINER and c.role != CorpusRole.TRAIN_HYDRATE:
        raise ValueError("TRAINER_CANNOT_HYDRATE_BLIND_EVAL_CORPUS")
    if audience != Audience.EVALUATOR:
        withheld.update({"poc", "trigger", "oracle_output", "pov_test", "repro_harness"})
    fields = tuple(x for x in base if x not in withheld)
    return HydrationView(c.corpus_id, level, audience, fields, tuple(sorted(withheld)), c.url_sha256, c.k27_xyz)


def validate_split(train_ids: Iterable[str], eval_ids: Iterable[str]) -> tuple[bool, tuple[str, ...]]:
    train = [descriptor(x) for x in train_ids]
    ev = [descriptor(x) for x in eval_ids]
    problems: list[str] = []
    train_ids_set = {x.corpus_id for x in train}
    eval_ids_set = {x.corpus_id for x in ev}
    if train_ids_set & eval_ids_set:
        problems.append("CORPUS_ID_OVERLAP")
    train_families = {x.contamination_family for x in train}
    eval_families = {x.contamination_family for x in ev}
    if train_families & eval_families:
        problems.append("CONTAMINATION_FAMILY_OVERLAP")
    for c in train:
        if c.role != CorpusRole.TRAIN_HYDRATE:
            problems.append(f"NONTRAIN_IN_TRAIN:{c.corpus_id}")
    for c in ev:
        if c.role != CorpusRole.BLIND_EVAL:
            problems.append(f"NONBLIND_IN_EVAL:{c.corpus_id}")
    return (not problems, tuple(problems))


def compute_scores(observations: Sequence[BenchmarkObservation]) -> dict[str, float | int | None]:
    if not observations:
        raise ValueError("EMPTY_BENCHMARK")
    tp = sum(1 for o in observations if o.known_vulnerable and o.predicted_positive and o.independently_supported)
    unsupported_positive = sum(1 for o in observations if o.predicted_positive and not o.independently_supported)
    fp = sum(1 for o in observations if not o.known_vulnerable and o.predicted_positive)
    fn = sum(1 for o in observations if o.known_vulnerable and not (o.predicted_positive and o.independently_supported))
    positives = tp + fp + unsupported_positive
    precision = None if positives == 0 else tp / positives
    recall = None if tp + fn == 0 else tp / (tp + fn)
    f1 = None if precision is None or recall is None or (precision + recall) == 0 else 2 * precision * recall / (precision + recall)

    file_f1s: list[float] = []
    trace_rates: list[float] = []
    repeat_rates: list[float] = []
    for o in observations:
        if o.ground_truth_files:
            pred, gt = set(o.localized_files), set(o.ground_truth_files)
            p = 0.0 if not pred else len(pred & gt) / len(pred)
            r = len(pred & gt) / len(gt)
            file_f1s.append(0.0 if p + r == 0 else 2 * p * r / (p + r))
        if o.trace_edges_total:
            trace_rates.append(min(o.trace_edges_hit, o.trace_edges_total) / o.trace_edges_total)
        if o.repeats > 0:
            repeat_rates.append(min(o.repeat_hits, o.repeats) / o.repeats)

    l4_verified = sum(1 for o in observations if o.known_vulnerable and o.reproduced and o.counterfactual_clean and o.independently_supported)
    return {
        "cases": len(observations),
        "true_positive_supported": tp,
        "unsupported_positive": unsupported_positive,
        "false_positive_clean_or_patched": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_file_f1": None if not file_f1s else sum(file_f1s) / len(file_f1s),
        "mean_trace_coverage": None if not trace_rates else sum(trace_rates) / len(trace_rates),
        "l4_verified": l4_verified,
        "mean_repeatability": sum(repeat_rates) / len(repeat_rates),
        "tool_calls": sum(o.tool_calls for o in observations),
        "tokens": sum(o.tokens for o in observations),
        "elapsed_ms": sum(o.elapsed_ms for o in observations),
    }


def k27_manifest() -> list[dict[str, object]]:
    out = []
    for c in CORPORA:
        out.append({
            "corpus_id": c.corpus_id,
            "canonical_url": c.canonical_url,
            "url_sha256": c.url_sha256,
            "k27_xyz": list(c.k27_xyz),
            "scheme": "K27-B3MOD27-XYZ-v1",
            "claim_ceiling": "RETRIEVAL_REOPEN_METADATA_ONLY",
        })
    return out


def corpus_manifest_digest() -> str:
    payload = []
    for c in CORPORA:
        d = asdict(c)
        d["role"] = c.role.value
        d["max_hydration"] = int(c.max_hydration)
        d["oracle_class"] = c.oracle_class.value
        payload.append(d)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def hyper1000_cells() -> list[tuple[str, str, str]]:
    corpora = [c.corpus_id for c in CORPORA[:10]]
    challenges = [
        "PATCH_LEAK", "LABEL_LEAK", "POC_LEAK", "STALE_GENERATION", "CROSS_SPLIT_REUSE",
        "ORACLE_VISIBLE", "NETWORK_REQUIRED", "CREDENTIAL_REQUIRED", "NONINDEPENDENT_TRUTH", "COST_OVERRUN",
    ]
    contexts = [
        "ATHENS", "SAN_FRANCISCO", "DETROIT", "GENEVA", "FEDERAL", "NEW_YORK",
        "STATIC", "DYNAMIC", "REPRO", "EVALUATION",
    ]
    return [(c, ch, ctx) for c in corpora for ch in challenges for ctx in contexts]


KEEPER_LAWS = (
    "TrainingHydration != BlindEvaluationTruth",
    "PatchOrPoCVisibleToSolver => EvaluationContaminated",
    "KnownBugLabel != CandidatePerformance",
    "Localization != CausalTrace != Reproduction",
    "ReproductionOnVulnerable != CounterfactualSpecificityUntilPatchedNegativeIsClean",
    "ReferenceAgreement != IndependentGroundTruth",
    "SyntheticCoverage != RealWorldGeneralization",
    "K27Coordinate != SourceIdentity != Truth != Currentness != Authority",
    "BenchmarkPass != LiveTargetAuthorization != SubmissionAuthority != Payout",
    "ReusableMemory != TargetSpecificUndisclosedExploitInstructions",
)
