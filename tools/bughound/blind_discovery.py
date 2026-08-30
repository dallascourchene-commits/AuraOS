"""Blind proactive-discovery boundary for the AuraOS BugHound SeedLab.

D0 / local benchmark only. Candidate-facing packets contain an unlabeled source
snapshot and neutral inspection instruction. Seeded labels, fixed references,
oracles, case IDs, and causal cones remain evaluator-only. Novel findings are
queued for independent verification rather than silently credited as true bugs.

This module performs no provider call, network scan, external target interaction,
public submission, repair, merge, promotion, or authority widening.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.bughound.seedlab_benchmark import SeedBugCaseV1, Visibility

SCHEMA = "BlindDiscoveryPacketV1"
BINDING_SCHEMA = "HiddenCaseBindingV1"
FINDING_SCHEMA = "BlindFindingV1"
ADJUDICATION_SCHEMA = "BlindAdjudicationV1"
NEUTRAL_INSTRUCTION = "Inspect this source snapshot proactively for correctness defects. No issue report is provided."

FORBIDDEN_CANDIDATE_FIELDS = frozenset(
    {
        "case_id",
        "bug_family",
        "is_bug",
        "fixed_source",
        "fixed_patch",
        "trigger_id",
        "oracle_id",
        "expected_symbol",
        "causal_cone",
        "hidden_case_digest",
        "hidden_case_binding",
        "issue_report",
    }
)
_FINDING_FIELDS = frozenset(
    {
        "schema",
        "target_id",
        "finding_id",
        "localized_symbols",
        "defect_hypothesis",
        "evidence_refs",
    }
)


class BlindDiscoveryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BlindDiscoveryError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _source_digest(source: str) -> str:
    if not isinstance(source, str) or not source:
        raise BlindDiscoveryError("SOURCE_SNAPSHOT_REQUIRED")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BlindDiscoveryError(code)
    return value.strip()


@dataclass(frozen=True)
class BlindDiscoveryPacketV1:
    target_id: str
    language: str
    source_snapshot_digest: str
    source_snapshot: str
    source_generation: str
    worker_budget: int
    tool_budget: int
    instruction: str = NEUTRAL_INSTRUCTION
    fixed_patch_visible: bool = False
    labels_visible: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        _text(self.target_id, "TARGET_ID_REQUIRED")
        if self.language != "python":
            raise BlindDiscoveryError("BLIND_LANGUAGE_UNSUPPORTED", self.language)
        if _source_digest(self.source_snapshot) != self.source_snapshot_digest:
            raise BlindDiscoveryError("SOURCE_SNAPSHOT_DIGEST_MISMATCH")
        _text(self.source_generation, "SOURCE_GENERATION_REQUIRED")
        if isinstance(self.worker_budget, bool) or not isinstance(self.worker_budget, int) or self.worker_budget <= 0:
            raise BlindDiscoveryError("WORKER_BUDGET_INVALID")
        if isinstance(self.tool_budget, bool) or not isinstance(self.tool_budget, int) or self.tool_budget < 0:
            raise BlindDiscoveryError("TOOL_BUDGET_INVALID")
        if self.instruction != NEUTRAL_INSTRUCTION:
            raise BlindDiscoveryError("NONNEUTRAL_INSTRUCTION_FORBIDDEN")
        if self.fixed_patch_visible or self.labels_visible:
            raise BlindDiscoveryError("LEAKAGE_INVALIDATED")
        if self.authority or self.external_effect:
            raise BlindDiscoveryError("EFFECT_OR_AUTHORITY_WIDENING_FORBIDDEN")

    def to_candidate_dict(self) -> dict[str, Any]:
        body = asdict(self)
        leaked = FORBIDDEN_CANDIDATE_FIELDS.intersection(body)
        if leaked:
            raise BlindDiscoveryError("BLIND_PACKET_FORBIDDEN_FIELD", ",".join(sorted(leaked)))
        return body

    @property
    def packet_digest(self) -> str:
        return _digest("AURA_BUGHOUND_BLIND_PACKET_V1", self.to_candidate_dict())


@dataclass(frozen=True)
class HiddenCaseBindingV1:
    target_id: str
    hidden_case_digest: str
    source_snapshot_digest: str
    source_generation: str
    evaluator_generation: str
    visibility: Visibility = Visibility.HOLDOUT
    evaluator_current: bool = True
    fixed_patch_visible: bool = False
    labels_visible: bool = False
    schema: str = BINDING_SCHEMA

    def __post_init__(self) -> None:
        _text(self.target_id, "TARGET_ID_REQUIRED")
        _text(self.hidden_case_digest, "HIDDEN_CASE_DIGEST_REQUIRED")
        _text(self.source_snapshot_digest, "SOURCE_SNAPSHOT_DIGEST_REQUIRED")
        _text(self.source_generation, "SOURCE_GENERATION_REQUIRED")
        _text(self.evaluator_generation, "EVALUATOR_GENERATION_REQUIRED")
        if self.visibility is not Visibility.HOLDOUT:
            raise BlindDiscoveryError("BLIND_HOLDOUT_REQUIRED")
        if type(self.evaluator_current) is not bool:
            raise BlindDiscoveryError("EVALUATOR_CURRENT_BOOL_REQUIRED")

    @property
    def binding_digest(self) -> str:
        body = asdict(self)
        body["visibility"] = self.visibility.value
        return _digest("AURA_BUGHOUND_HIDDEN_BINDING_V1", body)


@dataclass(frozen=True)
class BlindFindingV1:
    target_id: str
    finding_id: str
    localized_symbols: tuple[str, ...]
    defect_hypothesis: str
    evidence_refs: tuple[str, ...] = ()
    schema: str = FINDING_SCHEMA

    def __post_init__(self) -> None:
        _text(self.target_id, "TARGET_ID_REQUIRED")
        _text(self.finding_id, "FINDING_ID_REQUIRED")
        _text(self.defect_hypothesis, "DEFECT_HYPOTHESIS_REQUIRED")
        if not isinstance(self.localized_symbols, tuple):
            raise BlindDiscoveryError("LOCALIZED_SYMBOLS_TUPLE_REQUIRED")
        if any(not isinstance(v, str) or not v.strip() for v in self.localized_symbols):
            raise BlindDiscoveryError("LOCALIZED_SYMBOL_INVALID")
        if not isinstance(self.evidence_refs, tuple):
            raise BlindDiscoveryError("EVIDENCE_REFS_TUPLE_REQUIRED")

    @property
    def finding_digest(self) -> str:
        return _digest("AURA_BUGHOUND_BLIND_FINDING_V1", asdict(self))


def parse_blind_finding(value: Mapping[str, Any]) -> BlindFindingV1:
    if not isinstance(value, Mapping):
        raise BlindDiscoveryError("BLIND_FINDING_MAPPING_REQUIRED")
    forbidden = FORBIDDEN_CANDIDATE_FIELDS.intersection(value)
    if forbidden:
        raise BlindDiscoveryError("BLINDNESS_VIOLATION", ",".join(sorted(forbidden)))
    unknown = set(value) - _FINDING_FIELDS
    if unknown:
        raise BlindDiscoveryError("BLIND_FINDING_UNKNOWN_FIELD", ",".join(sorted(unknown)))
    if value.get("schema", FINDING_SCHEMA) != FINDING_SCHEMA:
        raise BlindDiscoveryError("BLIND_FINDING_SCHEMA_MISMATCH")
    symbols = value.get("localized_symbols", ())
    refs = value.get("evidence_refs", ())
    if isinstance(symbols, list):
        symbols = tuple(symbols)
    if isinstance(refs, list):
        refs = tuple(refs)
    return BlindFindingV1(
        target_id=value.get("target_id", ""),
        finding_id=value.get("finding_id", ""),
        localized_symbols=symbols,
        defect_hypothesis=value.get("defect_hypothesis", ""),
        evidence_refs=refs,
    )


def compile_blind_case(
    case: SeedBugCaseV1,
    *,
    evaluator_salt: str,
    evaluator_generation: str,
    worker_budget: int = 1,
    tool_budget: int = 0,
) -> tuple[BlindDiscoveryPacketV1, HiddenCaseBindingV1]:
    if not isinstance(case, SeedBugCaseV1):
        raise BlindDiscoveryError("SEED_CASE_REQUIRED")
    if case.visibility is not Visibility.HOLDOUT:
        raise BlindDiscoveryError("BLIND_HOLDOUT_REQUIRED")
    salt = _text(evaluator_salt, "EVALUATOR_SALT_REQUIRED")
    evaluator_generation = _text(evaluator_generation, "EVALUATOR_GENERATION_REQUIRED")
    source = case.buggy_source
    source_digest = _source_digest(source)
    target_id = _digest(
        "AURA_BUGHOUND_OPAQUE_TARGET_V1",
        {
            "salt": salt,
            "hidden_case_digest": case.case_digest,
            "source_snapshot_digest": source_digest,
            "source_generation": case.source_generation,
        },
    )
    packet = BlindDiscoveryPacketV1(
        target_id=target_id,
        language=case.language,
        source_snapshot_digest=source_digest,
        source_snapshot=source,
        source_generation=case.source_generation,
        worker_budget=worker_budget,
        tool_budget=tool_budget,
    )
    binding = HiddenCaseBindingV1(
        target_id=target_id,
        hidden_case_digest=case.case_digest,
        source_snapshot_digest=source_digest,
        source_generation=case.source_generation,
        evaluator_generation=evaluator_generation,
    )
    return packet, binding


def validate_packet_binding(
    packet: BlindDiscoveryPacketV1,
    binding: HiddenCaseBindingV1,
    case: SeedBugCaseV1,
) -> None:
    if not isinstance(packet, BlindDiscoveryPacketV1) or not isinstance(binding, HiddenCaseBindingV1):
        raise BlindDiscoveryError("BLIND_PACKET_BINDING_REQUIRED")
    if not isinstance(case, SeedBugCaseV1):
        raise BlindDiscoveryError("SEED_CASE_REQUIRED")
    if packet.target_id != binding.target_id:
        raise BlindDiscoveryError("EVALUATOR_BINDING_MISMATCH")
    if binding.hidden_case_digest != case.case_digest:
        raise BlindDiscoveryError("EVALUATOR_BINDING_MISMATCH")
    expected_source = _source_digest(case.buggy_source)
    if packet.source_snapshot_digest != expected_source or binding.source_snapshot_digest != expected_source:
        raise BlindDiscoveryError("SOURCE_CURRENTNESS_MISMATCH")
    if packet.source_generation != case.source_generation or binding.source_generation != case.source_generation:
        raise BlindDiscoveryError("SOURCE_CURRENTNESS_MISMATCH")
    if not binding.evaluator_current:
        raise BlindDiscoveryError("EVALUATOR_CURRENTNESS_REQUIRED")
    if packet.fixed_patch_visible or packet.labels_visible or binding.fixed_patch_visible or binding.labels_visible:
        raise BlindDiscoveryError("LEAKAGE_INVALIDATED")
    packet.to_candidate_dict()


@dataclass(frozen=True)
class BlindAdjudicationV1:
    target_id: str
    outcome: str
    seeded_true_positive: bool
    clean_control_correct: bool
    novelty_verification_required: bool
    evaluator_generation: str
    authority: bool = False
    external_effect: bool = False
    schema: str = ADJUDICATION_SCHEMA

    @property
    def adjudication_digest(self) -> str:
        return _digest("AURA_BUGHOUND_BLIND_ADJUDICATION_V1", asdict(self))


def adjudicate_blind_finding(
    *,
    packet: BlindDiscoveryPacketV1,
    binding: HiddenCaseBindingV1,
    case: SeedBugCaseV1,
    finding: BlindFindingV1 | Mapping[str, Any] | None,
) -> BlindAdjudicationV1:
    validate_packet_binding(packet, binding, case)
    parsed: BlindFindingV1 | None
    if finding is None:
        parsed = None
    elif isinstance(finding, BlindFindingV1):
        parsed = finding
    else:
        parsed = parse_blind_finding(finding)
    if parsed is not None and parsed.target_id != packet.target_id:
        raise BlindDiscoveryError("EVALUATOR_BINDING_MISMATCH")

    if parsed is None:
        if case.is_bug:
            outcome = "SEEDED_BUG_MISSED"
            tp = False
            clean = False
        else:
            outcome = "CLEAN_CONTROL_CORRECT"
            tp = False
            clean = True
        novelty = False
    elif not case.is_bug:
        outcome = "CLEAN_CONTROL_FALSE_POSITIVE"
        tp = False
        clean = False
        novelty = False
    else:
        localized = set(parsed.localized_symbols)
        expected = {case.expected_symbol, *case.causal_cone}
        if localized.intersection(expected):
            outcome = "SEEDED_BUG_DISCOVERED"
            tp = True
            clean = False
            novelty = False
        else:
            outcome = "POTENTIAL_NOVELTY_UNVERIFIED"
            tp = False
            clean = False
            novelty = True

    return BlindAdjudicationV1(
        target_id=packet.target_id,
        outcome=outcome,
        seeded_true_positive=tp,
        clean_control_correct=clean,
        novelty_verification_required=novelty,
        evaluator_generation=binding.evaluator_generation,
    )
