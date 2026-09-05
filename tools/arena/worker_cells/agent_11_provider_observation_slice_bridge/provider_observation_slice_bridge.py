from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
from itertools import product
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

SCHEMA = "AURA-PROVIDER-OBSERVATION-SLICE-BRIDGE-v1"
RECEIPT_SCHEMA = SCHEMA + "-RECEIPT"
AGENT10_PARENT_COMMIT = "1bed171bc842ab98e51bd85c37a4b49ab9194aef"
EVIDENCE_DAG_PARENT_COMMIT = "88aa998ae80677375ebc8fcda3ea08c7cb894a6e"
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
    HOLD_DAG_PLAN = "HOLD_DAG_PLAN"


def canon(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise BridgeError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canon(value)).hexdigest()


def _nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise BridgeError(f"INVALID_STRING:{name}")
    return value


def _hex40(value: str, name: str) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        raise BridgeError(f"INVALID_HEX40:{name}")
    return value


def _hex64(value: str, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise BridgeError(f"INVALID_HEX64:{name}")
    return value


def canonical_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)) or not paths:
        raise BridgeError("INVALID_CHANGED_PATHS")
    out = tuple(sorted(paths))
    if len(set(out)) != len(out):
        raise BridgeError("DUPLICATE_CHANGED_PATH")
    for path in out:
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            raise BridgeError("INVALID_CHANGED_PATH")
    return out


def canonical_nodes(nodes: Sequence[str], name: str) -> tuple[str, ...]:
    if isinstance(nodes, (str, bytes)) or not nodes:
        raise BridgeError(f"INVALID_NODE_SET:{name}")
    out = tuple(sorted(nodes))
    if len(set(out)) != len(out) or any(not isinstance(n, str) or not n for n in out):
        raise BridgeError(f"INVALID_NODE_SET:{name}")
    return out


def _https_uri(value: str, name: str) -> str:
    value = _nonempty(value, name)
    p = urlparse(value)
    if p.scheme != "https" or not p.netloc:
        raise BridgeError(f"INVALID_HTTPS_URI:{name}")
    return value


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
    if isinstance(e.accepted_verifier_ids, (str, bytes)) or not e.accepted_verifier_ids:
        raise BridgeError("INVALID_ACCEPTED_VERIFIERS")
    if len(set(e.accepted_verifier_ids)) != len(e.accepted_verifier_ids) or any(not isinstance(v, str) or not v for v in e.accepted_verifier_ids):
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
    for b in bindings:
        if type(b) is not PathBinding:
            raise BridgeError("INVALID_PATH_BINDING")
        path = canonical_paths((b.path,))[0]
        if path in out:
            raise BridgeError("DUPLICATE_PATH_BINDING")
        out[path] = canonical_nodes(b.evidence_nodes, f"binding:{path}")
    return out


@dataclass(frozen=True)
class SlicePlanAttestation:
    graph_root: str
    changed_roots: tuple[str, ...]
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    decision: str
    plan_root: str
    dag_semantic_commit: str = EVIDENCE_DAG_PARENT_COMMIT


def validate_plan_shape(p: SlicePlanAttestation) -> None:
    if type(p) is not SlicePlanAttestation:
        raise BridgeError("SLICE_PLAN_REQUIRED")
    _hex64(p.graph_root, "graph_root")
    _hex64(p.plan_root, "plan_root")
    for name in ("changed_roots", "invalidated", "recompute_order"):
        canonical_nodes(getattr(p, name), name)
    if isinstance(p.reusable, (str, bytes)):
        raise BridgeError("INVALID_REUSABLE_SET")
    if len(set(p.reusable)) != len(p.reusable) or any(not isinstance(x, str) or not x for x in p.reusable):
        raise BridgeError("INVALID_REUSABLE_SET")
    if isinstance(p.affected_consequence_keys, (str, bytes)):
        raise BridgeError("INVALID_CONSEQUENCE_KEYS")
    if len(set(p.affected_consequence_keys)) != len(p.affected_consequence_keys) or any(not isinstance(x, str) or not x for x in p.affected_consequence_keys):
        raise BridgeError("INVALID_CONSEQUENCE_KEYS")
    if p.decision not in {"RECOMPUTE_MINIMUM_SLICE", "RECOMPUTE_ALL"}:
        raise BridgeError("INVALID_PLAN_DECISION")
    if p.dag_semantic_commit != EVIDENCE_DAG_PARENT_COMMIT:
        raise BridgeError("WRONG_DAG_PARENT_GENERATION")
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
    verification_status: str
    changed_paths: tuple[str, ...]
    changed_evidence_nodes: tuple[str, ...]
    graph_root: str
    slice_plan_root: str
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    agent10_semantic_commit: str
    dag_semantic_commit: str
    evidence_root: str
    fresh_hosted_pass: bool = False
    effect_authority: bool = False
    gate10: bool = False
    receipt_root: str = ""

    def without_root(self) -> dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        d.pop("receipt_root")
        return d


def movement_reasons(e: BridgeEvidence) -> tuple[str, ...]:
    try:
        validate_observation(e.observation)
        validate_expectation(e.expectation)
        binding_map = validate_bindings(e.bindings)
    except BridgeError as exc:
        return (str(exc),)
    o, x = e.observation, e.expectation
    out: list[str] = []
    if o.provider != x.provider:
        out.append("PROVIDER_MISMATCH")
    if o.repository != x.repository:
        out.append("REPOSITORY_MISMATCH")
    if o.change_request_id != x.change_request_id:
        out.append("CHANGE_REQUEST_MISMATCH")
    if o.parent_head != x.proved_parent_head:
        out.append("PARENT_HEAD_MISMATCH")
    if o.child_head != x.current_child_head:
        out.append("CHILD_HEAD_MISMATCH")
    if o.generator_identity != x.expected_generator_identity:
        out.append("GENERATOR_IDENTITY_MISMATCH")
    if o.verifier_id not in x.accepted_verifier_ids:
        out.append("UNACCEPTED_VERIFIER")
    if not set(o.changed_paths).issubset(set(x.allowed_proof_neutral_paths)):
        out.append("NON_NEUTRAL_CHANGED_PATH")
    missing = [p for p in o.changed_paths if p not in binding_map]
    if missing:
        out.append("UNBOUND_CHANGED_PATH")
    if type(e.authority_requested) is not bool:
        out.append("INVALID_AUTHORITY_BOOL")
    elif e.authority_requested:
        out.append("AUTHORITY_REQUESTED")
    return tuple(out) or ("OK",)


def changed_evidence_nodes(e: BridgeEvidence) -> tuple[str, ...]:
    binding_map = validate_bindings(e.bindings)
    return tuple(sorted({n for p in e.observation.changed_paths for n in binding_map[p]}))


def plan_reasons(e: BridgeEvidence) -> tuple[str, ...]:
    try:
        validate_plan_shape(e.slice_plan)
        _hex64(e.expected_graph_root, "expected_graph_root")
        nodes = changed_evidence_nodes(e)
    except BridgeError as exc:
        return (str(exc),)
    p = e.slice_plan
    out: list[str] = []
    if p.graph_root != e.expected_graph_root:
        out.append("GRAPH_ROOT_MISMATCH")
    if p.changed_roots != nodes:
        out.append("CHANGED_ROOT_BINDING_MISMATCH")
    return tuple(out) or ("OK",)


def reasons(e: BridgeEvidence) -> tuple[str, ...]:
    if type(e) is not BridgeEvidence:
        return ("INVALID_EVIDENCE_TYPE",)
    movement = movement_reasons(e)
    if movement != ("OK",):
        return movement
    if e.observation.status is not EvidenceStatus.ATTESTED:
        return (f"PROVIDER_EVIDENCE_{e.observation.status.value}",)
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
    if any(r.split(":", 1)[0] in movement_markers for r in rs):
        return Decision.HOLD_MOVEMENT_BINDING
    return Decision.HOLD_DAG_PLAN


def evidence_root(e: BridgeEvidence) -> str:
    return digest({
        "schema": SCHEMA,
        "observation": observation_body(e.observation) | {"observation_root": e.observation.observation_root},
        "expectation": asdict(e.expectation),
        "bindings": [asdict(b) for b in e.bindings],
        "slice_plan": asdict(e.slice_plan),
        "expected_graph_root": e.expected_graph_root,
        "authority_requested": e.authority_requested,
    })


def make_receipt(e: BridgeEvidence) -> Receipt:
    rs = reasons(e)
    decision = decide(e)
    try:
        nodes = changed_evidence_nodes(e)
        o, p = e.observation, e.slice_plan
        provider, repository, cr = o.provider, o.repository, o.change_request_id
        parent, child = o.parent_head, o.child_head
        obs_root, payload = o.observation_root, o.payload_sha256
        status = o.status.value
        changed_paths = canonical_paths(o.changed_paths)
        graph_root, plan_root = p.graph_root, p.plan_root
        invalidated, reusable, order, keys = p.invalidated, p.reusable, p.recompute_order, p.affected_consequence_keys
    except Exception:
        nodes = ()
        provider = repository = cr = status = "INVALID"
        parent = child = "0" * 40
        obs_root = payload = graph_root = plan_root = "0" * 64
        changed_paths = invalidated = reusable = order = keys = ()
    base = Receipt(
        RECEIPT_SCHEMA, decision, rs, provider, repository, cr, parent, child, obs_root, payload, status,
        changed_paths, nodes, graph_root, plan_root, invalidated, reusable, order, keys,
        AGENT10_PARENT_COMMIT, EVIDENCE_DAG_PARENT_COMMIT,
        evidence_root(e) if type(e) is BridgeEvidence else "0" * 64,
        False, False, False, ""
    )
    return replace(base, receipt_root=digest(base.without_root()))


def verify_receipt(e: BridgeEvidence, receipt: Receipt) -> bool:
    if type(receipt) is not Receipt or receipt.schema != RECEIPT_SCHEMA:
        return False
    try:
        expected = make_receipt(e)
    except Exception:
        return False
    return (
        receipt == expected
        and receipt.receipt_root == digest(receipt.without_root())
        and receipt.fresh_hosted_pass is False
        and receipt.effect_authority is False
        and receipt.gate10 is False
    )


AXES8 = (
    "provider_identity",
    "observation_integrity",
    "attestation_status",
    "movement_binding",
    "path_to_evidence_binding",
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


def observation_for(
    *, provider: str, repository: str, change_request_id: str, parent_head: str, child_head: str,
    actor_identity: str, generator_identity: str, changed_paths: Sequence[str], evidence_uri: str,
    captured_at: str, verifier_id: str, verifier_generation: str, status: EvidenceStatus,
    payload_sha256: str,
) -> ProviderObservation:
    provisional = ProviderObservation(
        provider, repository, change_request_id, parent_head, child_head, actor_identity, generator_identity,
        canonical_paths(changed_paths), evidence_uri, captured_at, verifier_id, verifier_generation, status,
        _hex64(payload_sha256, "payload_sha256"), ""
    )
    root = digest(observation_body(provisional))
    return replace(provisional, observation_root=root)
