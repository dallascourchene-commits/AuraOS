"""Deterministic toolchain bindings for Aura's unified memory/continuity lifecycle.

This adapter compiles the canonical contracts in ``aura_unified_memory_continuity``
from an already prepared Agent Bridge session. It creates no new store, truth,
routing, verifier, policy, or authority plane. Owner projections are reference-only
and never auto-promote learning, commit code, open a PR, merge, or mutate production.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import time
from typing import Any

from aura_event_contracts import stable_digest
from aura_model_cognome import ModelEndpointIdentity
from aura_unified_memory_continuity import (
    ArenaEvidenceItem,
    AuthorityEnvelope,
    ContinuityDelta,
    ContinuitySensitivityReceipt,
    EvidenceTruthClass,
    IntentPacket,
    LearningToReproofDecision,
    ModelProfileRef,
    QDKTConsequentialAdmission,
    SemanticDefinition,
    SemanticLedger,
    compile_act_capsule_envelope,
    compile_arena_evidence_slice,
    compile_model_execution_packet,
)

TOOLCHAIN_VERSION = "AURA_UNIFIED_MEMORY_CONTINUITY_TOOLCHAIN_V1"
BINDING_VERSION = "AURA_UNIFIED_EXECUTION_BINDING_V1"
PROJECTION_VERSION = "AURA_UNIFIED_CONTINUITY_OWNER_PROJECTIONS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_PROHIBITIONS = (
    "no direct production mutation",
    "no automatic commit",
    "no automatic push",
    "no automatic pull request",
    "no automatic merge",
    "no automatic learning promotion",
    "no model-vote authority",
)
_INVARIANTS = (
    "canonical human intent is model-independent",
    "minimum-sufficient evidence remains exactly recoverable",
    "P0 is committed before P1 is observed",
    "independent verification precedes consequential learning",
    "human or community authority disposes",
)
_CONTINUITY = (
    "return a compact Continuity Delta",
    "preserve protected pathways",
    "retain accepted, denied, failed, and rolled-back attempt references",
    "require current reproof before learning eligibility",
)
_REQUIRED_TERMS = ("memory", "continuity", "verified", "authority")
_LEGAL_OUTCOMES = ("EXECUTE", "VERIFY", "REPAIR", "ESCALATE", "REFUSE")


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str))


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        value = ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be an array")
    result = tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _path(value: Any) -> str:
    text = _required(value, "repository path").replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("repository path must remain relative")
    return candidate.as_posix().removeprefix("./")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _file_digest(root: Path, value: Any) -> str:
    relative = _path(value)
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("repository path escaped root") from exc
    if not target.is_file():
        raise ValueError(f"evidence file is missing: {relative}")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def repository_identity(repo_root: str | Path) -> dict[str, str]:
    root = Path(repo_root).resolve()
    head = _required(_git(root, "rev-parse", "HEAD"), "repository head")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "repository_head": head,
        "working_tree_digest": stable_digest({"head": head, "status": status.splitlines()}),
        "codemap_digest": _file_digest(root, ".aura/CODEMAP.json"),
    }


def _authority(value: Any) -> AuthorityEnvelope:
    if value is None:
        return AuthorityEnvelope(inspect=True, edit=True, test=True)
    if isinstance(value, AuthorityEnvelope):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("authority must be an object")
    names = set(AuthorityEnvelope.__dataclass_fields__)
    if set(value) - names:
        raise ValueError("authority contains unknown fields")
    normalized: dict[str, bool] = {}
    for name in names:
        item = value.get(name, False)
        if type(item) is not bool:
            raise ValueError(f"authority.{name} must be a boolean")
        normalized[name] = item
    return AuthorityEnvelope(**normalized)


def _semantics(value: Any) -> tuple[SemanticDefinition, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("semantic_definitions must be an array")
    result = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("semantic_definitions must contain objects")
        result.append(
            SemanticDefinition(
                term=_required(item.get("term"), "semantic term"),
                means=_strings(item.get("means"), "means", required=True),
                does_not_mean=_strings(item.get("does_not_mean"), "does_not_mean"),
                source_refs=_strings(item.get("source_refs"), "source_refs", required=True),
                freshness=str(item.get("freshness") or "CURRENT"),
            )
        )
    if not result:
        raise ValueError("semantic_definitions must not be empty")
    return tuple(result)


def _endpoint(value: Any) -> ModelEndpointIdentity:
    if isinstance(value, ModelEndpointIdentity):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("model_profile.endpoint_identity must be an object")
    now = time.time()
    endpoint = ModelEndpointIdentity.create(
        provider=_required(value.get("provider"), "provider"),
        requested_model=_required(value.get("requested_model"), "requested_model"),
        returned_model=str(value.get("returned_model") or value.get("requested_model") or ""),
        base_url_digest=str(value.get("base_url_digest") or ""),
        access_class=str(value.get("access_class") or "BLACK_BOX"),
        endpoint_fingerprint=str(value.get("endpoint_fingerprint") or ""),
        fingerprint_version=str(value.get("fingerprint_version") or "identity-v1"),
        provider_revision=str(value.get("provider_revision") or ""),
        tokenizer_family=str(value.get("tokenizer_family") or ""),
        price_snapshot_digest=str(value.get("price_snapshot_digest") or ""),
        first_seen_at=float(value.get("first_seen_at", now)),
        last_seen_at=float(value.get("last_seen_at", now)),
        status=str(value.get("status") or "ACTIVE"),
    )
    if value.get("profile_id") and value.get("profile_id") != endpoint.profile_id:
        raise ValueError("endpoint profile_id failed canonical validation")
    return endpoint


def _canonical_capsule(bridge: Any, phase_hash: str, task_id: str) -> Any:
    session = bridge._require_session(phase_hash)
    plan = getattr(session.get("prepared"), "plan", None)
    match = next(
        (
            item
            for item in list(getattr(plan, "act_capsules", []) or [])
            if str(getattr(item, "task_id", "")) == task_id
        ),
        None,
    )
    if match is None:
        raise ValueError(f"canonical ActCapsule not found for task_id={task_id}")
    return match


def _evidence(root: Path, micro: Mapping[str, Any]) -> tuple[list[ArenaEvidenceItem], list[str], list[str], list[str]]:
    items: list[ArenaEvidenceItem] = []
    required_refs: list[str] = []
    files: list[str] = []
    symbols: list[str] = []

    def add_file(raw: Any, reason: str, truth: EvidenceTruthClass, suffix: str = "") -> None:
        path = _path(raw)
        digest = _file_digest(root, path)
        ref = f"{truth.value.lower()}:{path}{suffix}:{digest}"
        if ref in required_refs:
            return
        items.append(ArenaEvidenceItem(ref, reason, truth, path, digest, "CURRENT", True))
        required_refs.append(ref)
        if path not in files:
            files.append(path)

    for row in list(micro.get("line_ranges") or []):
        if not isinstance(row, Mapping) or not row.get("file"):
            continue
        bounds = list(row.get("line_range") or [])
        suffix = f"#L{int(bounds[0])}-L{int(bounds[1])}" if len(bounds) >= 2 else ""
        add_file(row["file"], "Exact source span changes action or proof.", EvidenceTruthClass.EXACT_SOURCE, suffix)
        symbol = str(row.get("symbol") or "").strip()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    if not files and micro.get("target_file"):
        add_file(micro["target_file"], "Canonical Act Capsule target source.", EvidenceTruthClass.EXACT_SOURCE)
    target_symbol = str(micro.get("target_symbol") or "").strip()
    if target_symbol and target_symbol not in symbols:
        symbols.append(target_symbol)
    for test_path in list(micro.get("tests") or []):
        add_file(test_path, "Focused test defines a proof obligation.", EvidenceTruthClass.EXACT_TEST)

    route = {
        "route_decision": dict(micro.get("route_decision") or {}),
        "target_file": micro.get("target_file"),
        "target_symbol": micro.get("target_symbol"),
        "line_ranges": list(micro.get("line_ranges") or []),
    }
    route_digest = stable_digest(route)
    route_ref = f"exact_receipt:agent_bridge_route:{route_digest}"
    items.append(
        ArenaEvidenceItem(
            route_ref,
            "Prepared Bridge route determines bounded execution eligibility.",
            EvidenceTruthClass.EXACT_RECEIPT,
            "aura_agent_arena_bridge.AuraAgentArenaBridge",
            route_digest,
            "CURRENT",
            True,
        )
    )
    required_refs.append(route_ref)
    return items, required_refs, files, symbols


@dataclass(frozen=True)
class UnifiedExecutionBinding:
    plan_phase_hash: str
    task_id: str
    records: Mapping[str, Any]
    owner_refs: Mapping[str, str]
    authority: Mapping[str, Any]
    binding_digest: str
    binding_id: str
    version: str = BINDING_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", _copy(dict(self.records)))
        object.__setattr__(self, "owner_refs", _copy(dict(self.owner_refs)))
        object.__setattr__(self, "authority", _copy(dict(self.authority)))
        if self.version != BINDING_VERSION or self.authority.get("patch_authority") != PATCH_AUTHORITY:
            raise ValueError("unified binding authority or version changed")
        forbidden = (
            "automatic_commit",
            "automatic_push",
            "automatic_pull_request",
            "automatic_merge",
            "automatic_promotion",
            "production_mutation",
            "model_vote_authority",
        )
        if any(self.authority.get(name) is not False for name in forbidden):
            raise ValueError("unified binding gained forbidden authority")
        expected = stable_digest(self.identity_payload())
        if self.binding_digest != expected or self.binding_id != f"umcbind_{expected}":
            raise ValueError("unified binding identity mismatch")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "plan_phase_hash": self.plan_phase_hash,
            "task_id": self.task_id,
            "records": _copy(self.records),
            "owner_refs": _copy(self.owner_refs),
            "authority": _copy(self.authority),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            **self.identity_payload(),
            "binding_digest": self.binding_digest,
            "version": self.version,
        }


def compile_bridge_execution_binding(
    bridge: Any,
    *,
    plan_phase_hash: str,
    task_id: str,
    contract: Mapping[str, Any],
) -> UnifiedExecutionBinding:
    """Compile a model-relative packet from one exact prepared Bridge task."""
    if not isinstance(contract, Mapping):
        raise ValueError("contract must be an object")
    phase_hash = _required(plan_phase_hash, "plan_phase_hash")
    task = _required(task_id, "task_id")
    root = Path(bridge.repo_root).resolve()
    repo = repository_identity(root)
    expected_head = str(contract.get("expected_repository_head") or "")
    if expected_head and expected_head != repo["repository_head"]:
        raise ValueError("expected_repository_head differs from exact current head")
    capsule = _canonical_capsule(bridge, phase_hash, task)
    micro = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash, task_id=task, depth=1, format="both", max_tokens_est=2000
    )
    if not isinstance(micro, Mapping) or micro.get("ok") is not True:
        raise ValueError("Bridge micro-context is unavailable")
    items, refs, files, symbols = _evidence(root, micro)

    acceptance = (_required(getattr(capsule, "acceptance", ""), "Act Capsule acceptance"),)
    intent = IntentPacket.create(
        objective=_required(getattr(capsule, "objective", ""), "Act Capsule objective"),
        purpose=_required(contract.get("purpose"), "purpose"),
        user_meaning=_required(contract.get("user_meaning"), "user_meaning"),
        mode=str(contract.get("mode") or "EXECUTE"),
        arena=str(contract.get("arena") or "Coding"),
        constraints=tuple(
            dict.fromkeys([*getattr(capsule, "constraints", []), *_strings(contract.get("constraints"), "constraints")])
        ),
        prohibitions=tuple(dict.fromkeys([*_PROHIBITIONS, *_strings(contract.get("prohibitions"), "prohibitions")])),
        authority=_authority(contract.get("authority")),
        acceptance_criteria=acceptance,
        required_evidence=(
            "minimum-sufficient exact source/test evidence",
            "Bridge route receipt",
            "independent verifier evidence",
        ),
        risk_class=str(contract.get("risk_class") or "architecture"),
        cost_budget=str(contract.get("cost_budget") or "bounded"),
        context_budget=str(contract.get("context_budget") or "minimum sufficient"),
        privacy_class=str(contract.get("privacy_class") or "PROJECT"),
        freshness_requirement=str(contract.get("freshness_requirement") or "CURRENT_HEAD"),
        output_contract=str(contract.get("output_contract") or "bounded result plus evidence-backed Continuity Delta"),
    )
    ledger = SemanticLedger.create(
        intent_digest=intent.intent_digest, definitions=_semantics(contract.get("semantic_definitions"))
    )
    evidence_slice = compile_arena_evidence_slice(
        repository_head=repo["repository_head"],
        working_tree_digest=repo["working_tree_digest"],
        codemap_digest=repo["codemap_digest"],
        objective_digest=intent.intent_digest,
        candidate_items=items,
        required_refs=refs,
        prohibitions=intent.prohibitions,
        required_verifiers=_strings(
            contract.get("required_verifiers") or ("pytest", "Coding Waboose"), "required_verifiers", required=True
        ),
    )
    envelope = compile_act_capsule_envelope(
        legacy_act_capsule=capsule,
        intent=intent,
        semantic_ledger=ledger,
        arena_slice=evidence_slice,
        allowed_files=files,
        allowed_symbols=symbols,
        prohibited_effects=intent.prohibitions,
        invariants=_INVARIANTS,
        allowed_tools=_strings(contract.get("allowed_tools") or ("pytest", "Coding Waboose"), "allowed_tools"),
        acceptance_bundle=acceptance,
        repair_budget=int(contract.get("repair_budget", 2)),
        legal_outcomes=_LEGAL_OUTCOMES,
        continuity_requirements=_strings(
            contract.get("continuity_requirements") or _CONTINUITY, "continuity_requirements", required=True
        ),
        required_semantic_terms=_strings(
            contract.get("required_semantic_terms") or _REQUIRED_TERMS, "required_semantic_terms", required=True
        ),
    )
    model_value = contract.get("model_profile")
    if not isinstance(model_value, Mapping):
        raise ValueError("model_profile must be an object")
    profile = ModelProfileRef.create(
        endpoint_identity=_endpoint(model_value.get("endpoint_identity")),
        calibrated_at=float(model_value.get("calibrated_at")),
        expires_at=float(model_value.get("expires_at")),
        evidence_refs=_strings(model_value.get("evidence_refs"), "model evidence_refs", required=True),
        uncertainty=float(model_value.get("uncertainty", 0.5)),
    )
    source_digest = stable_digest({path: _file_digest(root, path) for path in sorted(files)})
    role = _required(getattr(capsule, "role", ""), "Act Capsule role")
    packet = compile_model_execution_packet(
        intent=intent,
        act_envelope=envelope,
        arena_slice=evidence_slice,
        model_profile=profile,
        current_source_digest=source_digest,
        provider_config_digest=_required(contract.get("provider_config_digest"), "provider_config_digest"),
        selected_role=role,
        task_slice=f"{task}:{micro.get('target_file') or ''}::{micro.get('target_symbol') or ''}",
        prompt_structure=_strings(
            contract.get("prompt_structure") or ("agent kernel", "intent", "semantics", "evidence", "acceptance"),
            "prompt_structure",
            required=True,
        ),
        evidence_refs=refs,
        context_order=_strings(
            contract.get("context_order") or ("intent", "authority", "semantics", "evidence", "acceptance"),
            "context_order",
            required=True,
        ),
        examples=tuple(dict(item) for item in list(contract.get("examples") or []) if isinstance(item, Mapping)),
        tools_available=_strings(contract.get("tools_available") or ("pytest",), "tools_available"),
        reasoning_budget=str(contract.get("reasoning_budget") or "bounded"),
        output_schema=str(contract.get("output_schema") or "unified_diff_plus_continuity_delta"),
        uncertainty_requirements=_strings(
            contract.get("uncertainty_requirements")
            or ("label unsupported claims", "separate evidence from inference"),
            "uncertainty_requirements",
            required=True,
        ),
        stop_conditions=_strings(
            contract.get("stop_conditions")
            or ("repository identity changes", "scope expands", "invariant violation", "repair budget exhausted"),
            "stop_conditions",
            required=True,
        ),
        retry_policy=str(contract.get("retry_policy") or "bounded local repair only"),
        escalation_policy=str(contract.get("escalation_policy") or "Council V3 or human review"),
        disagreement_refs=_strings(contract.get("disagreement_refs"), "disagreement_refs"),
        observed_at=float(contract.get("observed_at", time.time())),
    )

    from aura_arena_st3gg_codec import should_st3gg_encode_arena_capsule
    from aura_jspace_codec import attach_jspace_to_capsule

    grounding = {
        "route": dict(micro.get("route_decision") or {}).get("route", ""),
        "line_ranges": list(micro.get("line_ranges") or []),
        "source_hashes": {path: _file_digest(root, path) for path in files},
        "tests": list(micro.get("tests") or []),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    jspace = attach_jspace_to_capsule(packet.to_dict(), grounding=grounding)
    st3gg = should_st3gg_encode_arena_capsule(jspace)
    lanes = ["scope", "tests"]
    if packet.disagreement_refs or packet.required_verification_depth > 1:
        lanes.append("continuity")
    if envelope.continuity_requirements:
        lanes.append("rollback")
    records = {
        "intent_packet": intent.to_dict(),
        "semantic_ledger": ledger.to_dict(),
        "arena_evidence_slice": evidence_slice.to_dict(),
        "act_capsule_envelope": envelope.to_dict(),
        "model_profile": profile.to_dict(),
        "model_execution_packet": packet.to_dict(),
        "jspace": {
            "packet": jspace.get("jspace_packet", ""),
            "state": jspace.get("jspace_state", {}),
            "advisory_only": True,
        },
        "st3gg": {"decision": asdict(st3gg), "recall_written": False, "advisory_only": True},
        "council": {
            "required_lanes": list(dict.fromkeys(lanes)),
            "required_verification_depth": packet.required_verification_depth,
            "disagreement_refs": list(packet.disagreement_refs),
            "p0_required": True,
            "proposal_only": True,
        },
    }
    owners = {
        "intent": "aura_unified_memory_continuity.IntentPacket",
        "act_capsule": "aura_architect_loop.ActCapsule",
        "model_identity": "aura_model_cognome.ModelEndpointIdentity",
        "bridge": "aura_agent_arena_bridge.AuraAgentArenaBridge",
        "council": "aura_architect_council_v3.SelectiveArchitectFusionCouncil",
        "forge": "aura_forge.AuraForgeRuntime",
        "crucible": "aura_arena_crucible.ArenaCrucibleService",
        "relationship_experience": "aura_relationship_experience.RelationshipExperienceObservation",
        "qdkt": "aura_qdkt.UnifiedQDKT",
        "state_ledger": "aura_refactor_state_ledger_core.RefactorStateLedger",
        "temporal_persistence": "aura_arena_persistence_adapters.ArenaPersistenceCoordinator",
        "attempt_archive": "aura_arena_attempt_archive.ArenaAttemptArchive",
        "st3gg": "aura_arena_st3gg_codec.ArenaST3GGCapsule",
        "jspace": "aura_jspace_codec.AuraJPacket",
        "observatory": "aura_temporal_persistence.TemporalCheckpointRegistry.observatory_projection",
    }
    authority_projection = {
        "planning_proposes": True,
        "verification_proves": True,
        "human_or_community_authority_disposes": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "model_vote_authority": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "automatic_promotion": False,
        "production_mutation": False,
    }
    identity = {
        "plan_phase_hash": phase_hash,
        "task_id": task,
        "records": records,
        "owner_refs": owners,
        "authority": authority_projection,
    }
    digest = stable_digest(identity)
    return UnifiedExecutionBinding(phase_hash, task, records, owners, authority_projection, digest, f"umcbind_{digest}")


def _typed(value: Any, expected: type[Any], name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, expected):
        raise ValueError(f"{name} must use canonical {expected.__name__}")
    return value.to_dict()


def compile_continuity_owner_projections(
    binding: UnifiedExecutionBinding,
    *,
    continuity_delta: ContinuityDelta | None = None,
    continuity_receipt: ContinuitySensitivityReceipt | None = None,
    learning_decision: LearningToReproofDecision | None = None,
    qdkt_admission: QDKTConsequentialAdmission | None = None,
) -> dict[str, Any]:
    """Produce explicit, reference-only owner packets; perform no writes."""
    if not isinstance(binding, UnifiedExecutionBinding):
        raise ValueError("binding must use canonical UnifiedExecutionBinding")
    delta = _typed(continuity_delta, ContinuityDelta, "continuity_delta")
    receipt = _typed(continuity_receipt, ContinuitySensitivityReceipt, "continuity_receipt")
    learning = _typed(learning_decision, LearningToReproofDecision, "learning_decision")
    admission = _typed(qdkt_admission, QDKTConsequentialAdmission, "qdkt_admission")
    packet = dict(binding.records["model_execution_packet"])
    intent = dict(binding.records["intent_packet"])
    exact_refs = list(packet.get("evidence_refs") or [])
    refs = {
        "binding_id": binding.binding_id,
        "binding_digest": binding.binding_digest,
        "continuity_delta_ref": delta.get("delta_id", ""),
        "continuity_receipt_ref": receipt.get("receipt_id", ""),
        "learning_decision_ref": learning.get("decision_id", ""),
        "qdkt_admission_ref": admission.get("decision_id", ""),
    }
    digest = stable_digest(refs)
    checkpoint = {
        **refs,
        "intent_digest": intent.get("intent_digest", ""),
        "model_execution_packet_digest": packet.get("packet_digest", ""),
        "repository_head": packet.get("repository_head", ""),
        "working_tree_digest": packet.get("working_tree_digest", ""),
        "source_digest": packet.get("source_digest", ""),
        "exact_evidence_refs": exact_refs,
        "raw_payload_retained": False,
        "automatic_resume": False,
        "automatic_promotion": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    result = {
        "version": PROJECTION_VERSION,
        "projection_id": f"umcproj_{digest}",
        "projection_digest": digest,
        **refs,
        "bridge": {
            "owner": binding.owner_refs["bridge"],
            "plan_phase_hash": binding.plan_phase_hash,
            "task_id": binding.task_id,
        },
        "council": {"owner": binding.owner_refs["council"], **dict(binding.records["council"])},
        "forge": {
            "owner": binding.owner_refs["forge"],
            "binding_digest": binding.binding_digest,
            "p0_required": True,
            "human_review_required": True,
        },
        "crucible": {
            "owner": binding.owner_refs["crucible"],
            "continuity_receipt_ref": receipt.get("receipt_id", ""),
            "raw_evidence_refs": list(receipt.get("raw_evidence_refs") or exact_refs),
            "proposal_only": True,
            "automatic_grammar_promotion": False,
        },
        "relationship_experience": {
            "owner": binding.owner_refs["relationship_experience"],
            "eligible": learning.get("eligible") is True,
            "automatic_record": False,
            "human_disposition_required": True,
        },
        "qdkt": {
            "owner": binding.owner_refs["qdkt"],
            "admitted": admission.get("admitted") is True,
            "proposal_only": True,
            "automatic_observe": False,
            "automatic_crystallization": False,
        },
        "state_ledger": {
            "owner": binding.owner_refs["state_ledger"],
            "execution_state_ref": f"aura://unified-memory-continuity/{binding.binding_id}",
            "raw_payload_retained": False,
        },
        "temporal_persistence": {
            "owner": binding.owner_refs["temporal_persistence"],
            "source_kind": "UNIFIED_MEMORY_CONTINUITY_BINDING",
            "checkpoint_state": checkpoint,
            "automatic_resume": False,
            "restore_mode": "ASSESSMENT_ONLY",
        },
        "attempt_archive": {
            "owner": binding.owner_refs["attempt_archive"],
            "archive_context": {"objective": intent.get("objective", ""), **refs, "exact_evidence_refs": exact_refs},
            "automatic_record": False,
            "learning_authority": False,
        },
        "st3gg": dict(binding.records["st3gg"]),
        "jspace": dict(binding.records["jspace"]),
        "observatory": {
            "owner": binding.owner_refs["observatory"],
            "binding_id": binding.binding_id,
            "intent_digest": intent.get("intent_digest", ""),
            "protected_pathways": list(receipt.get("protected_pathways") or []),
            "prediction_error": list(receipt.get("prediction_error") or []),
            "missing_measurements": list(receipt.get("missing_measurements") or []),
            "projection_only": True,
        },
        "authority": dict(binding.authority),
    }
    return _copy(result)


__all__ = [
    "BINDING_VERSION",
    "PATCH_AUTHORITY",
    "PROJECTION_VERSION",
    "TOOLCHAIN_VERSION",
    "UnifiedExecutionBinding",
    "compile_bridge_execution_binding",
    "compile_continuity_owner_projections",
    "repository_identity",
]
