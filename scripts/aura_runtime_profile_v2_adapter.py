#!/usr/bin/env python3
"""Evidence-only V2 adapter over Aura's canonical V1 Runtime Harness."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aura_bilateral_intent_compiler import VERSION as CONFIRMATION_PACKET_VERSION
from aura_event_contracts import stable_digest
from aura_intent_refinement import IntentConfirmationReceipt
from aura_unified_memory_continuity import (
    AuthorityEnvelope,
    IntentPacket,
    SemanticDefinition,
    SemanticLedger,
)

try:
    from scripts import aura_runtime_refactor_harness as _v1
except ModuleNotFoundError:
    import aura_runtime_refactor_harness as _v1  # type: ignore[no-redef]

VERSION = "AURA_RUNTIME_BILATERAL_PROOF_V1"
PROFILE_VERSION = "AURA_RUNTIME_PROFILE_V2"
MAX_ASSERTIONS = 256
MAX_SCENARIOS = 64
MAX_TRACES = 64
MAX_PATHS = 256
MAX_JSON_BYTES = 8 * 1024 * 1024
GROUPS = (
    "positive_assertions",
    "negative_assertions",
    "preservation_assertions",
    "fault_injections",
)
FALSE_AUTHORITIES = (
    "automatic_fix",
    "automatic_commit",
    "automatic_push",
    "automatic_pull_request",
    "automatic_merge",
    "production_mutation",
    "professional_authority",
    "physical_work_authority",
    "learning_promotion",
)
SPECIAL_TRACES = frozenset(
    {
        "runtime_harness_receipt.json",
        "readiness.receipt.json",
        "server-output.receipt.json",
        "server-termination.receipt.json",
    }
)
DIGEST = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
JSON_PATH = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")
OPERATORS = frozenset({"equals", "not_equals", "truthy", "falsy", "contains", "nonempty"})
NO_POST_CONFIRMATION_REVISION = "NOT_CREATED_NO_POST_CONFIRMATION_DRIFT"
AUTHORITY_CONTRACT = {
    **_v1.AUTHORITY_CONTRACT,
    "production_mutation": False,
    "professional_authority": False,
    "physical_work_authority": False,
    "learning_promotion": False,
    "bilateral_runtime_evidence_authority": False,
}


class BilateralRuntimeProfileError(_v1.RuntimeHarnessError):
    """A V2 contract or proof crossed a deterministic boundary."""


def _json_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode(), digest_size=32).hexdigest()


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise BilateralRuntimeProfileError(f"{label} is invalid")
    return value


def _hex(value: Any, label: str, pattern: re.Pattern[str] = DIGEST) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise BilateralRuntimeProfileError(f"{label} has invalid identity")
    return value


def _path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BilateralRuntimeProfileError(f"{label} is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise BilateralRuntimeProfileError(f"{label} escapes its boundary")
    return pure.as_posix()


def _read_json(path: Path, label: str, maximum: int) -> Any:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise BilateralRuntimeProfileError(f"{label} is missing, unsafe, or oversized")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BilateralRuntimeProfileError(f"{label} is not canonical UTF-8 JSON: {exc}") from exc


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BilateralRuntimeProfileError(f"repository identity is unavailable: {exc}") from exc
    if result.returncode:
        raise BilateralRuntimeProfileError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _repo_identity(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        raise BilateralRuntimeProfileError("V2 runtime proof requires a Git checkout")
    status = [item for item in _git(root, "status", "--porcelain=v1", "-z").split("\x00") if item]
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "source_tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "branch": _git(root, "branch", "--show-current"),
        "status": status[:10_000],
        "clean": not status,
    }


def _contract(value: Any) -> dict[str, str]:
    keys = {"confirmation_packet_version", "intent_revision_status"}
    if not isinstance(value, Mapping) or set(value) != keys:
        raise BilateralRuntimeProfileError("intent_contract must be complete and exact")
    if value["confirmation_packet_version"] != CONFIRMATION_PACKET_VERSION:
        raise BilateralRuntimeProfileError("intent_contract must require the canonical bilateral confirmation packet")
    if value["intent_revision_status"] != NO_POST_CONFIRMATION_REVISION:
        raise BilateralRuntimeProfileError("B9 requires the canonical no-post-confirmation-drift revision status")
    return {
        "confirmation_packet_version": CONFIRMATION_PACKET_VERSION,
        "intent_revision_status": NO_POST_CONFIRMATION_REVISION,
    }


def _assertions(raw: Any, group: str, traces: set[str], seen: set[str]) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_ASSERTIONS:
        raise BilateralRuntimeProfileError(f"{group} must be a non-empty bounded array")
    rows = []
    allowed = {"assertion_id", "artifact", "json_path", "operator", "expected"}
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) - allowed:
            raise BilateralRuntimeProfileError(f"{group}[{index}] is invalid")
        assertion_id = _id(item.get("assertion_id"), f"{group}[{index}].assertion_id")
        if assertion_id in seen:
            raise BilateralRuntimeProfileError(f"duplicate assertion_id: {assertion_id}")
        seen.add(assertion_id)
        artifact = _path(item.get("artifact"), f"{group}[{index}].artifact")
        json_path = item.get("json_path")
        operator = item.get("operator", "equals")
        if artifact not in traces:
            raise BilateralRuntimeProfileError(f"{group}[{index}].artifact is not an admitted trace")
        if not isinstance(json_path, str) or not JSON_PATH.fullmatch(json_path):
            raise BilateralRuntimeProfileError(f"{group}[{index}].json_path is invalid")
        if operator not in OPERATORS:
            raise BilateralRuntimeProfileError(f"{group}[{index}].operator is invalid")
        if operator in {"equals", "not_equals", "contains"} and "expected" not in item:
            raise BilateralRuntimeProfileError(f"{group}[{index}] requires expected")
        rows.append(
            {
                "assertion_id": assertion_id,
                "artifact": artifact,
                "json_path": json_path,
                "operator": operator,
                "expected": item.get("expected"),
                "group": group,
            }
        )
    return tuple(rows)


def _requirement_bindings(
    raw: Any,
    assertions: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, tuple[dict[str, Any], ...]]:
    if not isinstance(raw, Mapping) or set(raw) != set(GROUPS):
        raise BilateralRuntimeProfileError("requirement_bindings must cover every assertion group exactly")
    result: dict[str, tuple[dict[str, Any], ...]] = {}
    for group in GROUPS:
        rows = raw[group]
        if not isinstance(rows, list) or not rows or len(rows) > MAX_ASSERTIONS:
            raise BilateralRuntimeProfileError(f"requirement_bindings.{group} must be a non-empty bounded array")
        group_assertions = {str(item["assertion_id"]) for item in assertions[group]}
        seen_requirements: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(rows):
            if not isinstance(item, Mapping) or set(item) != {
                "requirement_digest",
                "assertion_ids",
            }:
                raise BilateralRuntimeProfileError(f"requirement_bindings.{group}[{index}] is invalid")
            requirement_digest = _hex(
                item["requirement_digest"],
                f"requirement_bindings.{group}[{index}].requirement_digest",
            )
            raw_assertion_ids = item["assertion_ids"]
            if (
                not isinstance(raw_assertion_ids, list)
                or not raw_assertion_ids
                or len(raw_assertion_ids) > MAX_ASSERTIONS
            ):
                raise BilateralRuntimeProfileError(
                    f"requirement_bindings.{group}[{index}].assertion_ids must be a non-empty bounded array"
                )
            assertion_ids = tuple(
                _id(value, f"requirement_bindings.{group}[{index}].assertion_ids") for value in raw_assertion_ids
            )
            if (
                requirement_digest in seen_requirements
                or len(set(assertion_ids)) != len(assertion_ids)
                or not set(assertion_ids).issubset(group_assertions)
            ):
                raise BilateralRuntimeProfileError(
                    f"requirement_bindings.{group}[{index}] is duplicated or references the wrong assertion group"
                )
            seen_requirements.add(requirement_digest)
            normalized.append(
                {
                    "requirement_digest": requirement_digest,
                    "assertion_ids": assertion_ids,
                }
            )
        result[group] = tuple(normalized)
    return result


def load_runtime_profile_v2(root: Path, profile_path: str | Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    path = _v1._safe_repo_path(root, str(profile_path), "runtime profile")
    raw = _read_json(path, "runtime profile", _v1.MAX_PROFILE_BYTES)
    if not isinstance(raw, Mapping) or raw.get("version") != PROFILE_VERSION:
        raise BilateralRuntimeProfileError(f"runtime profile version must be {PROFILE_VERSION}")
    allowed_keys = {
        "version",
        "profile_id",
        "objective",
        "runtime_candidate_id",
        "base_profile",
        "intent_contract",
        "allowed_paths",
        "scenarios",
        *GROUPS,
        "requirement_bindings",
        "required_trace_artifacts",
        "repair_policy",
        "independent_verifier",
        "axiom_bindings",
    }
    if set(raw) - allowed_keys:
        raise BilateralRuntimeProfileError("runtime profile contains unknown top-level fields")

    profile_id = _id(raw.get("profile_id"), "profile_id")
    candidate_id = _id(raw.get("runtime_candidate_id"), "runtime_candidate_id")
    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip() or len(objective.encode()) > 2000:
        raise BilateralRuntimeProfileError("objective must be a non-empty bounded string")
    base_path = _path(raw.get("base_profile"), "base_profile")
    base = _v1.load_runtime_profile(root, base_path)
    contract = _contract(raw.get("intent_contract"))

    raw_allowed_paths = raw.get("allowed_paths", [])
    if not isinstance(raw_allowed_paths, list) or not raw_allowed_paths or len(raw_allowed_paths) > MAX_PATHS:
        raise BilateralRuntimeProfileError("allowed_paths must be a non-empty bounded array")
    allowed_paths = tuple(sorted(_path(item, "allowed_paths") for item in raw_allowed_paths))
    if len(set(allowed_paths)) != len(allowed_paths):
        raise BilateralRuntimeProfileError("allowed_paths must be unique and non-empty")
    for item in allowed_paths:
        _v1._safe_repo_path(root, item, "allowed path")

    raw_traces = raw.get("required_trace_artifacts")
    if not isinstance(raw_traces, list) or not raw_traces or len(raw_traces) > MAX_TRACES:
        raise BilateralRuntimeProfileError("required_trace_artifacts must be a non-empty bounded array")
    traces = tuple(_path(item, "required_trace_artifacts") for item in raw_traces)
    admitted = set(base["probe"]["required_artifacts"]) | set(SPECIAL_TRACES)
    if len(set(traces)) != len(traces) or not set(traces).issubset(admitted):
        raise BilateralRuntimeProfileError("required traces are duplicated or not emitted by the V1 run")

    seen: set[str] = set()
    groups = {name: _assertions(raw.get(name), name, set(traces), seen) for name in GROUPS}
    requirement_bindings = _requirement_bindings(
        raw.get("requirement_bindings"),
        groups,
    )
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios or len(scenarios) > MAX_SCENARIOS:
        raise BilateralRuntimeProfileError("scenarios must be a non-empty bounded array")
    scenario_rows, referenced, scenario_ids = [], set(), set()
    for index, item in enumerate(scenarios):
        if not isinstance(item, Mapping) or set(item) != {
            "scenario_id",
            "description",
            "required_assertion_ids",
        }:
            raise BilateralRuntimeProfileError(f"scenarios[{index}] is invalid")
        scenario_id = _id(item["scenario_id"], f"scenarios[{index}].scenario_id")
        raw_required = item["required_assertion_ids"]
        if not isinstance(raw_required, list) or len(raw_required) > MAX_ASSERTIONS:
            raise BilateralRuntimeProfileError(f"scenarios[{index}].required_assertion_ids must be a bounded array")
        required = tuple(_id(value, "required_assertion_ids") for value in raw_required)
        if scenario_id in scenario_ids or not required or not set(required).issubset(seen):
            raise BilateralRuntimeProfileError(f"scenarios[{index}] references invalid assertions")
        scenario_ids.add(scenario_id)
        referenced.update(required)
        scenario_rows.append(
            {
                "scenario_id": scenario_id,
                "description": str(item["description"])[:2000],
                "required_assertion_ids": required,
            }
        )
    if referenced != seen:
        raise BilateralRuntimeProfileError(f"scenarios leave assertions unreferenced: {sorted(seen - referenced)}")

    policy = raw.get("repair_policy")
    required_policy = {*FALSE_AUTHORITIES, "max_attempts", "retry_failed_assertions", "human_review_required"}
    if not isinstance(policy, Mapping) or set(policy) != required_policy:
        raise BilateralRuntimeProfileError("repair_policy must use the exact bounded schema")
    for field in FALSE_AUTHORITIES:
        if policy[field] is not False:
            raise BilateralRuntimeProfileError(f"repair_policy cannot grant {field}")
    if policy["max_attempts"] != 1 or policy["retry_failed_assertions"] is not False:
        raise BilateralRuntimeProfileError("persistent repair is deferred beyond B9")
    if policy["human_review_required"] is not True:
        raise BilateralRuntimeProfileError("repair_policy must require human review")

    verifier = raw.get("independent_verifier")
    if not isinstance(verifier, Mapping) or set(verifier) != {"verifier_id", "source_path", "source_sha256"}:
        raise BilateralRuntimeProfileError("independent_verifier must use the exact schema")
    verifier_id = _id(verifier["verifier_id"], "verifier_id")
    verifier_path = _path(verifier["source_path"], "verifier source")
    verifier_sha = _hex(verifier["source_sha256"], "verifier source_sha256")
    verifier_source = _v1._safe_repo_path(root, verifier_path, "independent verifier source")
    if verifier_id in {profile_id, candidate_id} or _v1._sha256(verifier_source) != verifier_sha:
        raise BilateralRuntimeProfileError("independent verifier identity or source digest mismatch")
    if verifier_path not in allowed_paths:
        raise BilateralRuntimeProfileError("independent verifier source must be included in allowed_paths")
    command_sources: list[Path] = []
    for token in base["probe"]["command"]:
        if not isinstance(token, str) or not token or "{" in token:
            continue
        candidate = (root / token).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file() and not candidate.is_symlink():
            command_sources.append(candidate)
    if command_sources.count(verifier_source) != 1:
        raise BilateralRuntimeProfileError(
            "independent verifier source is not the exact probe command evidence producer"
        )

    axioms = raw.get("axiom_bindings") or list(_v1.AXIOM_BINDINGS)
    if not isinstance(axioms, list) or not axioms or any(not isinstance(item, str) for item in axioms):
        raise BilateralRuntimeProfileError("axiom_bindings must be a non-empty string array")
    return {
        "version": PROFILE_VERSION,
        "profile_id": profile_id,
        "objective": objective.strip(),
        "runtime_candidate_id": candidate_id,
        "profile_path": path.relative_to(root).as_posix(),
        "profile_sha256": _v1._sha256(path),
        "base_profile": base_path,
        "base_profile_id": base["profile_id"],
        "base_profile_sha256": base["profile_sha256"],
        "intent_contract": contract,
        "allowed_paths": allowed_paths,
        "scenarios": tuple(scenario_rows),
        **groups,
        "requirement_bindings": requirement_bindings,
        "required_trace_artifacts": traces,
        "repair_policy": dict(policy),
        "independent_verifier": {
            "verifier_id": verifier_id,
            "source_path": verifier_path,
            "source_sha256": verifier_sha,
        },
        "axiom_bindings": tuple(axioms),
    }


def _external_input_path(root: Path, value: str | Path, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        pass
    else:
        raise BilateralRuntimeProfileError(f"{label} must remain outside the source checkout")
    if not path.is_file() or path.is_symlink():
        raise BilateralRuntimeProfileError(f"{label} is missing or unsafe")
    return path


def _rehydrate_intent(value: Any) -> IntentPacket:
    if not isinstance(value, Mapping):
        raise BilateralRuntimeProfileError("canonical intent packet is missing")
    expected = set(IntentPacket.__dataclass_fields__)
    if set(value) != expected or not isinstance(value.get("authority"), Mapping):
        raise BilateralRuntimeProfileError("canonical intent packet schema is invalid")
    payload = dict(value)
    try:
        payload["authority"] = AuthorityEnvelope(**dict(payload["authority"]))
        for field in (
            "constraints",
            "prohibitions",
            "acceptance_criteria",
            "required_evidence",
        ):
            payload[field] = tuple(payload[field])
        return IntentPacket(**payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise BilateralRuntimeProfileError(f"canonical intent packet identity is invalid: {exc}") from exc


def _rehydrate_ledger(value: Any) -> SemanticLedger:
    if not isinstance(value, Mapping):
        raise BilateralRuntimeProfileError("canonical Semantic Ledger is missing")
    expected = set(SemanticLedger.__dataclass_fields__)
    if set(value) != expected or not isinstance(value.get("definitions"), list):
        raise BilateralRuntimeProfileError("canonical Semantic Ledger schema is invalid")
    payload = dict(value)
    try:
        payload["definitions"] = tuple(
            SemanticDefinition(
                term=item["term"],
                means=tuple(item["means"]),
                does_not_mean=tuple(item["does_not_mean"]),
                source_refs=tuple(item["source_refs"]),
                freshness=item.get("freshness", "CURRENT"),
            )
            for item in payload["definitions"]
        )
        return SemanticLedger(**payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise BilateralRuntimeProfileError(f"canonical Semantic Ledger identity is invalid: {exc}") from exc


def _rehydrate_receipt(value: Any) -> IntentConfirmationReceipt:
    if not isinstance(value, Mapping):
        raise BilateralRuntimeProfileError("canonical confirmation receipt is missing")
    expected = set(IntentConfirmationReceipt.__dataclass_fields__)
    if set(value) != expected:
        raise BilateralRuntimeProfileError("canonical confirmation receipt schema is invalid")
    payload = dict(value)
    try:
        payload["expires_or_stales_on"] = tuple(payload["expires_or_stales_on"])
        receipt = IntentConfirmationReceipt(**payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise BilateralRuntimeProfileError(f"canonical confirmation receipt is invalid: {exc}") from exc
    if not receipt.has_valid_identity():
        raise BilateralRuntimeProfileError("canonical confirmation receipt identity is invalid")
    return receipt


def _confirmed_requirement_digests(values: Any, label: str) -> set[str]:
    if (
        not isinstance(values, list)
        or not values
        or len(values) > MAX_ASSERTIONS
        or any(not isinstance(item, str) or not item.strip() for item in values)
    ):
        raise BilateralRuntimeProfileError(f"{label} must be a non-empty bounded string array")
    return {_json_digest(item) for item in values}


def _validate_requirement_coverage(
    profile: Mapping[str, Any],
    positive_requirements: list[str],
    negative_requirements: list[str],
) -> dict[str, list[dict[str, Any]]]:
    bindings = profile["requirement_bindings"]
    positive = _confirmed_requirement_digests(
        positive_requirements,
        "confirmed positive requirements",
    )
    negative = _confirmed_requirement_digests(
        negative_requirements,
        "confirmed negative requirements",
    )
    bound_positive = {item["requirement_digest"] for item in bindings[GROUPS[0]]}
    bound_negative = {item["requirement_digest"] for group in GROUPS[1:] for item in bindings[group]}
    if bound_positive != positive:
        raise BilateralRuntimeProfileError("runtime profile does not cover the exact confirmed positive requirements")
    if bound_negative != negative:
        raise BilateralRuntimeProfileError("runtime profile does not cover the exact confirmed negative requirements")
    return {
        group: [
            {
                "requirement_digest": item["requirement_digest"],
                "assertion_ids": list(item["assertion_ids"]),
            }
            for item in bindings[group]
        ]
        for group in GROUPS
    }


def _load_confirmation_packet(
    root: Path,
    confirmation_packet: str | Path,
    *,
    profile: Mapping[str, Any],
    repository: Mapping[str, Any],
) -> dict[str, Any]:
    path = _external_input_path(root, confirmation_packet, "canonical confirmation packet")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise BilateralRuntimeProfileError("canonical confirmation packet is oversized")
    try:
        packet_bytes = path.read_bytes()
        raw = json.loads(packet_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BilateralRuntimeProfileError(
            f"canonical confirmation packet is not immutable canonical JSON: {exc}"
        ) from exc
    packet_sha256 = hashlib.sha256(packet_bytes).hexdigest()
    if not isinstance(raw, Mapping) or raw.get("version") != CONFIRMATION_PACKET_VERSION:
        raise BilateralRuntimeProfileError("confirmation packet must come from the canonical bilateral compiler")
    intent = _rehydrate_intent(raw.get("intent_packet"))
    ledger = _rehydrate_ledger(raw.get("semantic_ledger"))
    receipt = _rehydrate_receipt(raw.get("confirmation_receipt"))
    refinement = raw.get("refinement_session")
    guardrails = raw.get("guardrails")
    u7 = raw.get("u7_references")
    if (
        not isinstance(refinement, Mapping)
        or not isinstance(guardrails, list)
        or not guardrails
        or not isinstance(u7, Mapping)
    ):
        raise BilateralRuntimeProfileError(
            "confirmation packet is missing canonical refinement, guardrail, or U7 records"
        )
    positive_requirements = refinement.get("positive_requirements")
    negative_requirements = refinement.get("negative_requirements")
    confirmation_evidence = refinement.get("confirmation_evidence")
    teach_back = refinement.get("teach_back")
    if (
        not isinstance(positive_requirements, list)
        or not isinstance(negative_requirements, list)
        or not isinstance(confirmation_evidence, Mapping)
        or not isinstance(teach_back, Mapping)
    ):
        raise BilateralRuntimeProfileError("confirmation packet does not expose the canonical confirmed requirements")
    allowed_paths = confirmation_evidence.get("allowed_paths")
    if not isinstance(allowed_paths, list):
        raise BilateralRuntimeProfileError("confirmation packet does not expose its canonical allowed paths")
    revision_status = u7.get("intent_revision_status")
    if revision_status != profile["intent_contract"]["intent_revision_status"]:
        raise BilateralRuntimeProfileError("canonical intent revision status mismatch")
    if (
        intent.intent_digest != ledger.intent_digest
        or receipt.semantic_ledger_digest != ledger.ledger_digest
        or receipt.source_request_digest != refinement.get("source_request_digest")
        or receipt.guardrail_set_digest != stable_digest(guardrails)
        or not all(item in intent.prohibitions for item in negative_requirements)
        or list(intent.acceptance_criteria) != positive_requirements
    ):
        raise BilateralRuntimeProfileError(
            "canonical intent, ledger, confirmation, guardrail, or requirement identity mismatch"
        )
    profile_digest = str(profile["profile_sha256"])
    authority_digest = stable_digest(intent.authority.to_dict())
    try:
        current = receipt.is_current(
            repository_head=str(repository["head"]),
            source_tree_digest=str(repository["source_tree"]),
            source_request_digest=str(refinement["source_request_digest"]),
            positive_requirements=positive_requirements,
            negative_requirements=negative_requirements,
            semantic_ledger_digest=ledger.ledger_digest,
            guardrail_set_digest=stable_digest(guardrails),
            authority_digest=authority_digest,
            teach_back_digest=str(teach_back.get("teach_back_digest") or ""),
            allowed_paths=allowed_paths,
            runtime_profile_digest=profile_digest,
            now=time.time(),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise BilateralRuntimeProfileError(f"canonical confirmation currency check failed: {exc}") from exc
    if not current:
        raise BilateralRuntimeProfileError(
            "canonical confirmation is stale, expired, or bound to another source identity"
        )
    if tuple(allowed_paths) != tuple(profile["allowed_paths"]):
        raise BilateralRuntimeProfileError("canonical confirmation allowed paths do not match the runtime profile")
    requirement_bindings = _validate_requirement_coverage(
        profile,
        positive_requirements,
        negative_requirements,
    )
    guardrail_ids = []
    for item in guardrails:
        if not isinstance(item, Mapping):
            raise BilateralRuntimeProfileError("canonical guardrail record is invalid")
        guardrail_id = item.get("guardrail_id")
        if not isinstance(guardrail_id, str) or not guardrail_id:
            raise BilateralRuntimeProfileError("canonical guardrail identity is missing")
        guardrail_ids.append(guardrail_id)
    return {
        "packet_sha256": packet_sha256,
        "intent_digest": intent.intent_digest,
        "semantic_ledger_digest": ledger.ledger_digest,
        "confirmation_digest": receipt.confirmation_id,
        "guardrail_set_digest": receipt.guardrail_set_digest,
        "intent_revision_status": str(revision_status),
        "expected_repository_head": receipt.repository_head,
        "expected_source_tree": receipt.source_tree_digest,
        "allowed_path_set_digest": receipt.allowed_path_set_digest,
        "guardrail_ids": guardrail_ids,
        "positive_requirement_digests": sorted(
            _confirmed_requirement_digests(
                positive_requirements,
                "confirmed positive requirements",
            )
        ),
        "negative_requirement_digests": sorted(
            _confirmed_requirement_digests(
                negative_requirements,
                "confirmed negative requirements",
            )
        ),
        "requirement_bindings": requirement_bindings,
    }


def _artifact(output: Path, name: str) -> Path:
    path = (output / Path(*PurePosixPath(name).parts)).resolve()
    try:
        path.relative_to(output)
    except ValueError as exc:
        raise BilateralRuntimeProfileError("runtime trace escaped the output directory") from exc
    return path


def _lookup(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _matches(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "truthy":
        return bool(actual)
    if operator == "falsy":
        return not bool(actual)
    if operator == "nonempty":
        return hasattr(actual, "__len__") and len(actual) > 0
    try:
        return expected in actual
    except (TypeError, ValueError):
        return False


def _snapshot_traces(
    output: Path,
    traces: Sequence[str],
) -> dict[str, dict[str, Any]]:
    maximum = int(getattr(_v1, "MAX_ARTIFACT_BYTES", 32 * 1024 * 1024))
    snapshots: dict[str, dict[str, Any]] = {}
    for name in traces:
        path = _artifact(output, name)
        if not path.is_file() or path.is_symlink():
            raise BilateralRuntimeProfileError(f"runtime trace {name} was not produced by the current run")
        size = path.stat().st_size
        if size > maximum or size > MAX_JSON_BYTES:
            raise BilateralRuntimeProfileError(f"runtime trace {name} is oversized")
        try:
            body = path.read_bytes()
            value = json.loads(body.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BilateralRuntimeProfileError(f"runtime trace {name} is not immutable canonical JSON: {exc}") from exc
        if len(body) != size:
            raise BilateralRuntimeProfileError(f"runtime trace {name} changed while it was being snapshotted")
        snapshots[name] = {
            "value": value,
            "size_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
    return snapshots


def _evaluate(
    snapshots: Mapping[str, Mapping[str, Any]],
    assertion: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot = snapshots[str(assertion["artifact"])]
    value = snapshot["value"]
    found, actual = _lookup(value, str(assertion["json_path"]))
    return {
        **dict(assertion),
        "found": found,
        "actual": actual,
        "passed": found and _matches(actual, str(assertion["operator"]), assertion.get("expected")),
        "artifact_sha256": snapshot["sha256"],
    }


def _trace_inventory(
    snapshots: Mapping[str, Mapping[str, Any]],
    traces: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in traces:
        snapshot = snapshots[name]
        rows.append(
            {
                "path": name,
                "present": True,
                "size_bytes": snapshot["size_bytes"],
                "within_size_limit": True,
                "sha256": snapshot["sha256"],
            }
        )
    return rows


def run_runtime_profile_v2(
    root: Path,
    *,
    profile_path: str | Path,
    confirmation_packet: str | Path,
    output_dir: str | Path,
    venv_path: str | Path | None = None,
    install_requirements: bool = False,
    allow_dirty: bool = False,
    baseline_receipt: str | Path | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    before = _repo_identity(root)
    if allow_dirty:
        raise BilateralRuntimeProfileError(
            "V2 runtime proof cannot bind dirty working-tree execution to a committed source tree"
        )
    if before["status"]:
        raise BilateralRuntimeProfileError("repository is dirty; V2 proof requires a clean tree")
    profile = load_runtime_profile_v2(root, profile_path)
    output = _v1._external_output_path(root, output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise BilateralRuntimeProfileError("V2 runtime proof requires a fresh empty output directory")
    confirmation = _load_confirmation_packet(
        root,
        confirmation_packet,
        profile=profile,
        repository=before,
    )

    base = _v1.run_runtime_profile(
        root,
        profile_path=profile["base_profile"],
        output_dir=output,
        venv_path=venv_path,
        install_requirements=install_requirements,
        allow_dirty=False,
        baseline_receipt=baseline_receipt,
    )
    after = _repo_identity(root)
    snapshots = _snapshot_traces(output, profile["required_trace_artifacts"])
    results, by_id = {}, {}
    for group in GROUPS:
        results[group] = [_evaluate(snapshots, row) for row in profile[group]]
        by_id.update({row["assertion_id"]: row for row in results[group]})
    scenarios = []
    for row in profile["scenarios"]:
        required = [by_id[item] for item in row["required_assertion_ids"]]
        scenarios.append(
            {
                **row,
                "passed": all(item["passed"] for item in required),
                "failed_assertion_ids": [item["assertion_id"] for item in required if not item["passed"]],
            }
        )
    traces = _trace_inventory(snapshots, profile["required_trace_artifacts"])
    identity_ok = before == after
    ok = (
        bool(base.get("ok"))
        and identity_ok
        and all(item["passed"] for rows in results.values() for item in rows)
        and all(item["passed"] for item in scenarios)
        and all(item["present"] and item["within_size_limit"] for item in traces)
    )
    unproved = [item["assertion_id"] for rows in results.values() for item in rows if not item["passed"]]
    proof = {
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "profile_id": profile["profile_id"],
        "profile_path": profile["profile_path"],
        "profile_sha256": profile["profile_sha256"],
        "base_profile_id": profile["base_profile_id"],
        "base_profile_sha256": profile["base_profile_sha256"],
        "runtime_candidate_id": profile["runtime_candidate_id"],
        "objective": profile["objective"],
        "ok": ok,
        "repository_identity_before": before,
        "repository_identity_after": after,
        "repository_identity_unchanged": identity_ok,
        "resolved_expected_repository_head": confirmation["expected_repository_head"],
        "resolved_expected_source_tree": confirmation["expected_source_tree"],
        "intent_contract": {
            key: value
            for key, value in confirmation.items()
            if key
            in {
                "intent_digest",
                "semantic_ledger_digest",
                "confirmation_digest",
                "guardrail_set_digest",
                "intent_revision_status",
                "expected_repository_head",
                "expected_source_tree",
                "allowed_path_set_digest",
            }
        },
        "confirmation_packet_sha256": confirmation["packet_sha256"],
        "allowed_paths": list(profile["allowed_paths"]),
        "guardrail_ids": confirmation["guardrail_ids"],
        "confirmed_positive_requirement_digests": confirmation["positive_requirement_digests"],
        "confirmed_negative_requirement_digests": confirmation["negative_requirement_digests"],
        "requirement_bindings": confirmation["requirement_bindings"],
        "scenarios": scenarios,
        **results,
        "positive_requirements_proved": [item["assertion_id"] for item in results[GROUPS[0]] if item["passed"]],
        "negative_requirements_proved": [item["assertion_id"] for item in results[GROUPS[1]] if item["passed"]],
        "preservation_requirements_proved": [item["assertion_id"] for item in results[GROUPS[2]] if item["passed"]],
        "fault_behaviors_proved": [item["assertion_id"] for item in results[GROUPS[3]] if item["passed"]],
        "requirements_unproved": unproved,
        "guardrail_violations": [
            item["assertion_id"] for group in GROUPS[1:] for item in results[group] if not item["passed"]
        ],
        "required_trace_artifacts": traces,
        "independent_verifier": profile["independent_verifier"],
        "repair_policy": profile["repair_policy"],
        "base_runtime_receipt": {
            "version": base.get("version"),
            "profile_id": base.get("profile_id"),
            "run_digest": base.get("run_digest"),
            "ok": base.get("ok"),
            "cycle_state": base.get("cycle_state"),
        },
        "residual_risks": [] if ok else ["one or more runtime proof obligations remain unproved"],
        "human_review_required": True,
        "axiom_bindings": list(profile["axiom_bindings"]),
        **AUTHORITY_CONTRACT,
    }
    proof["proof_digest"] = _json_digest(proof)
    proof_path = output / "bilateral_runtime_proof.json"
    _v1._write_json(proof_path, proof)
    return {**proof, "proof_path": str(proof_path), "output_dir": str(output)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile", required=True)
    parser.add_argument(
        "--confirmation-packet",
        required=True,
        help="External canonical bilateral compiler packet for the exact clean execution head.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--venv")
    parser.add_argument("--install-requirements", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--baseline-receipt")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = run_runtime_profile_v2(
            Path(args.repo_root),
            profile_path=args.profile,
            confirmation_packet=args.confirmation_packet,
            output_dir=args.output_dir,
            venv_path=args.venv,
            install_requirements=args.install_requirements,
            allow_dirty=args.allow_dirty,
            baseline_receipt=args.baseline_receipt,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "version": VERSION,
                    "profile_version": PROFILE_VERSION,
                    "error": f"{type(exc).__name__}: {exc}",
                    **AUTHORITY_CONTRACT,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
