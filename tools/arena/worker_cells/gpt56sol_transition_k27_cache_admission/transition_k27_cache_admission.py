from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from enum import Enum
from hashlib import sha256
import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "AURA-TRANSITION-K27-CACHE-ADMISSION-v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ID = re.compile(r"^[A-Za-z0-9_.:/@+-]{1,160}$")

class AdmissionError(ValueError):
    pass

class TransitionDisposition(str, Enum):
    EXACT_UNCHANGED = "EXACT_UNCHANGED"
    PROOF_NEUTRAL_REBIND = "PROOF_NEUTRAL_REBIND"
    CONSEQUENCE_CHANGED = "CONSEQUENCE_CHANGED"
    UNKNOWN = "UNKNOWN"

class Decision(str, Enum):
    ADMIT_RUNTIME_REUSE = "ADMIT_RUNTIME_REUSE"
    RECOMPUTE = "RECOMPUTE"
    HOLD = "HOLD"


def canon(v: Any) -> bytes:
    try:
        return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise AdmissionError("NON_CANONICAL") from exc


def digest(v: Any) -> str:
    return sha256(canon(v)).hexdigest()


def _id(v: Any, label: str) -> str:
    if not isinstance(v, str) or ID.fullmatch(v) is None:
        raise AdmissionError(f"INVALID_{label.upper()}")
    return v


def _h64(v: Any, label: str) -> str:
    if not isinstance(v, str) or HEX64.fullmatch(v) is None:
        raise AdmissionError(f"INVALID_{label.upper()}")
    return v


def _h40(v: Any, label: str) -> str:
    if not isinstance(v, str) or HEX40.fullmatch(v) is None:
        raise AdmissionError(f"INVALID_{label.upper()}")
    return v


def _keys(values: Iterable[str], label: str, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AdmissionError(f"INVALID_{label.upper()}")
    out = tuple(sorted(values))
    if not allow_empty and not out:
        raise AdmissionError(f"EMPTY_{label.upper()}")
    if len(out) != len(set(out)):
        raise AdmissionError(f"DUPLICATE_{label.upper()}")
    for v in out:
        _id(v, label)
    return out


def coordinate_for(identity_root: str) -> tuple[int, int, int]:
    raw = bytes.fromhex(_h64(identity_root, "identity_root"))
    return (raw[0] % 27, raw[1] % 27, raw[2] % 27)


@dataclass(frozen=True)
class TransitionReceipt:
    disposition: TransitionDisposition
    prior_generation: str
    current_generation: str
    provider_anchor_root: str
    dependency_root: str
    prior_consequence_root: str
    current_consequence_root: str
    dependency_keys: tuple[str, ...]
    changed_keys: tuple[str, ...]
    provider_observation_verified: bool
    authority_requested: bool
    receipt_root: str

    def body(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "-TRANSITION",
            "disposition": self.disposition.value if isinstance(self.disposition, TransitionDisposition) else self.disposition,
            "prior_generation": self.prior_generation,
            "current_generation": self.current_generation,
            "provider_anchor_root": self.provider_anchor_root,
            "dependency_root": self.dependency_root,
            "prior_consequence_root": self.prior_consequence_root,
            "current_consequence_root": self.current_consequence_root,
            "dependency_keys": list(_keys(self.dependency_keys, "dependency_keys")),
            "changed_keys": list(_keys(self.changed_keys, "changed_keys", allow_empty=True)),
            "provider_observation_verified": self.provider_observation_verified,
            "authority_requested": self.authority_requested,
        }


def make_transition_receipt(*, disposition: TransitionDisposition, prior_generation: str, current_generation: str,
                            provider_anchor_root: str, dependency_root: str, prior_consequence_root: str,
                            current_consequence_root: str, dependency_keys: Sequence[str], changed_keys: Sequence[str] = (),
                            provider_observation_verified: bool = True, authority_requested: bool = False) -> TransitionReceipt:
    if type(provider_observation_verified) is not bool or type(authority_requested) is not bool:
        raise AdmissionError("INVALID_TRANSITION_BOOL")
    _h40(prior_generation, "prior_generation"); _h40(current_generation, "current_generation")
    for name, value in (("provider_anchor_root", provider_anchor_root), ("dependency_root", dependency_root),
                        ("prior_consequence_root", prior_consequence_root), ("current_consequence_root", current_consequence_root)):
        _h64(value, name)
    provisional = TransitionReceipt(disposition, prior_generation, current_generation, provider_anchor_root, dependency_root,
                                    prior_consequence_root, current_consequence_root, _keys(dependency_keys, "dependency_keys"),
                                    _keys(changed_keys, "changed_keys", allow_empty=True), provider_observation_verified,
                                    authority_requested, "")
    return replace(provisional, receipt_root=digest(provisional.body()))


def verify_transition(t: TransitionReceipt) -> bool:
    if type(t) is not TransitionReceipt or not isinstance(t.disposition, TransitionDisposition):
        return False
    if type(t.provider_observation_verified) is not bool or type(t.authority_requested) is not bool:
        return False
    try:
        _h40(t.prior_generation, "prior_generation"); _h40(t.current_generation, "current_generation")
        _h64(t.provider_anchor_root, "provider_anchor_root"); _h64(t.dependency_root, "dependency_root")
        _h64(t.prior_consequence_root, "prior_consequence_root"); _h64(t.current_consequence_root, "current_consequence_root")
        _keys(t.dependency_keys, "dependency_keys"); _keys(t.changed_keys, "changed_keys", allow_empty=True)
        _h64(t.receipt_root, "receipt_root")
    except AdmissionError:
        return False
    if t.receipt_root != digest(t.body()):
        return False
    if t.authority_requested:
        return False
    if t.disposition is TransitionDisposition.EXACT_UNCHANGED:
        return (t.prior_generation == t.current_generation and not t.changed_keys and
                t.prior_consequence_root == t.current_consequence_root and t.provider_observation_verified)
    if t.disposition is TransitionDisposition.PROOF_NEUTRAL_REBIND:
        return (t.prior_consequence_root == t.current_consequence_root and t.provider_observation_verified and
                set(t.changed_keys).isdisjoint(t.dependency_keys))
    return True


@dataclass(frozen=True)
class K27Entry:
    subject_id: str
    identity_root: str
    coordinate: tuple[int, int, int]
    semantic_root: str
    provider_anchor_root: str
    dependency_root: str
    runtime_owner: str
    runtime_generation: str
    compatibility_profile: str
    benchmark_generation: str
    payload_hash: str
    cache_handle: str
    entry_root: str

    def body(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "-ENTRY",
            "subject_id": self.subject_id,
            "identity_root": self.identity_root,
            "coordinate": list(self.coordinate),
            "semantic_root": self.semantic_root,
            "provider_anchor_root": self.provider_anchor_root,
            "dependency_root": self.dependency_root,
            "runtime_owner": self.runtime_owner,
            "runtime_generation": self.runtime_generation,
            "compatibility_profile": self.compatibility_profile,
            "benchmark_generation": self.benchmark_generation,
            "payload_hash": self.payload_hash,
            "cache_handle": self.cache_handle,
        }


def make_entry(*, subject_id: str, semantic_root: str, provider_anchor_root: str, dependency_root: str,
               runtime_owner: str, runtime_generation: str, compatibility_profile: str,
               benchmark_generation: str, payload_hash: str, cache_handle: str) -> K27Entry:
    subject_id = _id(subject_id, "subject_id")
    identity_root = digest({"schema": SCHEMA + "-IDENTITY", "subject_id": subject_id})
    for name, value in (("semantic_root", semantic_root), ("provider_anchor_root", provider_anchor_root),
                        ("dependency_root", dependency_root), ("payload_hash", payload_hash)):
        _h64(value, name)
    for name, value in (("runtime_owner", runtime_owner), ("compatibility_profile", compatibility_profile),
                        ("cache_handle", cache_handle)):
        _id(value, name)
    _h40(runtime_generation, "runtime_generation"); _h40(benchmark_generation, "benchmark_generation")
    provisional = K27Entry(subject_id, identity_root, coordinate_for(identity_root), semantic_root, provider_anchor_root,
                           dependency_root, runtime_owner, runtime_generation, compatibility_profile,
                           benchmark_generation, payload_hash, cache_handle, "")
    return replace(provisional, entry_root=digest(provisional.body()))


def verify_entry(e: K27Entry) -> bool:
    if type(e) is not K27Entry:
        return False
    try:
        _id(e.subject_id, "subject_id")
        expected_identity = digest({"schema": SCHEMA + "-IDENTITY", "subject_id": e.subject_id})
        if e.identity_root != expected_identity or e.coordinate != coordinate_for(expected_identity):
            return False
        for name, value in (("semantic_root", e.semantic_root), ("provider_anchor_root", e.provider_anchor_root),
                            ("dependency_root", e.dependency_root), ("payload_hash", e.payload_hash),
                            ("entry_root", e.entry_root)):
            _h64(value, name)
        for name, value in (("runtime_owner", e.runtime_owner), ("compatibility_profile", e.compatibility_profile),
                            ("cache_handle", e.cache_handle)):
            _id(value, name)
        _h40(e.runtime_generation, "runtime_generation"); _h40(e.benchmark_generation, "benchmark_generation")
    except AdmissionError:
        return False
    return e.entry_root == digest(e.body())


@dataclass(frozen=True)
class CurrentContext:
    subject_id: str
    semantic_root: str
    provider_anchor_root: str
    dependency_root: str
    expected_runtime_owner: str
    runtime_generation: str
    compatibility_profile: str
    benchmark_generation: str
    payload_hash: str


@dataclass(frozen=True)
class RoutingSignals:
    recompute_cost: float
    dependency_fanout: int
    invocation_frequency: float
    locality: float
    queue_depth: int


@dataclass(frozen=True)
class AdmissionReceipt:
    decision: Decision
    reasons: tuple[str, ...]
    coordinate: tuple[int, int, int]
    route_score: float | None
    transition_root: str
    entry_root: str
    semantic_root: str
    dependency_root: str
    provider_anchor_root: str
    d0: bool
    truth_authority: bool
    effect_authority: bool
    gate10: bool
    receipt_root: str


def _validate_context(c: CurrentContext) -> None:
    if type(c) is not CurrentContext:
        raise AdmissionError("CURRENT_CONTEXT_REQUIRED")
    _id(c.subject_id, "subject_id")
    for name, value in (("semantic_root", c.semantic_root), ("provider_anchor_root", c.provider_anchor_root),
                        ("dependency_root", c.dependency_root), ("payload_hash", c.payload_hash)):
        _h64(value, name)
    _id(c.expected_runtime_owner, "expected_runtime_owner")
    _h40(c.runtime_generation, "runtime_generation")
    _id(c.compatibility_profile, "compatibility_profile")
    _h40(c.benchmark_generation, "benchmark_generation")


def _route_score(s: RoutingSignals) -> float:
    if type(s) is not RoutingSignals:
        raise AdmissionError("ROUTING_SIGNALS_REQUIRED")
    values = (s.recompute_cost, s.invocation_frequency, s.locality)
    if any(type(v) not in (int, float) or isinstance(v, bool) or not math.isfinite(float(v)) or float(v) < 0 for v in values):
        raise AdmissionError("INVALID_ROUTING_FLOAT")
    if type(s.dependency_fanout) is not int or isinstance(s.dependency_fanout, bool) or s.dependency_fanout < 0:
        raise AdmissionError("INVALID_FANOUT")
    if type(s.queue_depth) is not int or isinstance(s.queue_depth, bool) or s.queue_depth < 0:
        raise AdmissionError("INVALID_QUEUE_DEPTH")
    # Efficiency only. This score is never consulted by semantic admission.
    score = (float(s.recompute_cost) * (1 + s.dependency_fanout) * (1 + float(s.invocation_frequency)) *
             (1 + float(s.locality))) / (1 + s.queue_depth)
    if not math.isfinite(score):
        raise AdmissionError("ROUTING_SCORE_OVERFLOW")
    return round(score, 12)


def admission_reasons(t: TransitionReceipt, e: K27Entry, c: CurrentContext) -> tuple[str, ...]:
    out: list[str] = []
    if not verify_transition(t): out.append("INVALID_TRANSITION")
    if not verify_entry(e): out.append("INVALID_K27_ENTRY")
    try:
        _validate_context(c)
    except AdmissionError as exc:
        out.append(str(exc)); return tuple(out)
    if out:
        return tuple(out)
    if t.disposition in (TransitionDisposition.CONSEQUENCE_CHANGED, TransitionDisposition.UNKNOWN):
        out.append("TRANSITION_REQUIRES_RECOMPUTE")
    if e.subject_id != c.subject_id: out.append("SUBJECT_MISMATCH")
    if e.semantic_root != c.semantic_root: out.append("SEMANTIC_ROOT_MISMATCH")
    if e.provider_anchor_root != c.provider_anchor_root or e.provider_anchor_root != t.provider_anchor_root:
        out.append("PROVIDER_ANCHOR_MISMATCH")
    if e.dependency_root != c.dependency_root or e.dependency_root != t.dependency_root:
        out.append("DEPENDENCY_ROOT_MISMATCH")
    if e.runtime_owner != c.expected_runtime_owner: out.append("RUNTIME_OWNER_MISMATCH")
    if e.runtime_generation != c.runtime_generation: out.append("RUNTIME_GENERATION_MISMATCH")
    if e.compatibility_profile != c.compatibility_profile: out.append("COMPATIBILITY_PROFILE_MISMATCH")
    if e.benchmark_generation != c.benchmark_generation: out.append("BENCHMARK_GENERATION_MISMATCH")
    if e.payload_hash != c.payload_hash: out.append("PAYLOAD_HASH_MISMATCH")
    return tuple(out) or ("OK",)


def decide(t: TransitionReceipt, e: K27Entry, c: CurrentContext, signals: RoutingSignals) -> AdmissionReceipt:
    reasons = admission_reasons(t, e, c)
    score = None
    if reasons == ("OK",):
        try:
            score = _route_score(signals)
            decision = Decision.ADMIT_RUNTIME_REUSE
        except AdmissionError as exc:
            reasons = (str(exc),)
            decision = Decision.HOLD
            score = None
    elif any(r == "TRANSITION_REQUIRES_RECOMPUTE" for r in reasons):
        decision = Decision.RECOMPUTE
    else:
        decision = Decision.HOLD
    body = {
        "schema": SCHEMA + "-RECEIPT",
        "decision": decision.value,
        "reasons": list(reasons),
        "coordinate": list(e.coordinate) if type(e) is K27Entry else [-1, -1, -1],
        "route_score": score,
        "transition_root": t.receipt_root if type(t) is TransitionReceipt else "0" * 64,
        "entry_root": e.entry_root if type(e) is K27Entry else "0" * 64,
        "semantic_root": c.semantic_root if type(c) is CurrentContext else "0" * 64,
        "dependency_root": c.dependency_root if type(c) is CurrentContext else "0" * 64,
        "provider_anchor_root": c.provider_anchor_root if type(c) is CurrentContext else "0" * 64,
        "d0": True, "truth_authority": False, "effect_authority": False, "gate10": False,
    }
    root = digest(body)
    return AdmissionReceipt(decision, reasons, tuple(body["coordinate"]), score, body["transition_root"], body["entry_root"],
                            body["semantic_root"], body["dependency_root"], body["provider_anchor_root"],
                            True, False, False, False, root)


def classify8(state: Sequence[int]) -> bool:
    return len(state) == 8 and all(type(x) is int and x == 2 for x in state)


def classify13(state: Sequence[int]) -> bool:
    if len(state) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in state):
        return False
    return classify8(state[:8])


def demo_fixture(disposition: TransitionDisposition = TransitionDisposition.PROOF_NEUTRAL_REBIND):
    h = lambda s: sha256(s.encode()).hexdigest()
    g1 = "1" * 40; g2 = g1 if disposition is TransitionDisposition.EXACT_UNCHANGED else "2" * 40
    sem = h("semantic"); prov = h("provider"); dep = h("dependency"); payload = h("payload")
    changed = () if disposition is TransitionDisposition.EXACT_UNCHANGED else ("docs",)
    t = make_transition_receipt(disposition=disposition, prior_generation=g1, current_generation=g2,
                                provider_anchor_root=prov, dependency_root=dep, prior_consequence_root=sem,
                                current_consequence_root=sem if disposition is not TransitionDisposition.CONSEQUENCE_CHANGED else h("changed-sem"),
                                dependency_keys=("model", "runtime", "trace"), changed_keys=changed,
                                provider_observation_verified=True)
    e = make_entry(subject_id="arena:demo", semantic_root=sem, provider_anchor_root=prov, dependency_root=dep,
                   runtime_owner="runtime-owner", runtime_generation="3"*40, compatibility_profile="kv-v1",
                   benchmark_generation="4"*40, payload_hash=payload, cache_handle="runtime:opaque:1")
    c = CurrentContext("arena:demo", sem, prov, dep, "runtime-owner", "3"*40, "kv-v1", "4"*40, payload)
    s = RoutingSignals(10.0, 3, 4.0, 0.8, 2)
    return t, e, c, s
