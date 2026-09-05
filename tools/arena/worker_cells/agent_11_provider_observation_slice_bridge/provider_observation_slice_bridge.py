from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
from itertools import product
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

SCHEMA = "AURA-PROVIDER-OBSERVATION-SLICE-BRIDGE-v2"
RECEIPT_SCHEMA = SCHEMA + "-RECEIPT"
AGENT10_PARENT_COMMIT = "1bed171bc842ab98e51bd85c37a4b49ab9194aef"
EVIDENCE_DAG_PARENT_COMMIT = "8d97a5f0fb0efefedf3daa2e36161c5eecc93fb1"
EVIDENCE_DAG_SCHEMA = "AURA-EVIDENCE-SLICE-DAG-v2"
ADMISSION_SCHEMA = "AURA-EXTERNAL-WITNESS-ADMISSION-v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class BridgeError(ValueError):
    pass


class EvidenceStatus(str, Enum):
    OBSERVED = "OBSERVED"
    ATTESTED = "ATTESTED"
    CONTESTED = "CONTESTED"
    EXPIRED = "EXPIRED"
    INDETERMINATE = "INDETERMINATE"


class Decision(str, Enum):
    REPROVE_MINIMUM_SLICE = "REPROVE_MINIMUM_SLICE"
    HOLD_PROVIDER_EVIDENCE = "HOLD_PROVIDER_EVIDENCE"
    HOLD_MOVEMENT_BINDING = "HOLD_MOVEMENT_BINDING"
    HOLD_SEMANTIC_ADMISSION = "HOLD_SEMANTIC_ADMISSION"
    HOLD_DAG_PLAN = "HOLD_DAG_PLAN"


def canon(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BridgeError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canon(value)).hexdigest()


def _nonempty(value: str, name: str) -> str:
    if type(value) is not str or not value:
        raise BridgeError(f"INVALID_STRING:{name}")
    return value


def _hex40(value: str, name: str) -> str:
    if type(value) is not str or HEX40.fullmatch(value) is None:
        raise BridgeError(f"INVALID_HEX40:{name}")
    return value


def _hex64(value: str, name: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise BridgeError(f"INVALID_HEX64:{name}")
    return value


def canonical_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)) or not paths:
        raise BridgeError("INVALID_CHANGED_PATHS")
    out = tuple(sorted(paths))
    if len(set(out)) != len(out):
        raise BridgeError("DUPLICATE_CHANGED_PATH")
    for path in out:
        if type(path) is not str or not path or path.startswith("/") or ".." in path.split("/"):
            raise BridgeError("INVALID_CHANGED_PATH")
    return out


def canonical_nodes(nodes: Sequence[str], name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(nodes, (str, bytes)) or (not nodes and not allow_empty):
        raise BridgeError(f"INVALID_NODE_SET:{name}")
    out = tuple(sorted(nodes))
    if len(set(out)) != len(out) or any(type(n) is not str or not n for n in out):
        raise BridgeError(f"INVALID_NODE_SET:{name}")
    return out


def _https_uri(value: str, name: str) -> str:
    value = _nonempty(value, name)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise BridgeError(f"INVALID_HTTPS_URI:{name}")
    return value


def _pairs(values: tuple[tuple[str, str], ...], name: str, *, second_hex64: bool = False) -> tuple[tuple[str, str], ...]:
    if type(values) is not tuple:
        raise BridgeError(f"INVALID_TUPLE:{name}")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in values:
        if type(item) is not tuple or len(item) != 2:
            raise BridgeError(f"INVALID_PAIR:{name}")
        left = _nonempty(item[0], f"{name}.left")
        right = _hex64(item[1], f"{name}.right") if second_hex64 else _nonempty(item[1], f"{name}.right")
        if left in seen:
            raise BridgeError(f"DUPLICATE_PAIR_KEY:{name}")
        seen.add(left)
        out.append((left, right))
    return tuple(sorted(out))


@dataclass(frozen=True)
class ProviderObservation:
    provider: str
    repository: str
    change_request_id: str
    parent_head: str
    child_head: str
    actor_identity: str
    generator_identity: str
    changed_paths: tuple[str, ...]
    evidence_uri: str
    captured_at: str
    verifier_id: str
    verifier_generation: str
    status: EvidenceStatus
    payload_sha256: str
    observation_root: str


def observation_body(o: ProviderObservation) -> dict[str, Any]:
    return {
        "provider": o.provider,
        "repository": o.repository,
        "change_request_id": o.change_request_id,
        "parent_head": o.parent_head,
        "child_head": o.child_head,
        "actor_identity": o.actor_identity,
        "generator_identity": o.generator_identity,
        "changed_paths": list(canonical_paths(o.changed_paths)),
        "evidence_uri": o.evidence_uri,
        "captured_at": o.captured_at,
        "verifier_id": o.verifier_id,
        "verifier_generation": o.verifier_generation,
        "status": o.status.value if isinstance(o.status, EvidenceStatus) else o.status,
        "payload_sha256": o.payload_sha256,
    }


def validate_observation(o: ProviderObservation) -> None:
    if type(o) is not ProviderObservation:
        raise BridgeError("PROVIDER_OBSERVATION_REQUIRED")
    for name in ("provider", "repository", "change_request_id", "actor_identity", "generator_identity", "captured_at", "verifier_id", "verifier_generation"):
        _nonempty(getattr(o, name), name)
    _hex40(o.parent_head, "parent_head")
    _hex40(o.child_head, "child_head")
    canonical_paths(o.changed_paths)
    _https_uri(o.evidence_uri, "evidence_uri")
    if not isinstance(o.status, EvidenceStatus):
        raise BridgeError("INVALID_EVIDENCE_STATUS")
    _hex64(o.payload_sha256, "payload_sha256")
    _hex64(o.observation_root, "observation_root")
    if o.observation_root != digest(observation_body(o)):
        raise BridgeError("OBSERVATION_ROOT_MISMATCH")


@dataclass(frozen=True)
class MovementExpectation:
    provider: str
    repository: str
    change_request_id: str
    proved_parent_head: str
    current_child_head: str
    expected_generator_identity: str
    allowed_proof_neutral_paths: tuple[str, ...]
    accepted_verifier_ids: tuple[str, ...]
    agent10_semantic_commit: str = AGENT10_PARENT_COMMIT


def validate_expectation(e: MovementExpectation) -> None:
    if type(e) is not MovementExpectation:
        raise BridgeError("MOVEMENT_EXPECTATION_REQUIRED")
    for name in ("provider", "repository", "change_request_id", "expected_generator_identity"):
        _nonempty(getattr(e, name), name)
    _hex40(e.proved_parent_head, "proved_parent_head")
    _hex40(e.current_child_head, "current_child_head")
    canonical_paths(e.allowed_proof_neutral_paths)
    if type(e.accepted_verifier_ids) is not tuple or not e.accepted_verifier_ids:
        raise BridgeError("INVALID_ACCEPTED_VERIFIERS")
    if len(set(e.accepted_verifier_ids)) != len(e.accepted_verifier_ids) or any(type(v) is not str or not v for v in e.accepted_verifier_ids):
        raise BridgeError("INVALID_ACCEPTED_VERIFIERS")
    if e.agent10_semantic_commit != AGENT10_PARENT_COMMIT:
        raise BridgeError("WRONG_AGENT10_PARENT_GENERATION")


@dataclass(frozen=True)
class PathBinding:
    path: str
    evidence_nodes: tuple[str, ...]


def validate_bindings(bindings: Sequence[PathBinding]) -> Mapping[str, tuple[str, ...]]:
    if isinstance(bindings, (str, bytes)) or not bindings:
        raise BridgeError("PATH_BINDINGS_REQUIRED")
    out: dict[str, tuple[str, ...]] = {}
    for binding in bindings:
        if type(binding) is not PathBinding:
            raise BridgeError("INVALID_PATH_BINDING")
        path = canonical_paths((binding.path,))[0]
        if path in out:
            raise BridgeError("DUPLICATE_PATH_BINDING")
        out[path] = canonical_nodes(binding.evidence_nodes, f"binding:{path}")
    return out


@dataclass(frozen=True)
class SemanticAdmissionSurface:
    graph_root: str
    verifier_generations: tuple[tuple[str, str], ...]
    accepted_witness_roots: tuple[tuple[str, str], ...]
    observation_generation: str
    external_receipt_root: str
    surface_root: str


def semantic_admission_body(a: SemanticAdmissionSurface) -> dict[str, Any]:
    return {
        "schema": ADMISSION_SCHEMA,
        "graph_root": a.graph_root,
        "verifier_generations": _pairs(a.verifier_generations, "verifier_generations"),
        "accepted_witness_roots": _pairs(a.accepted_witness_roots, "accepted_witness_roots", second_hex64=True),
        "observation_generation": a.observation_generation,
        "external_receipt_root": a.external_receipt_root,
    }


def validate_semantic_admission(a: SemanticAdmissionSurface) -> None:
    if type(a) is not SemanticAdmissionSurface:
        raise BridgeError("SEMANTIC_ADMISSION_REQUIRED")
    _hex64(a.graph_root, "admission.graph_root")
    _pairs(a.verifier_generations, "verifier_generations")
    _pairs(a.accepted_witness_roots, "accepted_witness_roots", second_hex64=True)
    _nonempty(a.observation_generation, "admission.observation_generation")
    _hex64(a.external_receipt_root, "admission.external_receipt_root")
    _hex64(a.surface_root, "admission.surface_root")
    if a.surface_root != digest(semantic_admission_body(a)):
        raise BridgeError("SEMANTIC_ADMISSION_ROOT_MISMATCH")


@dataclass(frozen=True)
class SlicePlanAttestation:
    graph_root: str
    changed_roots: tuple[str, ...]
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    admission_surface_root: str
    decision: str
    plan_root: str
    dag_semantic_commit: str = EVIDENCE_DAG_PARENT_COMMIT
    dag_schema: str = EVIDENCE_DAG_SCHEMA


def validate_plan_shape(p: SlicePlanAttestation) -> None:
    if type(p) is not SlicePlanAttestation:
        raise BridgeError("SLICE_PLAN_REQUIRED")
    _hex64(p.graph_root, "graph_root")
    _hex64(p.plan_root, "plan_root")
    _hex64(p.admission_surface_root, "admission_surface_root")
    canonical_nodes(p.changed_roots, "changed_roots")
    canonical_nodes(p.invalidated, "invalidated")
    canonical_nodes(p.recompute_order, "recompute_order")
    canonical_nodes(p.reusable, "reusable", allow_empty=True)
    canonical_nodes(p.affected_consequence_keys, "affected_consequence_keys", allow_empty=True)
    if p.decision not in {"RECOMPUTE_MINIMUM_SLICE", "RECOMPUTE_ALL"}:
        raise BridgeError("INVALID_PLAN_DECISION")
    if p.dag_semantic_commit != EVIDENCE_DAG_PARENT_COMMIT:
        raise BridgeError("WRONG_DAG_PARENT_GENERATION")
    if p.dag_schema != EVIDENCE_DAG_SCHEMA:
        raise BridgeError("WRONG_DAG_SCHEMA")
    if not set(p.changed_roots).issubset(set(p.invalidated)):
        raise BridgeError("CHANGED_ROOT_NOT_INVALIDATED")
    if set(p.invalidated) & set(p.reusable):
        raise BridgeError("INVALIDATED_REUSABLE_OVERLAP")
    if set(p.recompute_order) != set(p.invalidated):
        raise BridgeError("RECOMPUTE_ORDER_COVERAGE_MISMATCH")


@dataclass(frozen=True)
class BridgeEvidence:
    observation: ProviderObservation
    expectation: MovementExpectation
    bindings: tuple[PathBinding, ...]
    semantic_admission: SemanticAdmissionSurface
    slice_plan: SlicePlanAttestation
    expected_graph_root: str
    authority_requested: bool = False


@dataclass(frozen=True)
class Receipt:
    schema: str
    decision: Decision
    reasons: tuple[str, ...]
    provider: str
    repository: str
    change_request_id: str
    parent_head: str
    child_head: str
    observation_root: str
    payload_sha256: str
    provider_status: str
    changed_paths: tuple[str, ...]
    changed_evidence_nodes: tuple[str, ...]
    graph_root: str
    semantic_admission_surface_root: str
    semantic_external_receipt_root: str
    semantic_observation_generation: str
    slice_plan_root: str
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    agent10_semantic_commit: str
    dag_semantic_commit: str
    dag_schema: str
    evidence_root: str
    fresh_hosted_pass: bool = False
    effect_authority: bool = False
    gate10: bool = False
    receipt_root: str = ""

    def without_root(self) -> dict[str, Any]:
        body = asdict(self)
        body["decision"] = self.decision.value
        body.pop("receipt_root")
        return body


def movement_reasons(e: BridgeEvidence) -> tuple[str, ...]:
    try:
        validate_observation(e.observation)
        validate_expectation(e.expectation)
        binding_map = validate_bindings(e.bindings)
    except BridgeError as exc:
        return (str(exc),)
    o, x = e.observation, e.expectation
    out: list[str] = []
    if o.provider != x.provider: out.append("PROVIDER_MISMATCH")
    if o.repository != x.repository: out.append("REPOSITORY_MISMATCH")
    if o.change_request_id != x.change_request_id: out.append("CHANGE_REQUEST_MISMATCH")
    if o.parent_head != x.proved_parent_head: out.append("PARENT_HEAD_MISMATCH")
    if o.child_head != x.current_child_head: out.append("CHILD_HEAD_MISMATCH")
    if o.generator_identity != x.expected_generator_identity: out.append("GENERATOR_IDENTITY_MISMATCH")
    if o.verifier_id not in x.accepted_verifier_ids: out.append("UNACCEPTED_VERIFIER")
    if not set(o.changed_paths).issubset(set(x.allowed_proof_neutral_paths)): out.append("NON_NEUTRAL_CHANGED_PATH")
    if any(path not in binding_map for path in o.changed_paths): out.append("UNBOUND_CHANGED_PATH")
    if type(e.authority_requested) is not bool: out.append("INVALID_AUTHORITY_BOOL")
    elif e.authority_requested: out.append("AUTHORITY_REQUESTED")
    return tuple(out) or ("OK",)


def changed_evidence_nodes(e: BridgeEvidence) -> tuple[str, ...]:
    binding_map = validate_bindings(e.bindings)
    return tuple(sorted({node for path in e.observation.changed_paths for node in binding_map[path]}))


def semantic_admission_reasons(e: BridgeEvidence) -> tuple[str, ...]:
    try:
        validate_semantic_admission(e.semantic_admission)
        _hex64(e.expected_graph_root, "expected_graph_root")
    except BridgeError as exc:
        return (str(exc),)
    if e.semantic_admission.graph_root != e.expected_graph_root:
        return ("SEMANTIC_ADMISSION_GRAPH_MISMATCH",)
    return ("OK",)


def plan_reasons(e: BridgeEvidence) -> tuple[str, ...]:
    try:
        validate_plan_shape(e.slice_plan)
        _hex64(e.expected_graph_root, "expected_graph_root")
        nodes = changed_evidence_nodes(e)
    except BridgeError as exc:
        return (str(exc),)
    p = e.slice_plan
    out: list[str] = []
    if p.graph_root != e.expected_graph_root: out.append("GRAPH_ROOT_MISMATCH")
    if p.changed_roots != nodes: out.append("CHANGED_ROOT_BINDING_MISMATCH")
    if p.admission_surface_root != e.semantic_admission.surface_root: out.append("ADMISSION_SURFACE_BINDING_MISMATCH")
    if p.graph_root != e.semantic_admission.graph_root: out.append("PLAN_ADMISSION_GRAPH_MISMATCH")
    return tuple(out) or ("OK",)


def reasons(e: BridgeEvidence) -> tuple[str, ...]:
    if type(e) is not BridgeEvidence:
        return ("INVALID_EVIDENCE_TYPE",)
    movement = movement_reasons(e)
    if movement != ("OK",):
        return movement
    if e.observation.status is not EvidenceStatus.ATTESTED:
        return (f"PROVIDER_EVIDENCE_{e.observation.status.value}",)
    semantic = semantic_admission_reasons(e)
    if semantic != ("OK",):
        return semantic
    plan = plan_reasons(e)
    if plan != ("OK",):
        return plan
    return ("OK",)


def decide(e: BridgeEvidence) -> Decision:
    rs = reasons(e)
    if rs == ("OK",):
        return Decision.REPROVE_MINIMUM_SLICE
    if rs and rs[0].startswith("PROVIDER_EVIDENCE_"):
        return Decision.HOLD_PROVIDER_EVIDENCE
    movement_markers = {
        "PROVIDER_MISMATCH", "REPOSITORY_MISMATCH", "CHANGE_REQUEST_MISMATCH", "PARENT_HEAD_MISMATCH",
        "CHILD_HEAD_MISMATCH", "GENERATOR_IDENTITY_MISMATCH", "UNACCEPTED_VERIFIER", "NON_NEUTRAL_CHANGED_PATH",
        "UNBOUND_CHANGED_PATH", "AUTHORITY_REQUESTED", "INVALID_AUTHORITY_BOOL", "OBSERVATION_ROOT_MISMATCH",
        "INVALID_EVIDENCE_STATUS", "INVALID_CHANGED_PATH", "INVALID_CHANGED_PATHS", "DUPLICATE_CHANGED_PATH",
        "WRONG_AGENT10_PARENT_GENERATION", "DUPLICATE_PATH_BINDING", "INVALID_PATH_BINDING", "PATH_BINDINGS_REQUIRED",
    }
    semantic_markers = {
        "SEMANTIC_ADMISSION_REQUIRED", "SEMANTIC_ADMISSION_ROOT_MISMATCH", "SEMANTIC_ADMISSION_GRAPH_MISMATCH",
        "INVALID_TUPLE", "INVALID_PAIR", "DUPLICATE_PAIR_KEY",
    }
    bases = {reason.split(":", 1)[0] for reason in rs}
    if bases & movement_markers:
        return Decision.HOLD_MOVEMENT_BINDING
    if bases & semantic_markers or any(reason.startswith("INVALID_HEX64:admission.") or reason.startswith("INVALID_STRING:admission.") for reason in rs):
        return Decision.HOLD_SEMANTIC_ADMISSION
    return Decision.HOLD_DAG_PLAN


def evidence_root(e: BridgeEvidence) -> str:
    return digest({
        "schema": SCHEMA,
        "observation": observation_body(e.observation) | {"observation_root": e.observation.observation_root},
        "expectation": asdict(e.expectation),
        "bindings": [asdict(binding) for binding in e.bindings],
        "semantic_admission": asdict(e.semantic_admission),
        "slice_plan": asdict(e.slice_plan),
        "expected_graph_root": e.expected_graph_root,
        "authority_requested": e.authority_requested,
    })


def make_receipt(e: BridgeEvidence) -> Receipt:
    rs = reasons(e)
    decision = decide(e)
    try:
        nodes = changed_evidence_nodes(e)
        o, p, a = e.observation, e.slice_plan, e.semantic_admission
        provider, repository, change_request_id = o.provider, o.repository, o.change_request_id
        parent_head, child_head = o.parent_head, o.child_head
        observation_root, payload_sha256, status = o.observation_root, o.payload_sha256, o.status.value
        changed_paths = canonical_paths(o.changed_paths)
        graph_root = p.graph_root
        admission_root = a.surface_root
        external_receipt_root = a.external_receipt_root
        observation_generation = a.observation_generation
        plan_root = p.plan_root
        invalidated, reusable = p.invalidated, p.reusable
        recompute_order, keys = p.recompute_order, p.affected_consequence_keys
        dag_schema = p.dag_schema
    except Exception:
        nodes = ()
        provider = repository = change_request_id = status = observation_generation = dag_schema = "INVALID"
        parent_head = child_head = "0" * 40
        observation_root = payload_sha256 = graph_root = admission_root = external_receipt_root = plan_root = "0" * 64
        changed_paths = invalidated = reusable = recompute_order = keys = ()
    base = Receipt(
        RECEIPT_SCHEMA, decision, rs, provider, repository, change_request_id, parent_head, child_head,
        observation_root, payload_sha256, status, changed_paths, nodes, graph_root, admission_root,
        external_receipt_root, observation_generation, plan_root, invalidated, reusable, recompute_order, keys,
        AGENT10_PARENT_COMMIT, EVIDENCE_DAG_PARENT_COMMIT, dag_schema,
        evidence_root(e) if type(e) is BridgeEvidence else "0" * 64,
        False, False, False, "",
    )
    return replace(base, receipt_root=digest(base.without_root()))


def verify_receipt(e: BridgeEvidence, receipt: Receipt) -> bool:
    if type(receipt) is not Receipt or receipt.schema != RECEIPT_SCHEMA:
        return False
    try:
        expected = make_receipt(e)
    except Exception:
        return False
    return receipt == expected and receipt.receipt_root == digest(receipt.without_root()) and not receipt.fresh_hosted_pass and not receipt.effect_authority and not receipt.gate10


AXES8 = (
    "provider_identity_integrity",
    "provider_attestation_status",
    "movement_binding",
    "path_to_evidence_binding",
    "semantic_admission_surface",
    "dag_plan_binding",
    "current_generation",
    "authority_ceiling",
)


def classify8(state: Sequence[int]) -> str:
    if len(state) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in state):
        raise BridgeError("INVALID_OMEGA8")
    if any(v == 0 for v in state[:7]) or state[7] == 0:
        return "HOLD_HARD_INVALID"
    if any(v == 1 for v in state[:7]):
        return "HOLD_UNRESOLVED"
    if state[7] == 2:
        return "HOLD_AUTHORITY_WIDENING"
    return Decision.REPROVE_MINIMUM_SLICE.value


def classify13(state: Sequence[int]) -> str:
    if len(state) != 13 or any(type(v) is not int or v not in (0, 1, 2) for v in state):
        raise BridgeError("INVALID_13D")
    core = classify8(state[:8])
    if core != Decision.REPROVE_MINIMUM_SLICE.value:
        return core
    tail = state[8:]
    if 0 in tail:
        return "HOLD_TRAILING_INVALID"
    if 1 in tail:
        return "HOLD_TRAILING_UNRESOLVED"
    return core


def exhaustive8() -> dict[str, int]:
    out: dict[str, int] = {}
    for state in product(range(3), repeat=8):
        result = classify8(state)
        out[result] = out.get(result, 0) + 1
    return out


def observation_for(*, provider: str, repository: str, change_request_id: str, parent_head: str, child_head: str,
                    actor_identity: str, generator_identity: str, changed_paths: Sequence[str], evidence_uri: str,
                    captured_at: str, verifier_id: str, verifier_generation: str, status: EvidenceStatus,
                    payload_sha256: str) -> ProviderObservation:
    provisional = ProviderObservation(
        provider, repository, change_request_id, parent_head, child_head, actor_identity, generator_identity,
        canonical_paths(changed_paths), evidence_uri, captured_at, verifier_id, verifier_generation, status,
        _hex64(payload_sha256, "payload_sha256"), "0" * 64,
    )
    return replace(provisional, observation_root=digest(observation_body(provisional)))


def semantic_admission_for(*, graph_root: str, verifier_generations: tuple[tuple[str, str], ...],
                           accepted_witness_roots: tuple[tuple[str, str], ...], observation_generation: str,
                           external_receipt_root: str) -> SemanticAdmissionSurface:
    provisional = SemanticAdmissionSurface(
        _hex64(graph_root, "admission.graph_root"),
        _pairs(verifier_generations, "verifier_generations"),
        _pairs(accepted_witness_roots, "accepted_witness_roots", second_hex64=True),
        _nonempty(observation_generation, "admission.observation_generation"),
        _hex64(external_receipt_root, "admission.external_receipt_root"),
        "0" * 64,
    )
    return replace(provisional, surface_root=digest(semantic_admission_body(provisional)))
