from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
import json
from typing import Callable

SCHEMA = "AURA-PROJECT006-CANONICAL-CONSUMER-ADMISSION-CURRENTNESS-v1"
D0 = "D0_NONPROMOTING"
EXPECTED_REPROOF_SEMANTICS = "HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1"

try:
    from tools.arena.effect_return_atomicity import ProviderActionCurrentness  # type: ignore
except Exception:  # local exact-source proof fallback only
    @dataclass(frozen=True)
    class ProviderActionCurrentness:
        source_root: str
        authorization_root: str
        consumer_admission_root: str
        proof_semantics_id: str
        consumer_generation: int
        source_owner_id: str
        authorization_owner_id: str
        observer_id: str
        effect_authority: bool = False
        gate10: bool = False

        @property
        def identity_root(self) -> str:
            return digest({
                "schema": "AURA-EFFECT-RETURN-ATOMICITY-CAPSULE-v2",
                "kind": "provider_action_currentness",
                "source_root": self.source_root,
                "authorization_root": self.authorization_root,
                "consumer_admission_root": self.consumer_admission_root,
                "proof_semantics_id": self.proof_semantics_id,
                "consumer_generation": self.consumer_generation,
                "source_owner_id": self.source_owner_id,
                "authorization_owner_id": self.authorization_owner_id,
                "observer_id": self.observer_id,
                "effect_authority": False,
                "gate10": False,
            })


def digest(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(body.encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError(f"{field} required")
    return value


def _nn(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be nonnegative exact int")
    return value


class AdmissionDisposition(str, Enum):
    BIND_TECC_CONSUMER_D0 = "BIND_TECC_CONSUMER_D0"


@dataclass(frozen=True)
class CanonicalConsumerAdmission:
    command_id: str
    intent_root: str
    contract_root: str
    source_root: str
    authorization_root: str
    consumer_generation: int
    currentness_root: str
    verifier_instance: str
    producer_lineage_root: str
    observer_lineage_root: str
    observer_receipt_root: str
    proof_semantics_id: str
    source_owner_id: str
    authorization_owner_id: str
    observer_id: str
    issued_at: int
    expires_at: int
    disposition: AdmissionDisposition
    mac: str
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for name in ("command_id", "verifier_instance", "proof_semantics_id", "source_owner_id", "authorization_owner_id", "observer_id"):
            _id(getattr(self, name), name)
        for name in (
            "intent_root", "contract_root", "source_root", "authorization_root", "currentness_root",
            "producer_lineage_root", "observer_lineage_root", "observer_receipt_root", "mac",
        ):
            _root(getattr(self, name), name)
        _nn(self.consumer_generation, "consumer_generation")
        _nn(self.issued_at, "issued_at")
        _nn(self.expires_at, "expires_at")
        if self.expires_at < self.issued_at:
            raise ValueError("expires_at before issued_at")
        if not isinstance(self.disposition, AdmissionDisposition):
            raise ValueError("disposition must be AdmissionDisposition")
        if self.observer_id in {self.source_owner_id, self.authorization_owner_id}:
            raise ValueError("OBSERVER_NOT_INDEPENDENT")
        if self.observer_lineage_root == self.producer_lineage_root:
            raise ValueError("OBSERVER_LINEAGE_NOT_INDEPENDENT")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("consumer admission cannot mint effect/Gate10 authority")

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "kind": "canonical_consumer_admission",
            "command_id": self.command_id,
            "intent_root": self.intent_root,
            "contract_root": self.contract_root,
            "source_root": self.source_root,
            "authorization_root": self.authorization_root,
            "consumer_generation": self.consumer_generation,
            "currentness_root": self.currentness_root,
            "verifier_instance": self.verifier_instance,
            "producer_lineage_root": self.producer_lineage_root,
            "observer_lineage_root": self.observer_lineage_root,
            "observer_receipt_root": self.observer_receipt_root,
            "proof_semantics_id": self.proof_semantics_id,
            "source_owner_id": self.source_owner_id,
            "authorization_owner_id": self.authorization_owner_id,
            "observer_id": self.observer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "disposition": self.disposition.value,
            "authority": D0,
            "effect_authority": False,
            "gate10": False,
        }

    @property
    def receipt_root(self) -> str:
        return digest({**self.unsigned_payload(), "mac": self.mac})


def sign_consumer_admission(*, secret: bytes, **kwargs) -> CanonicalConsumerAdmission:
    disposition = kwargs.pop("disposition", AdmissionDisposition.BIND_TECC_CONSUMER_D0)
    if not isinstance(disposition, AdmissionDisposition):
        raise ValueError("disposition must be AdmissionDisposition")
    payload = {
        "schema": SCHEMA,
        "kind": "canonical_consumer_admission",
        **kwargs,
        "disposition": disposition.value,
        "authority": D0,
        "effect_authority": False,
        "gate10": False,
    }
    mac = hmac.new(secret, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(), sha256).hexdigest()
    return CanonicalConsumerAdmission(disposition=disposition, mac=mac, **kwargs)


@dataclass(frozen=True)
class CanonicalConsumerCut:
    consumer_generation: int
    currentness_root: str
    verifier_instance: str
    source_owner_id: str
    authorization_owner_id: str

    def __post_init__(self) -> None:
        _nn(self.consumer_generation, "consumer_generation")
        _root(self.currentness_root, "currentness_root")
        for name in ("verifier_instance", "source_owner_id", "authorization_owner_id"):
            _id(getattr(self, name), name)


AdmissionProvider = Callable[[object, object], CanonicalConsumerAdmission | None]
NowProvider = Callable[[], int]


class CanonicalConsumerAdmissionResolver:
    """Resolve PR899 ProviderActionCurrentness only from a canonical current consumer-admission receipt.

    The resolver is a D0 adapter. Its configured secret/current cut model the rightful upstream
    consumer-admission owner in finite tests; they are not production key-management claims.
    """

    def __init__(self, *, secret: bytes, cut: CanonicalConsumerCut, admission_provider: AdmissionProvider,
                 now_provider: NowProvider):
        if not isinstance(secret, (bytes, bytearray)) or not secret:
            raise ValueError("secret required")
        self.secret = bytes(secret)
        self.cut = cut
        self.admission_provider = admission_provider
        self.now_provider = now_provider

    def _verify(self, admission: CanonicalConsumerAdmission, intent: object, contract: object) -> bool:
        now = self.now_provider()
        _nn(now, "now")
        expected_mac = hmac.new(
            self.secret,
            json.dumps(admission.unsigned_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(),
            sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_mac, admission.mac):
            return False
        if admission.disposition is not AdmissionDisposition.BIND_TECC_CONSUMER_D0:
            return False
        if now < admission.issued_at or now > admission.expires_at:
            return False
        if admission.consumer_generation != self.cut.consumer_generation:
            return False
        if admission.currentness_root != self.cut.currentness_root:
            return False
        if admission.verifier_instance != self.cut.verifier_instance:
            return False
        if admission.source_owner_id != self.cut.source_owner_id or admission.authorization_owner_id != self.cut.authorization_owner_id:
            return False
        if admission.proof_semantics_id != EXPECTED_REPROOF_SEMANTICS:
            return False
        if admission.observer_id in {admission.source_owner_id, admission.authorization_owner_id}:
            return False
        if admission.observer_lineage_root == admission.producer_lineage_root:
            return False
        attrs = {
            "command_id": getattr(intent, "command_id", None),
            "intent_root": getattr(intent, "identity_root", None),
            "contract_root": getattr(contract, "contract_root", None),
            "source_root": getattr(intent, "source_root", None),
            "authorization_root": getattr(intent, "tecc_authorization_root", None),
        }
        return all(getattr(admission, name) == value for name, value in attrs.items())

    def __call__(self, intent: object, contract: object) -> ProviderActionCurrentness | None:
        try:
            admission = self.admission_provider(intent, contract)
        except Exception:
            return None
        if not isinstance(admission, CanonicalConsumerAdmission):
            return None
        try:
            if not self._verify(admission, intent, contract):
                return None
            return ProviderActionCurrentness(
                source_root=admission.source_root,
                authorization_root=admission.authorization_root,
                consumer_admission_root=admission.receipt_root,
                proof_semantics_id=admission.proof_semantics_id,
                consumer_generation=admission.consumer_generation,
                source_owner_id=admission.source_owner_id,
                authorization_owner_id=admission.authorization_owner_id,
                observer_id=admission.observer_id,
                effect_authority=False,
                gate10=False,
            )
        except Exception:
            return None


def k27_reopen_coordinate(receipt_root: str) -> tuple[int, int, int]:
    """L0 retrieval/reopen coordinate only. Never identity/currentness/authority."""
    root = _root(receipt_root, "receipt_root")
    raw = bytes.fromhex(root)
    return raw[0] % 27, raw[1] % 27, raw[2] % 27


def build_canonical_effect_attempt_journal(path, *, secret: bytes, cut: CanonicalConsumerCut,
                                           admission_provider: AdmissionProvider, now_provider: NowProvider):
    """Owner-adoption seam: construct the existing PR899 journal with canonical consumer admission.

    This function creates no new journal/trust owner; it injects the canonical resolver into the
    current EffectAttemptJournal hook. Raw journal construction remains a generic/noncanonical path.
    """
    from tools.project006.effect_attempt_recovery import EffectAttemptJournal  # type: ignore
    resolver = CanonicalConsumerAdmissionResolver(
        secret=secret, cut=cut, admission_provider=admission_provider, now_provider=now_provider
    )
    return EffectAttemptJournal(path, currentness_resolver=resolver)
