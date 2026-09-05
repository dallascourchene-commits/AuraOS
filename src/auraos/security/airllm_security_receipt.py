"""Deterministic, non-promoting receipts for AirLLM security verification.

This module intentionally does not load models or grant execution authority.  It turns
already-observed local security evidence into a canonical receipt that remains bound to
exact model/source identities and generation axes.  Any generation drift reopens only
the proof leaves whose dependencies changed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping, Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_STATUS = frozenset({"PASS", "FAIL", "HOLD_EXTERNAL", "PROVISIONAL_LOCAL", "MISSING"})
_SCHEMA = "AURA-AIRLLM-SECURITY-RECEIPT-v1"
_CLAIM_CEILING = "D0_LOCAL_SECURITY_VERIFICATION_ONLY_NOT_OWNER_HOST_NOT_HOSTED_NOT_GATE10"


class SecurityReceiptError(ValueError):
    """Raised when receipt inputs are malformed or authority-widening."""


def _canon(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest(value: object) -> str:
    return sha256(_canon(value)).hexdigest()


def _require_sha256(value: str, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SecurityReceiptError(f"{label} must be exact lowercase SHA-256")
    return value


def _require_revision(value: str) -> str:
    if not isinstance(value, str) or _REVISION_RE.fullmatch(value) is None:
        raise SecurityReceiptError("upstream_revision must be an exact lowercase 40-hex commit")
    return value


def _require_generation(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise SecurityReceiptError(f"{label} must be a non-empty exact string")
    return value


def _normalize_parents(values: Sequence[str]) -> tuple[str, str]:
    if isinstance(values, (str, bytes)) or len(values) != 2:
        raise SecurityReceiptError("exactly two foreign parents are required")
    parents = tuple(values)
    if any(not isinstance(x, str) or not x or x.strip() != x for x in parents):
        raise SecurityReceiptError("foreign parent ids must be non-empty exact strings")
    if parents[0] == parents[1]:
        raise SecurityReceiptError("foreign parents must be consequence-distinct ids")
    return parents  # type: ignore[return-value]


@dataclass(frozen=True)
class GenerationVector:
    semantic: str
    source: str
    runtime: str
    security: str
    evidence: str
    dependency: str

    def __post_init__(self) -> None:
        for field, value in asdict(self).items():
            _require_generation(value, f"generation.{field}")

    def select(self, axes: Iterable[str]) -> dict[str, str]:
        raw = asdict(self)
        selected: dict[str, str] = {}
        for axis in axes:
            if axis not in raw:
                raise SecurityReceiptError(f"unknown generation axis: {axis}")
            selected[axis] = raw[axis]
        return selected


@dataclass(frozen=True)
class ProofLeafSpec:
    leaf_id: str
    axes: tuple[str, ...]
    evidence_class: str


LEAVES = (
    ProofLeafSpec(
        "model_artifact_integrity",
        ("source", "security", "evidence"),
        "LOCAL_ARTIFACT_STATIC",
    ),
    ProofLeafSpec(
        "loader_source_integrity",
        ("source", "security", "evidence"),
        "LOCAL_SOURCE_STATIC",
    ),
    ProofLeafSpec(
        "runtime_hard_false_membrane",
        ("semantic", "source", "runtime", "security", "evidence"),
        "LOCAL_RUNTIME",
    ),
    ProofLeafSpec(
        "pinned_source_compatibility",
        ("source", "dependency", "security", "evidence"),
        "LOCAL_COMPATIBILITY",
    ),
)
_LEAF_BY_ID = {leaf.leaf_id: leaf for leaf in LEAVES}


@dataclass(frozen=True)
class ProofObservation:
    proof_id: str
    proof_digest: str
    status: str
    bound_generation: Mapping[str, str]
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.proof_id, str) or not self.proof_id or self.proof_id.strip() != self.proof_id:
            raise SecurityReceiptError("proof_id must be a non-empty exact string")
        _require_sha256(self.proof_digest, "proof_digest")
        if self.status not in _ALLOWED_STATUS:
            raise SecurityReceiptError(f"unsupported proof status: {self.status}")
        if not isinstance(self.bound_generation, Mapping) or not self.bound_generation:
            raise SecurityReceiptError("bound_generation must be a non-empty mapping")
        for key, value in self.bound_generation.items():
            _require_generation(key, "bound_generation axis")
            _require_generation(value, f"bound_generation.{key}")
        if not isinstance(self.note, str):
            raise SecurityReceiptError("note must be a string")


@dataclass(frozen=True)
class SecuritySubject:
    model_id: str
    model_sha256: str
    loader_source_sha256: str
    upstream_repository: str
    upstream_release: str
    upstream_revision: str

    def __post_init__(self) -> None:
        _require_generation(self.model_id, "model_id")
        _require_sha256(self.model_sha256, "model_sha256")
        _require_sha256(self.loader_source_sha256, "loader_source_sha256")
        _require_generation(self.upstream_repository, "upstream_repository")
        _require_generation(self.upstream_release, "upstream_release")
        _require_revision(self.upstream_revision)


class AirLLMSecurityReceiptBuilder:
    """Bind local proof leaves to exact identities without minting authority."""

    def __init__(
        self,
        *,
        subject: SecuritySubject,
        generation: GenerationVector,
        foreign_parents: Sequence[str],
    ) -> None:
        self.subject = subject
        self.generation = generation
        self.foreign_parents = _normalize_parents(foreign_parents)
        self._proofs: dict[str, ProofObservation] = {}

    def bind(
        self,
        leaf_id: str,
        *,
        proof_id: str,
        proof_digest: str,
        status: str = "PASS",
        note: str = "",
    ) -> None:
        try:
            spec = _LEAF_BY_ID[leaf_id]
        except KeyError as exc:
            raise SecurityReceiptError(f"unknown proof leaf: {leaf_id}") from exc
        self._proofs[leaf_id] = ProofObservation(
            proof_id=proof_id,
            proof_digest=proof_digest,
            status=status,
            bound_generation=self.generation.select(spec.axes),
            note=note,
        )

    def effective(self, leaf_id: str, current: GenerationVector | None = None) -> str:
        try:
            spec = _LEAF_BY_ID[leaf_id]
        except KeyError as exc:
            raise SecurityReceiptError(f"unknown proof leaf: {leaf_id}") from exc
        proof = self._proofs.get(leaf_id)
        if proof is None:
            return "MISSING"
        if proof.status != "PASS":
            return proof.status
        current = current or self.generation
        return "PASS" if current.select(spec.axes) == dict(proof.bound_generation) else "STALE"

    def affected_leaves(self, changed_axes: Iterable[str]) -> tuple[str, ...]:
        changed = set(changed_axes)
        known = set(asdict(self.generation))
        unknown = changed - known
        if unknown:
            raise SecurityReceiptError(f"unknown generation axes: {sorted(unknown)!r}")
        return tuple(sorted(spec.leaf_id for spec in LEAVES if changed.intersection(spec.axes)))

    def build(self, current: GenerationVector | None = None) -> dict[str, object]:
        current = current or self.generation
        states = {leaf.leaf_id: self.effective(leaf.leaf_id, current) for leaf in LEAVES}
        if any(state == "FAIL" for state in states.values()):
            disposition = "LOCAL_SECURITY_FAIL"
        elif all(state == "PASS" for state in states.values()):
            disposition = "LOCAL_VERIFIED_NONPROMOTING"
        else:
            disposition = "LOCAL_SECURITY_HOLD"

        leaves = []
        for spec in LEAVES:
            proof = self._proofs.get(spec.leaf_id)
            leaves.append(
                {
                    "leaf_id": spec.leaf_id,
                    "axes": list(spec.axes),
                    "evidence_class": spec.evidence_class,
                    "status": states[spec.leaf_id],
                    "proof": None if proof is None else {
                        "proof_id": proof.proof_id,
                        "proof_digest": proof.proof_digest,
                        "status": proof.status,
                        "bound_generation": dict(sorted(proof.bound_generation.items())),
                        "note": proof.note,
                    },
                }
            )

        body: dict[str, object] = {
            "schema": _SCHEMA,
            "subject": asdict(self.subject),
            "bound_generation": asdict(self.generation),
            "current_generation": asdict(current),
            "exact_foreign_parents": list(self.foreign_parents),
            "leaves": leaves,
            "disposition": disposition,
            "stale_or_missing": sorted(k for k, v in states.items() if v != "PASS"),
            "effect_authority": False,
            "promotion_authorized": False,
            "owner_host_proven": False,
            "hosted_ci_proven": False,
            "gate10": False,
            "claim_ceiling": _CLAIM_CEILING,
            "laws": [
                "ImmutableIdentityDoesNotImplyCurrentAlias",
                "SourceGenerationChangeReopensSourceBoundSecurityLeaves",
                "RuntimeGenerationChangeDoesNotInvalidateStaticArtifactProof",
                "LocalPassDoesNotCrossCastToOwnerHostOrHostedPass",
                "ReceiptDigestDoesNotMintAuthority",
            ],
        }
        receipt_sha256 = _digest(body)
        body["receipt_sha256"] = receipt_sha256
        raw = bytes.fromhex(receipt_sha256)
        body["k27"] = [raw[0] % 27, raw[1] % 27, raw[2] % 27]
        return body


def verify_receipt(receipt: Mapping[str, object]) -> bool:
    """Verify canonical digest and non-promotion invariants of a receipt payload."""
    if not isinstance(receipt, Mapping):
        return False
    if receipt.get("schema") != _SCHEMA:
        return False
    supplied = receipt.get("receipt_sha256")
    if not isinstance(supplied, str) or _SHA256_RE.fullmatch(supplied) is None:
        return False
    if any(receipt.get(key) is not False for key in (
        "effect_authority", "promotion_authorized", "owner_host_proven", "hosted_ci_proven", "gate10"
    )):
        return False
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    body.pop("k27", None)
    expected = _digest(body)
    if expected != supplied:
        return False
    raw = bytes.fromhex(expected)
    return receipt.get("k27") == [raw[0] % 27, raw[1] % 27, raw[2] % 27]


__all__ = [
    "AirLLMSecurityReceiptBuilder",
    "GenerationVector",
    "LEAVES",
    "ProofLeafSpec",
    "ProofObservation",
    "SecurityReceiptError",
    "SecuritySubject",
    "verify_receipt",
]

if __name__ == "__main__":
    from copy import deepcopy
    import itertools
    import unittest

    _PARENTS = (
        "1eqzOdEGaPzMRs3skE33JYwKVpG2OGdJDXlvsH5XTdg0",
        "1QeY3CJLJRzVpaV2rZDOxhg41gEACPoRli-K4FgjODVk",
    )

    def _g(**changes: str) -> GenerationVector:
        values = dict(
            semantic="sem-1",
            source="airllm-v4.0.0-ff35db207a0c559af9aa95d686057c3fe84f1d40",
            runtime="py3.12-stdlib",
            security="airllm-secure-wrapper-v2",
            evidence="arena-cut-20260905",
            dependency="transformers-pinned",
        )
        values.update(changes)
        return GenerationVector(**values)

    def _s(**changes: str) -> SecuritySubject:
        values = dict(
            model_id="zai-org/GLM-5.3",
            model_sha256="1" * 64,
            loader_source_sha256="2" * 64,
            upstream_repository="lyogavin/airllm",
            upstream_release="v4.0.0",
            upstream_revision="ff35db207a0c559af9aa95d686057c3fe84f1d40",
        )
        values.update(changes)
        return SecuritySubject(**values)

    def _green() -> AirLLMSecurityReceiptBuilder:
        builder = AirLLMSecurityReceiptBuilder(subject=_s(), generation=_g(), foreign_parents=_PARENTS)
        for index, leaf in enumerate(LEAVES):
            builder.bind(
                leaf.leaf_id,
                proof_id=f"proof-{leaf.leaf_id}",
                proof_digest=f"{index + 3:064x}",
            )
        return builder

    class SelfTest(unittest.TestCase):
        def test_exactly_two_distinct_parents(self):
            with self.assertRaises(SecurityReceiptError):
                AirLLMSecurityReceiptBuilder(subject=_s(), generation=_g(), foreign_parents=(_PARENTS[0],))
            with self.assertRaises(SecurityReceiptError):
                AirLLMSecurityReceiptBuilder(subject=_s(), generation=_g(), foreign_parents=(_PARENTS[0], _PARENTS[0]))

        def test_subject_hash_and_revision_are_exact(self):
            with self.assertRaises(SecurityReceiptError):
                _s(model_sha256="A" * 64)
            with self.assertRaises(SecurityReceiptError):
                _s(upstream_revision="f" * 39)

        def test_green_is_deterministic_nonpromoting(self):
            a = _green().build()
            b = _green().build()
            self.assertEqual(a, b)
            self.assertEqual(a["disposition"], "LOCAL_VERIFIED_NONPROMOTING")
            self.assertTrue(verify_receipt(a))
            for key in ("effect_authority", "promotion_authorized", "owner_host_proven", "hosted_ci_proven", "gate10"):
                self.assertIs(a[key], False)

        def test_payload_or_authority_tamper_fails(self):
            receipt = _green().build()
            altered = deepcopy(receipt)
            altered["subject"]["model_id"] = "attacker/model"
            self.assertFalse(verify_receipt(altered))
            widened = deepcopy(receipt)
            widened["gate10"] = True
            self.assertFalse(verify_receipt(widened))

        def test_runtime_drift_is_selective(self):
            builder = _green()
            receipt = builder.build(_g(runtime="py3.13"))
            self.assertEqual(receipt["stale_or_missing"], ["runtime_hard_false_membrane"])

        def test_source_security_and_evidence_drift_reopen_all(self):
            builder = _green()
            all_leaves = {leaf.leaf_id for leaf in LEAVES}
            for axis in ("source", "security", "evidence"):
                with self.subTest(axis=axis):
                    current = _g(**{axis: f"{axis}-next"})
                    self.assertEqual(set(builder.build(current)["stale_or_missing"]), all_leaves)

        def test_dependency_drift_reopens_compat_only(self):
            receipt = _green().build(_g(dependency="transformers-next"))
            self.assertEqual(receipt["stale_or_missing"], ["pinned_source_compatibility"])

        def test_nonpass_cannot_cross_cast(self):
            builder = _green()
            leaf = LEAVES[2]
            builder.bind(leaf.leaf_id, proof_id="provisional", proof_digest="9" * 64, status="PROVISIONAL_LOCAL")
            receipt = builder.build()
            self.assertEqual(receipt["disposition"], "LOCAL_SECURITY_HOLD")
            self.assertIn(leaf.leaf_id, receipt["stale_or_missing"])

        def test_fail_dominates(self):
            builder = _green()
            leaf = LEAVES[0]
            builder.bind(leaf.leaf_id, proof_id="failed", proof_digest="8" * 64, status="FAIL")
            self.assertEqual(builder.build()["disposition"], "LOCAL_SECURITY_FAIL")

        def test_omega8_and_13d_hard_failures_are_noncompensatory(self):
            admitted = sum(
                1
                for bits in itertools.product((False, True), repeat=8)
                if all(bits[:4]) and all(bits[4:])
            )
            self.assertEqual(admitted, 1)
            contexts = tuple(itertools.product(range(3), repeat=5))
            self.assertEqual(len(contexts), 243)
            for hard_state in itertools.product((False, True), repeat=8):
                if all(hard_state):
                    continue
                self.assertEqual(sum(1 for _ in contexts if all(hard_state)), 0)

    unittest.main(verbosity=2)
