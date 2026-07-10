"""
Aura Civic Deliberation — Consent Arc, dissent preservation, Democratic Friction.

The Consent Arc is NON_BINDING, BOUNDED_TO_RECORDED_PARTICIPANTS, NOT_A_REFERENDUM,
NOT_REPRESENTATIVE_UNLESS_PROVEN.
"""
from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

RESPONSE_TYPES = (
    "STRONG_SUPPORT", "SUPPORT", "CONSENT", "CONSENT_WITH_RESERVATION",
    "ABSTAIN", "NEEDS_MORE_INFORMATION", "OBJECT", "CRITICAL_OBJECTION",
    "PROPOSE_ALTERNATIVE", "WITHDRAW",
)

CONSENSUS_STATUSES = (
    "DRAFT", "COLLECTING_INPUT", "EMERGING_ALIGNMENT", "BROAD_CONSENT",
    "CONSENT_WITH_RESERVATIONS", "CONTESTED", "BLOCKED_BY_CRITICAL_OBJECTION",
    "INSUFFICIENT_INFORMATION", "INSUFFICIENT_PARTICIPATION",
    "REPRESENTATION_GAP", "LEGAL_OR_RESOURCE_BLOCK", "PILOT_RECOMMENDED",
    "NO_DECISION", "CLOSED_BY_HUMAN_FACILITATOR",
)


@dataclass
class ParticipantResponse:
    response_id: str
    participant_ref: str
    proposal_ref: str
    response_type: str
    statement: str = ""
    truth_class: str = "COMMUNITY_ASSERTED"
    created_at: float = 0.0
    def to_dict(self): return asdict(self)


@dataclass
class ConsentArc:
    arc_id: str
    proposal_ref: str
    responses: list[dict[str, Any]] = field(default_factory=list)
    consensus_status: str = "COLLECTING_INPUT"
    participant_scope: str = ""
    representation_gaps: list[str] = field(default_factory=list)
    non_binding: bool = True
    not_a_referendum: bool = True
    not_representative_unless_proven: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)


def collect_response(arc: ConsentArc, response: ParticipantResponse) -> ConsentArc:
    arc.responses.append(response.to_dict())
    has_critical = any(r["response_type"] == "CRITICAL_OBJECTION" for r in arc.responses)
    if has_critical:
        arc.consensus_status = "BLOCKED_BY_CRITICAL_OBJECTION"
    return arc


def assess_convergence(arc: ConsentArc) -> dict[str, Any]:
    total = len(arc.responses)
    if total == 0:
        return {"ok": True, "status": "INSUFFICIENT_PARTICIPATION", "total": 0,
                "representation_gaps": arc.representation_gaps,
                "participant_scope": arc.participant_scope,
                "non_binding": True, "not_a_referendum": True,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    counts: dict[str, int] = {}
    for r in arc.responses:
        rt = r.get("response_type", "ABSTAIN")
        counts[rt] = counts.get(rt, 0) + 1
    support = counts.get("STRONG_SUPPORT", 0) + counts.get("SUPPORT", 0) + counts.get("CONSENT", 0)
    objections = counts.get("OBJECT", 0) + counts.get("CRITICAL_OBJECTION", 0)
    reservations = counts.get("CONSENT_WITH_RESERVATION", 0)
    if counts.get("CRITICAL_OBJECTION", 0) > 0:
        status = "BLOCKED_BY_CRITICAL_OBJECTION"
    elif support > total * 0.6 and objections == 0:
        status = "BROAD_CONSENT" if reservations == 0 else "CONSENT_WITH_RESERVATIONS"
    elif objections > 0:
        status = "CONTESTED"
    else:
        status = "COLLECTING_INPUT"
    return {"ok": True, "status": status, "total_responses": total,
            "response_breakdown": counts, "support_count": support,
            "objection_count": objections, "reservation_count": reservations,
            "abstention_count": counts.get("ABSTAIN", 0),
            "participant_scope": arc.participant_scope,
            "representation_gaps": arc.representation_gaps,
            "non_binding": True, "not_a_referendum": True,
            "accessible_table_equivalent": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


@dataclass
class DemocraticFriction:
    round_count: int = 0
    meeting_count: int = 0
    elapsed_time_hours: float = 0.0
    proposal_revisions: int = 0
    evidence_requests: int = 0
    objections_raised: int = 0
    objections_addressed: int = 0
    objections_unresolved: int = 0
    facilitator_interventions: int = 0
    outreach_actions: int = 0
    participant_turnover: int = 0
    unresolved_representation_gaps: int = 0
    def to_dict(self): return asdict(self)
    def explanation(self) -> str:
        return ("Deliberation takes time. This panel shows the work required to reach "
                "the current position and the concerns that remain unresolved.")


@dataclass
class SystemicContextReport:
    report_id: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)


def create_systemic_context(findings: list[dict[str, Any]]) -> dict[str, Any]:
    validated = []
    for f in findings:
        if not f.get("source") or not f.get("truth_class"):
            continue
        finding = dict(f)
        if finding.get("truth_class") == "MODEL_INFERRED":
            finding["classification"] = "MODEL_HYPOTHESIZED"
        elif finding.get("truth_class") == "OFFICIAL_PRIMARY_SOURCE":
            finding["classification"] = "HISTORICALLY_DOCUMENTED"
        elif finding.get("truth_class") == "COMMUNITY_ASSERTED":
            finding["classification"] = "COMMUNITY_ASSERTED"
        else:
            finding["classification"] = "UNKNOWN"
        validated.append(finding)
    payload = json.dumps(validated, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.blake2b(payload.encode(), digest_size=4).hexdigest()
    report = SystemicContextReport(report_id=f"SYSCTX-{digest}", findings=validated)
    return {"ok": True, "report": report.to_dict(),
            "note": "Correlation is not converted to causation.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
