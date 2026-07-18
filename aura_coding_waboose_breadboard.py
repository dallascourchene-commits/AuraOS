"""Proposal-only diagnostic breadboard for Coding Waboose.

The breadboard turns a Waboose review contract into typed Planning Board
components. It lets Aura and a replaceable coding agent assemble review
hypotheses out of order, mock unavailable inputs explicitly, trace forward
consequences and backward proof requirements, and energize only components
that have bound inspection receipts.

A mock is never silently upgraded into grounding. A component may be explored
with an explicit mock, but it cannot reach grounded or verified continuity until
the missing exact dependency evidence is resolved.

It never executes code, grants a capability lease, creates patch authority,
mutates a repository, or promotes a repair.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from aura_event_contracts import stable_digest
from aura_planning_board import (
    ActionContinuityEvidence,
    ActionSpec,
    AuthorityRequirement,
    BoardContinuityLevel,
    ConstraintKind,
    ConstraintSpec,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PortCardinality,
    PortDirection,
    PortSpec,
    PredicateSpec,
    ResourceDemand,
    ReversibilityClass,
    VerifierReceiptEvidence,
    verify_board_continuity,
)

CODING_WABOOSE_BREADBOARD_VERSION = "AURA_CODING_WABOOSE_BREADBOARD_V1"
BREADBOARD_AUTHORITY = "proposal_only_diagnostic_circuit"


@dataclass(frozen=True)
class WabooseBreadboardComponent:
    directive_id: str
    action_id: str
    name: str
    risk: str
    direction: str
    connected_input_refs: tuple[str, ...]
    mocked_input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    verifier_ids: tuple[str, ...]
    energized: bool
    continuity: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "connected_input_refs",
            "mocked_input_refs",
            "output_refs",
            "verifier_ids",
        ):
            value[key] = list(value[key])
        return value


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _strings(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("expected a sequence of strings")
    result: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _directive_rows(contract: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    raw = contract.get("focus_directives")
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("contract.focus_directives must be an array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"contract.focus_directives[{index}] must be an object")
        row = dict(item)
        row["directive_id"] = _required(row.get("directive_id"), "directive_id")
        row["name"] = _required(row.get("name"), "name")
        row["question"] = _required(row.get("question"), "question")
        result.append(row)
    if not result:
        raise ValueError("contract.focus_directives must not be empty")
    return tuple(result)


def _impact_rows(contract: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    raw = contract.get("impact_slice") or []
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("contract.impact_slice must be an array")
    return tuple(dict(item) for item in raw if isinstance(item, Mapping))


def _matched_impact_refs(
    directive: Mapping[str, Any],
    impact_rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    patterns = tuple(
        pattern.lower() for pattern in _strings(directive.get("target_patterns"))
    )
    result: list[str] = []
    for item in impact_rows:
        node_id = str(item.get("node_id") or "").strip()
        if not node_id:
            continue
        corpus = " ".join(
            str(item.get(key) or "")
            for key in (
                "node_id",
                "file",
                "symbol",
                "kind",
                "edge_kind",
                "direction",
            )
        ).lower()
        if not patterns or any(pattern in corpus for pattern in patterns):
            ref = f"topology:{node_id}"
            if ref not in result:
                result.append(ref)
    return tuple(result)


def _source_refs(contract: Mapping[str, Any]) -> tuple[str, ...]:
    diff_digest = _required(contract.get("diff_digest"), "contract.diff_digest")
    raw_files = contract.get("changed_files")
    if isinstance(raw_files, (str, bytes)) or not isinstance(raw_files, Sequence):
        raise ValueError("contract.changed_files must be an array")
    refs = tuple(
        f"source:{_required(path, 'changed_file')}#diff:{diff_digest[:16]}"
        for path in raw_files
    )
    if not refs:
        raise ValueError("contract.changed_files must not be empty")
    return refs


def _component_action(
    directive: Mapping[str, Any],
    *,
    contract_id: str,
    source_refs: tuple[str, ...],
    impact_refs: tuple[str, ...],
) -> tuple[ActionSpec, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    directive_id = _required(directive.get("directive_id"), "directive_id")
    suggested_tools = _strings(directive.get("suggested_tools"))

    connected_refs = tuple(dict.fromkeys((*source_refs, *impact_refs)))
    mocked_refs: tuple[str, ...] = ()
    if not impact_refs:
        mocked_refs = (f"mock:{directive_id}:unresolved_impact_target",)

    constraint_ref = f"constraint:{contract_id}:review_only_non_mutating"
    output_refs = (
        f"output:{directive_id}:evidence_bundle",
        f"output:{directive_id}:finding_candidates",
    )
    verifier_ids = (
        f"waboose:{directive_id}:focus_executed",
        f"waboose:{directive_id}:exact_source_checked",
    )
    action_id = (
        "waboose_action_"
        + stable_digest(
            {"contract": contract_id, "directive": directive_id}, digest_size=12
        )
    )

    input_ports = [
        PortSpec("change_slice", "WabooseChangeSliceV1", PortDirection.INPUT),
        PortSpec("impact_graph", "WabooseImpactGraphV1", PortDirection.INPUT),
        PortSpec("review_hypothesis", "WabooseHypothesisV1", PortDirection.INPUT),
    ]
    if mocked_refs:
        input_ports.append(
            PortSpec(
                "mocked_dependency",
                "WabooseExplicitMockV1",
                PortDirection.INPUT,
                cardinality=PortCardinality.OPTIONAL,
                required=False,
            )
        )

    action = ActionSpec(
        action_id=action_id,
        name=f"Investigate {directive.get('name')}",
        domain="coding_waboose",
        preconditions=(
            PredicateSpec("waboose.contract.bound", True),
            PredicateSpec("waboose.diff.grounded", True),
            PredicateSpec(f"waboose.focus.{directive_id}.admitted", True),
        ),
        effects=(
            EffectSpec(f"waboose.focus.{directive_id}.investigated", True),
            EffectSpec(f"waboose.focus.{directive_id}.evidence_emitted", True),
        ),
        input_ports=tuple(input_ports),
        output_ports=(
            PortSpec(
                "evidence_bundle",
                "WabooseEvidenceBundleV1",
                PortDirection.OUTPUT,
            ),
            PortSpec(
                "finding_candidates",
                "WabooseFindingCandidateListV1",
                PortDirection.OUTPUT,
                cardinality=PortCardinality.MANY,
            ),
        ),
        constraints=(
            ConstraintSpec(
                constraint_id=(
                    "waboose_constraint_"
                    + stable_digest(
                        {"contract": contract_id, "directive": directive_id},
                        digest_size=12,
                    )
                ),
                kind=ConstraintKind.SAFETY,
                description=(
                    "Review is proposal-only. The circuit may inspect and "
                    "simulate but may not edit, commit, push, open a pull "
                    "request, merge, or promote a repair."
                ),
                evidence_refs=(constraint_ref,),
                blocking=True,
            ),
        ),
        required_capabilities=tuple(
            dict.fromkeys(("topology.query", "source.read_exact", *suggested_tools))
        ),
        verifier_ids=verifier_ids,
        authority_requirement=AuthorityRequirement.NONE,
        resource_demand=ResourceDemand(),
        reversibility=ReversibilityClass.REVERSIBLE,
        idempotency_key=f"waboose:{contract_id}:{directive_id}",
        # Mock references are declared as required evidence but are deliberately
        # not included in grounded_evidence_refs below. This makes BC3 fail
        # closed until exact dependency evidence replaces the mock.
        evidence_refs=tuple((*connected_refs, *mocked_refs)),
        proposal_only=True,
    )
    return action, connected_refs, mocked_refs, output_refs


def compile_waboose_breadboard(
    contract: Mapping[str, Any],
    *,
    energized_directive_ids: Sequence[str] = (),
    phase: str = "PREPARED",
) -> dict[str, Any]:
    """Compile a proposal-only diagnostic circuit from a Waboose contract.

    ``energized_directive_ids`` means an external review stage produced bound
    inspection receipts for those focus directives. It does not mean a defect
    exists, a finding is correct, or a repair is authorized.
    """

    if not isinstance(contract, Mapping):
        raise ValueError("contract must be an object")
    contract_id = _required(contract.get("contract_id"), "contract.contract_id")
    objective = _required(
        contract.get("objective") or contract.get("request_digest"), "objective"
    )
    purpose_digest = _required(
        contract.get("request_digest"), "contract.request_digest"
    )
    directives = _directive_rows(contract)
    impact_rows = _impact_rows(contract)
    source_refs = _source_refs(contract)
    energized = set(_strings(energized_directive_ids))

    actions: list[ActionSpec] = []
    component_rows: list[
        tuple[
            Mapping[str, Any],
            ActionSpec,
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
        ]
    ] = []
    evidence_rows: list[ActionContinuityEvidence] = []
    constraint_ref = f"constraint:{contract_id}:review_only_non_mutating"

    for directive in directives:
        impact_refs = _matched_impact_refs(directive, impact_rows)
        action, connected, mocked, outputs = _component_action(
            directive,
            contract_id=contract_id,
            source_refs=source_refs,
            impact_refs=impact_refs,
        )
        actions.append(action)
        directive_id = str(directive["directive_id"])
        receipts: tuple[VerifierReceiptEvidence, ...] = ()
        if directive_id in energized:
            receipts = tuple(
                VerifierReceiptEvidence(
                    verifier_id=verifier_id,
                    receipt_id=(
                        "receipt_"
                        + stable_digest(
                            {
                                "contract": contract_id,
                                "directive": directive_id,
                                "verifier": verifier_id,
                                "phase": phase,
                            },
                            digest_size=12,
                        )
                    ),
                )
                for verifier_id in action.verifier_ids
            )
        evidence_rows.append(
            ActionContinuityEvidence(
                action_id=action.action_id,
                constrained_evidence_refs=(constraint_ref,),
                # Exact connected inputs are grounded. Explicit mocks are not.
                grounded_evidence_refs=connected,
                authority_decision_ids=(
                    f"policy:{contract_id}:review_only_no_execution_authority",
                ),
                verifier_receipts=receipts,
            )
        )
        component_rows.append((directive, action, connected, mocked, outputs))

    goal = GoalSpec(
        goal_id=(
            "waboose_goal_"
            + stable_digest(
                {"contract": contract_id, "objective": objective}, digest_size=12
            )
        ),
        objective=(
            "Produce an evidence-bound Coding Waboose review packet for: "
            f"{objective}"
        ),
        desired_state=(PredicateSpec("waboose.review.packet_ready", True),),
        constraints=(
            ConstraintSpec(
                constraint_id=(
                    "waboose_goal_constraint_"
                    + stable_digest(contract_id, digest_size=12)
                ),
                kind=ConstraintKind.SAFETY,
                description=(
                    "No diagnostic circuit output is patch, merge, or "
                    "promotion authority."
                ),
                evidence_refs=(constraint_ref,),
                blocking=True,
            ),
        ),
        evidence_refs=(f"review_contract:{contract_id}",),
    )
    board = PlanningBoard(
        board_id=(
            "waboose_board_"
            + stable_digest(
                {
                    "contract": contract_id,
                    "actions": [item.action_id for item in actions],
                },
                digest_size=12,
            )
        ),
        arena_id="coding_waboose",
        purpose_digest=purpose_digest,
        goal=goal,
        actions=tuple(actions),
        current_state_refs=(f"review_contract:{contract_id}", *source_refs),
    )
    continuity = verify_board_continuity(board, evidence=tuple(evidence_rows))

    finding_by_action: dict[str, list[dict[str, Any]]] = {}
    for finding in continuity.findings:
        finding_by_action.setdefault(finding.subject_id, []).append(
            finding.to_dict()
        )

    components: list[WabooseBreadboardComponent] = []
    for directive, action, connected, mocked, outputs in component_rows:
        directive_id = str(directive["directive_id"])
        is_energized = directive_id in energized
        blocking = finding_by_action.get(action.action_id, [])
        if mocked:
            status = (
                "ENERGIZED_WITH_EXPLICIT_MOCKS"
                if is_energized
                else "MOCKED_LOCALLY_VALID_UNPOWERED"
            )
            level = BoardContinuityLevel.BC2_CONSTRAINED.value
        elif is_energized and not blocking:
            status = "VERIFIED_DIAGNOSTIC_COMPONENT"
            level = BoardContinuityLevel.BC5_VERIFIED.value
        else:
            status = "CONNECTED_GROUNDED_UNPOWERED"
            level = BoardContinuityLevel.BC4_AUTHORIZED.value
        components.append(
            WabooseBreadboardComponent(
                directive_id=directive_id,
                action_id=action.action_id,
                name=str(directive.get("name") or directive_id),
                risk=str(directive.get("risk") or "correctness"),
                direction=str(directive.get("direction") or "both"),
                connected_input_refs=connected,
                mocked_input_refs=mocked,
                output_refs=outputs,
                verifier_ids=action.verifier_ids,
                energized=is_energized,
                continuity=level,
                status=status,
            )
        )

    all_energized = all(component.energized for component in components)
    any_energized = any(component.energized for component in components)
    has_mocks = any(component.mocked_input_refs for component in components)
    if all_energized and continuity.continuity_complete and not has_mocks:
        circuit_status = "VERIFIED_DIAGNOSTIC_CIRCUIT"
    elif has_mocks and any_energized:
        circuit_status = "PARTIALLY_ENERGIZED_WITH_EXPLICIT_MOCKS"
    elif has_mocks:
        circuit_status = "DIAGNOSTIC_CIRCUIT_WITH_EXPLICIT_MOCKS"
    elif any_energized:
        circuit_status = "PARTIALLY_ENERGIZED_DIAGNOSTIC_CIRCUIT"
    else:
        circuit_status = "GROUNDED_DIAGNOSTIC_CIRCUIT_UNPOWERED"

    return {
        "ok": True,
        "version": CODING_WABOOSE_BREADBOARD_VERSION,
        "contract_id": contract_id,
        "phase": str(phase),
        "circuit_status": circuit_status,
        "has_explicit_mocks": has_mocks,
        "repair_handoff_eligible": (
            circuit_status == "VERIFIED_DIAGNOSTIC_CIRCUIT"
        ),
        "board": board.to_dict(),
        "board_digest": board.digest,
        "continuity": continuity.to_dict(),
        "components": [component.to_dict() for component in components],
        "forward_simulation": [
            {
                "directive_id": component.directive_id,
                "path": [
                    *component.connected_input_refs,
                    *component.mocked_input_refs,
                    f"action:{component.action_id}",
                    *component.output_refs,
                    (
                        f"decision:{component.directive_id}:"
                        "repair_handoff_or_no_defect"
                    ),
                ],
            }
            for component in components
        ],
        "backward_proof_requirements": [
            {
                "directive_id": component.directive_id,
                "required_for_repair_handoff": [
                    "exact_source_anchor",
                    "resolved_non_mocked_impact_or_control_flow_evidence",
                    "focus_execution_receipt",
                    "exact_source_check_receipt",
                    "human_review_decision",
                ],
            }
            for component in components
        ],
        "authority": {
            "class": BREADBOARD_AUTHORITY,
            "planning_proposes": True,
            "verification_proves": True,
            "human_authorizes": True,
            "execution_authority": False,
            "patch_authority": False,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
        },
    }


__all__ = [
    "BREADBOARD_AUTHORITY",
    "CODING_WABOOSE_BREADBOARD_VERSION",
    "WabooseBreadboardComponent",
    "compile_waboose_breadboard",
]
