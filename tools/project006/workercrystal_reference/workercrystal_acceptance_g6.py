from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence


G5_ACCEPTED_RESULT_IDENTITY_SCHEMA = "PROJECT006_LC_ACCEPTED_RESULT_IDENTITY_G5"
G5_CANONICAL_PROFILE = "PROJECT006_LC_G5_CANONICAL_V1"
G6_BINDING_SCHEMA = "PROJECT006_LC_ATTEMPT_ACCEPTED_RESULT_BINDING_G6"
G6_CANONICAL_PROFILE = "PROJECT006_LC_G6_CANONICAL_V1"
G6_OPERATION_SCHEMA = "PROJECT006_LC_ACCEPTANCE_OPERATION_G6"

G5_ACCEPTED_RESULT_DOMAIN = "AURA::PROJECT006::LANE-C::ACCEPTED-RESULT::G5"
G6_BINDING_DOMAIN = "AURA::PROJECT006::LANE-C::ATTEMPT-ACCEPTED-RESULT-BINDING::G6"
G6_OPERATION_DOMAIN = "AURA::PROJECT006::LANE-C::ACCEPTANCE-OPERATION::G6"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContractViolation(ValueError):
    """Fail-closed validation error for the Project006 Lane-C G6 reference."""


def _nfc(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ContractViolation(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized:
        raise ContractViolation(f"{field} must be non-empty")
    return normalized


def _digest(value: str, field: str) -> str:
    normalized = _nfc(value, field)
    if not _HEX64.fullmatch(normalized):
        raise ContractViolation(f"{field} must be lowercase 64-hex SHA-256 syntax")
    return normalized


def _generation(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractViolation(f"{field} must be a non-negative integer")
    return value


def _normalize_json(value: Any, field: str = "value") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, float):
        raise ContractViolation(f"{field} contains unsupported JSON value")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _generation(value, field)
    if isinstance(value, list):
        return [_normalize_json(item, f"{field}[]") for item in value]
    if isinstance(value, tuple):
        return [_normalize_json(item, f"{field}[]") for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _nfc(key, f"{field}.key")
            if normalized_key in normalized:
                raise ContractViolation(f"{field} has duplicate canonical key")
            normalized[normalized_key] = _normalize_json(item, f"{field}.{normalized_key}")
        return normalized
    raise ContractViolation(f"{field} contains unsupported type {type(value).__name__}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return deterministic JCS-compatible bytes for this schema's type domain.

    Contract objects use fixed ASCII object keys, NFC strings, non-negative
    integers, booleans, arrays and objects. Floats/null are rejected so the
    reference cannot introduce an unreviewed numeric representation choice.
    """
    normalized = _normalize_json(value)
    text = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def _hash_domain(domain: str, body: Mapping[str, Any]) -> str:
    if "domain_separator" in body:
        raise ContractViolation("body may not supply domain_separator")
    protected = {"domain_separator": domain, **dict(body)}
    return hashlib.sha256(canonical_json_bytes(protected)).hexdigest()


def canonical_string_set(values: Iterable[str], field: str) -> tuple[str, ...]:
    normalized = [_nfc(value, field) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ContractViolation(f"{field} contains duplicate canonical members")
    return tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))


@dataclass(frozen=True)
class ContributionBinding:
    provider_attempt_id: str
    dispatch_receipt_id: str
    result_or_contribution_digest: str
    result_binding_receipt_identity: str

    def protected_body(self) -> dict[str, Any]:
        return {
            "provider_attempt_id": _nfc(self.provider_attempt_id, "provider_attempt_id"),
            "dispatch_receipt_id": _nfc(self.dispatch_receipt_id, "dispatch_receipt_id"),
            "result_or_contribution_digest": _digest(
                self.result_or_contribution_digest, "result_or_contribution_digest"
            ),
            "result_binding_receipt_identity": _digest(
                self.result_binding_receipt_identity, "result_binding_receipt_identity"
            ),
        }


def canonical_contribution_set(
    values: Iterable[ContributionBinding],
) -> tuple[dict[str, Any], ...]:
    bodies = [value.protected_body() for value in values]
    encoded = [canonical_json_bytes(body) for body in bodies]
    if len(set(encoded)) != len(encoded):
        raise ContractViolation("contributing_attempt_bindings contains duplicate canonical members")
    return tuple(body for _, body in sorted(zip(encoded, bodies), key=lambda pair: pair[0]))


@dataclass(frozen=True)
class AcceptanceFacts:
    result_digest: str
    capsule_id: str
    capsule_digest: str
    capsule_incarnation: int
    accepted_lease_id: str
    lease_generation: int
    fencing_token_digest: str
    source_currentness_digest: str
    authority_effect_ceiling_digest: str
    verifying_receipt_identities: Sequence[str]
    required_contribution_profile_identity: str
    required_contribution_profile_generation: int
    required_attempt_set_identity: str
    external_contribution_required: bool
    contributing_attempt_bindings: Sequence[ContributionBinding]
    accepted_state_generation: int

    def accepted_result_body(self) -> dict[str, Any]:
        if not isinstance(self.external_contribution_required, bool):
            raise ContractViolation("external_contribution_required must be boolean")
        return {
            "identity_schema": G5_ACCEPTED_RESULT_IDENTITY_SCHEMA,
            "canonical_profile_id": G5_CANONICAL_PROFILE,
            "result_digest": _digest(self.result_digest, "result_digest"),
            "capsule_id": _nfc(self.capsule_id, "capsule_id"),
            "capsule_digest": _digest(self.capsule_digest, "capsule_digest"),
            "capsule_incarnation": _generation(self.capsule_incarnation, "capsule_incarnation"),
            "accepted_lease_id": _nfc(self.accepted_lease_id, "accepted_lease_id"),
            "lease_generation": _generation(self.lease_generation, "lease_generation"),
            "fencing_token_digest": _digest(self.fencing_token_digest, "fencing_token_digest"),
            "source_currentness_digest": _digest(
                self.source_currentness_digest, "source_currentness_digest"
            ),
            "authority_effect_ceiling_digest": _digest(
                self.authority_effect_ceiling_digest, "authority_effect_ceiling_digest"
            ),
            "verifying_receipt_identities": list(
                canonical_string_set(
                    (
                        _digest(value, "verifying_receipt_identity")
                        for value in self.verifying_receipt_identities
                    ),
                    "verifying_receipt_identities",
                )
            ),
            "required_contribution_profile_identity": _digest(
                self.required_contribution_profile_identity,
                "required_contribution_profile_identity",
            ),
            "required_contribution_profile_generation": _generation(
                self.required_contribution_profile_generation,
                "required_contribution_profile_generation",
            ),
            "required_attempt_set_identity": _digest(
                self.required_attempt_set_identity, "required_attempt_set_identity"
            ),
            "external_contribution_required": self.external_contribution_required,
            "contributing_attempt_bindings": list(
                canonical_contribution_set(self.contributing_attempt_bindings)
            ),
            "accepted_state_generation": _generation(
                self.accepted_state_generation, "accepted_state_generation"
            ),
        }

    def accepted_result_identity(self) -> str:
        return _hash_domain(G5_ACCEPTED_RESULT_DOMAIN, self.accepted_result_body())


@dataclass(frozen=True)
class AttemptTerminalFacts:
    contribution: ContributionBinding
    terminal_reconciliation_generation: int

    def relation_key(self) -> bytes:
        return canonical_json_bytes(self.contribution.protected_body())


_G6_BINDING_BODY_KEYS = frozenset(
    {
        "binding_schema",
        "canonical_profile_id",
        "provider_attempt_id",
        "dispatch_receipt_id",
        "attempt_result_or_contribution_digest",
        "result_binding_receipt_identity",
        "accepted_result_identity",
        "accepted_result_digest",
        "terminal_reconciliation_generation",
        "accepted_state_generation",
        "capsule_id",
        "capsule_digest",
        "capsule_incarnation",
        "lease_id",
        "lease_generation",
        "fencing_token_digest",
    }
)
_G6_BINDING_RECORD_KEYS = _G6_BINDING_BODY_KEYS | {"binding_identity"}


def _validate_exact_keys(mapping: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = frozenset(mapping.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractViolation(f"{label} schema mismatch: missing={missing}, extra={extra}")


def derive_g6_binding_identity_from_body(body: Mapping[str, Any]) -> str:
    _validate_exact_keys(body, _G6_BINDING_BODY_KEYS, "G6 binding body")
    if body["binding_schema"] != G6_BINDING_SCHEMA:
        raise ContractViolation("unsupported G6 binding schema")
    if body["canonical_profile_id"] != G6_CANONICAL_PROFILE:
        raise ContractViolation("unsupported G6 canonical profile")
    _nfc(body["provider_attempt_id"], "provider_attempt_id")
    _nfc(body["dispatch_receipt_id"], "dispatch_receipt_id")
    _digest(body["attempt_result_or_contribution_digest"], "attempt_result_or_contribution_digest")
    _digest(body["result_binding_receipt_identity"], "result_binding_receipt_identity")
    _digest(body["accepted_result_identity"], "accepted_result_identity")
    _digest(body["accepted_result_digest"], "accepted_result_digest")
    _generation(body["terminal_reconciliation_generation"], "terminal_reconciliation_generation")
    _generation(body["accepted_state_generation"], "accepted_state_generation")
    _nfc(body["capsule_id"], "capsule_id")
    _digest(body["capsule_digest"], "capsule_digest")
    _generation(body["capsule_incarnation"], "capsule_incarnation")
    _nfc(body["lease_id"], "lease_id")
    _generation(body["lease_generation"], "lease_generation")
    _digest(body["fencing_token_digest"], "fencing_token_digest")
    return _hash_domain(G6_BINDING_DOMAIN, body)


def build_g6_binding(
    facts: AcceptanceFacts,
    terminal: AttemptTerminalFacts,
    accepted_result_identity: str,
) -> dict[str, Any]:
    expected_result_identity = facts.accepted_result_identity()
    supplied_result_identity = _digest(accepted_result_identity, "accepted_result_identity")
    if supplied_result_identity != expected_result_identity:
        raise ContractViolation("accepted_result_identity does not match AcceptanceFacts")
    contribution = terminal.contribution.protected_body()
    body: dict[str, Any] = {
        "binding_schema": G6_BINDING_SCHEMA,
        "canonical_profile_id": G6_CANONICAL_PROFILE,
        "provider_attempt_id": contribution["provider_attempt_id"],
        "dispatch_receipt_id": contribution["dispatch_receipt_id"],
        "attempt_result_or_contribution_digest": contribution["result_or_contribution_digest"],
        "result_binding_receipt_identity": contribution["result_binding_receipt_identity"],
        "accepted_result_identity": expected_result_identity,
        "accepted_result_digest": _digest(facts.result_digest, "result_digest"),
        "terminal_reconciliation_generation": _generation(
            terminal.terminal_reconciliation_generation,
            "terminal_reconciliation_generation",
        ),
        "accepted_state_generation": _generation(
            facts.accepted_state_generation, "accepted_state_generation"
        ),
        "capsule_id": _nfc(facts.capsule_id, "capsule_id"),
        "capsule_digest": _digest(facts.capsule_digest, "capsule_digest"),
        "capsule_incarnation": _generation(facts.capsule_incarnation, "capsule_incarnation"),
        "lease_id": _nfc(facts.accepted_lease_id, "accepted_lease_id"),
        "lease_generation": _generation(facts.lease_generation, "lease_generation"),
        "fencing_token_digest": _digest(facts.fencing_token_digest, "fencing_token_digest"),
    }
    return {**body, "binding_identity": derive_g6_binding_identity_from_body(body)}


def validate_g6_binding_record(record: Mapping[str, Any]) -> str:
    _validate_exact_keys(record, _G6_BINDING_RECORD_KEYS, "G6 binding record")
    body = {key: record[key] for key in _G6_BINDING_BODY_KEYS}
    derived = derive_g6_binding_identity_from_body(body)
    stored = _digest(record["binding_identity"], "binding_identity")
    if derived != stored:
        raise ContractViolation("G6 binding_identity mismatch")
    return derived


_G6_OPERATION_BODY_KEYS = frozenset(
    {
        "operation_schema",
        "canonical_profile_id",
        "operation_kind",
        "accepted_result_identity",
        "accepted_result_digest",
        "accepted_state_generation",
        "required_attempt_set_identity",
        "attempt_accepted_result_binding_identities",
        "capsule_id",
        "capsule_digest",
        "capsule_incarnation",
        "lease_id",
        "lease_generation",
        "fencing_token_digest",
        "source_currentness_digest",
        "authority_effect_ceiling_digest",
        "lifecycle_after",
    }
)


def canonical_binding_identity_set(values: Iterable[str]) -> tuple[str, ...]:
    normalized = [_digest(value, "binding_identity") for value in values]
    if len(set(normalized)) != len(normalized):
        raise ContractViolation("attempt_accepted_result_binding_identities contains duplicates")
    return tuple(sorted(normalized, key=lambda value: value.encode("utf-8")))


def build_g6_operation_body(
    facts: AcceptanceFacts,
    accepted_result_identity: str,
    binding_identities: Iterable[str],
) -> dict[str, Any]:
    expected_result_identity = facts.accepted_result_identity()
    supplied_result_identity = _digest(accepted_result_identity, "accepted_result_identity")
    if supplied_result_identity != expected_result_identity:
        raise ContractViolation("accepted_result_identity does not match AcceptanceFacts")
    return {
        "operation_schema": G6_OPERATION_SCHEMA,
        "canonical_profile_id": G6_CANONICAL_PROFILE,
        "operation_kind": "ACCEPT_RESULT",
        "accepted_result_identity": expected_result_identity,
        "accepted_result_digest": _digest(facts.result_digest, "result_digest"),
        "accepted_state_generation": _generation(
            facts.accepted_state_generation, "accepted_state_generation"
        ),
        "required_attempt_set_identity": _digest(
            facts.required_attempt_set_identity, "required_attempt_set_identity"
        ),
        "attempt_accepted_result_binding_identities": list(
            canonical_binding_identity_set(binding_identities)
        ),
        "capsule_id": _nfc(facts.capsule_id, "capsule_id"),
        "capsule_digest": _digest(facts.capsule_digest, "capsule_digest"),
        "capsule_incarnation": _generation(facts.capsule_incarnation, "capsule_incarnation"),
        "lease_id": _nfc(facts.accepted_lease_id, "accepted_lease_id"),
        "lease_generation": _generation(facts.lease_generation, "lease_generation"),
        "fencing_token_digest": _digest(facts.fencing_token_digest, "fencing_token_digest"),
        "source_currentness_digest": _digest(
            facts.source_currentness_digest, "source_currentness_digest"
        ),
        "authority_effect_ceiling_digest": _digest(
            facts.authority_effect_ceiling_digest, "authority_effect_ceiling_digest"
        ),
        "lifecycle_after": "COMPLETE",
    }


def derive_g6_operation_digest_from_body(body: Mapping[str, Any]) -> str:
    _validate_exact_keys(body, _G6_OPERATION_BODY_KEYS, "G6 operation body")
    if body["operation_schema"] != G6_OPERATION_SCHEMA:
        raise ContractViolation("unsupported G6 operation schema")
    if body["canonical_profile_id"] != G6_CANONICAL_PROFILE:
        raise ContractViolation("unsupported G6 canonical profile")
    if body["operation_kind"] != "ACCEPT_RESULT":
        raise ContractViolation("unsupported operation_kind")
    if body["lifecycle_after"] != "COMPLETE":
        raise ContractViolation("lifecycle_after must be COMPLETE")
    _digest(body["accepted_result_identity"], "accepted_result_identity")
    _digest(body["accepted_result_digest"], "accepted_result_digest")
    _generation(body["accepted_state_generation"], "accepted_state_generation")
    _digest(body["required_attempt_set_identity"], "required_attempt_set_identity")
    _nfc(body["capsule_id"], "capsule_id")
    _digest(body["capsule_digest"], "capsule_digest")
    _generation(body["capsule_incarnation"], "capsule_incarnation")
    _nfc(body["lease_id"], "lease_id")
    _generation(body["lease_generation"], "lease_generation")
    _digest(body["fencing_token_digest"], "fencing_token_digest")
    _digest(body["source_currentness_digest"], "source_currentness_digest")
    _digest(body["authority_effect_ceiling_digest"], "authority_effect_ceiling_digest")
    expected_set = canonical_binding_identity_set(
        body["attempt_accepted_result_binding_identities"]
    )
    if list(expected_set) != list(body["attempt_accepted_result_binding_identities"]):
        raise ContractViolation("G6 operation binding set is not in canonical order")
    return _hash_domain(G6_OPERATION_DOMAIN, body)


@dataclass(frozen=True)
class AcceptanceBundle:
    accepted_result_identity: str
    bindings: tuple[dict[str, Any], ...]
    binding_identities: tuple[str, ...]
    operation_body: dict[str, Any]
    acceptance_operation_digest: str


def build_acceptance_bundle(
    facts: AcceptanceFacts,
    terminal_attempts: Sequence[AttemptTerminalFacts],
) -> AcceptanceBundle:
    """Construct the G6 identity graph in the reviewed one-way order."""
    accepted_result_identity = facts.accepted_result_identity()

    required = canonical_contribution_set(facts.contributing_attempt_bindings)
    required_keys = {canonical_json_bytes(body) for body in required}
    terminals_by_key: dict[bytes, AttemptTerminalFacts] = {}
    for terminal in terminal_attempts:
        key = terminal.relation_key()
        if key in terminals_by_key:
            raise ContractViolation("terminal_attempts contains duplicate required relation")
        terminals_by_key[key] = terminal

    if set(terminals_by_key) != required_keys:
        raise ContractViolation("terminal_attempts do not exactly equal required contributing attempt set")
    if facts.external_contribution_required and not required:
        raise ContractViolation("external contribution is required but required attempt set is empty")
    if not facts.external_contribution_required and required:
        raise ContractViolation("external contribution is false but required attempt set is non-empty")

    bindings = [
        build_g6_binding(facts, terminals_by_key[key], accepted_result_identity)
        for key in sorted(terminals_by_key)
    ]
    binding_identities = canonical_binding_identity_set(
        binding["binding_identity"] for binding in bindings
    )
    operation_body = build_g6_operation_body(
        facts, accepted_result_identity, binding_identities
    )
    operation_digest = derive_g6_operation_digest_from_body(operation_body)
    return AcceptanceBundle(
        accepted_result_identity=accepted_result_identity,
        bindings=tuple(bindings),
        binding_identities=binding_identities,
        operation_body=operation_body,
        acceptance_operation_digest=operation_digest,
    )


@dataclass(frozen=True)
class StoredAcceptance:
    accepted_result_identity: str
    attempt_accepted_result_binding_identities: Sequence[str]
    bindings: Sequence[Mapping[str, Any]]
    operation_body: Mapping[str, Any]
    acceptance_operation_digest: str
    lifecycle: str = "COMPLETE"


def verify_restart(
    facts: AcceptanceFacts,
    terminal_attempts: Sequence[AttemptTerminalFacts],
    stored: StoredAcceptance,
) -> AcceptanceBundle:
    """Recompute in G6 order and fail closed on any stored-state divergence.

    The stored operation digest is intentionally not consumed until all binding
    identities and the operation body have already been independently rebuilt.
    """
    if stored.lifecycle != "COMPLETE":
        raise ContractViolation("stored lifecycle is not COMPLETE")

    expected = build_acceptance_bundle(facts, terminal_attempts)

    stored_result_identity = _digest(
        stored.accepted_result_identity, "stored accepted_result_identity"
    )
    if stored_result_identity != expected.accepted_result_identity:
        raise ContractViolation("stored accepted_result_identity mismatch")

    stored_ids = canonical_binding_identity_set(
        stored.attempt_accepted_result_binding_identities
    )
    if tuple(stored.attempt_accepted_result_binding_identities) != stored_ids:
        raise ContractViolation("stored binding identity set is not canonical")
    if stored_ids != expected.binding_identities:
        raise ContractViolation("stored binding identity set mismatch")

    by_identity: dict[str, Mapping[str, Any]] = {}
    for record in stored.bindings:
        identity = validate_g6_binding_record(record)
        if identity in by_identity:
            raise ContractViolation("stored bindings contain duplicate identity")
        by_identity[identity] = record
    if set(by_identity) != set(expected.binding_identities):
        raise ContractViolation("stored binding records do not exactly match required G6 bindings")
    for expected_record in expected.bindings:
        stored_record = by_identity[expected_record["binding_identity"]]
        if canonical_json_bytes(stored_record) != canonical_json_bytes(expected_record):
            raise ContractViolation("stored G6 binding body mismatch")

    # Only after binding reconstruction do we validate/compare the operation.
    operation_body = dict(stored.operation_body)
    derived_stored_operation_digest = derive_g6_operation_digest_from_body(operation_body)
    if canonical_json_bytes(operation_body) != canonical_json_bytes(expected.operation_body):
        raise ContractViolation("stored G6 operation body mismatch")
    stored_operation_digest = _digest(
        stored.acceptance_operation_digest, "stored acceptance_operation_digest"
    )
    if derived_stored_operation_digest != stored_operation_digest:
        raise ContractViolation("stored acceptance_operation_digest does not match stored body")
    if stored_operation_digest != expected.acceptance_operation_digest:
        raise ContractViolation("stored acceptance_operation_digest mismatch")
    return expected
