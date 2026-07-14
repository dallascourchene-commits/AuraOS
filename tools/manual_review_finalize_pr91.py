from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old in text:
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return
    if new in text:
        return
    raise RuntimeError(f"replacement marker missing in {path}: {old[:80]!r}")


def insert_before(path: str, marker: str, addition: str, sentinel: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if sentinel in text:
        return
    if marker not in text:
        raise RuntimeError(f"insertion marker missing in {path}: {marker[:80]!r}")
    target.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8")


def patch_navigator() -> None:
    replace_once(
        "aura_codebase_navigator.py",
        '    "Aura_Memory",\n    ".venv",',
        '    "Aura_Memory",\n    "Aura_Sandbox",\n    ".venv",',
    )
    replace_once(
        "aura_codebase_navigator.py",
        "\n\n\n\ndef _atomic_write_text",
        "\n\ndef _atomic_write_text",
    )


def patch_replay() -> None:
    insert_before(
        "aura_model_cognome_replay.py",
        "@dataclass(frozen=True)\nclass ReplayOutcome:",
        '''def _strict_optional_bool(value: Any, name: str) -> bool | None:\n    if value is None:\n        return None\n    if type(value) is not bool:\n        raise ValueError(f"{name} must be a boolean or None")\n    return value\n\n\n''',
        "def _strict_optional_bool(",
    )
    replace_once(
        "aura_model_cognome_replay.py",
        '        if not self.profile_id:\n            raise ValueError("profile_id must not be empty")\n',
        '        if not self.profile_id:\n            raise ValueError("profile_id must not be empty")\n        _strict_optional_bool(self.verifier_pass, "verifier_pass")\n',
    )
    replace_once(
        "aura_model_cognome_replay.py",
        '            verifier_pass=value.get("verifier_pass"),',
        '            verifier_pass=_strict_optional_bool(value.get("verifier_pass"), "verifier_pass"),',
    )
    replace_once(
        "aura_model_cognome_replay.py",
        '        if not self.capability_graph_digest or not self.path_digest:\n            raise ValueError("replay cases must be graph and path bound")\n',
        '        if not self.capability_graph_digest or not self.path_digest:\n            raise ValueError("replay cases must be graph and path bound")\n        _nonnegative(self.created_at, "created_at")\n',
    )
    replace_once(
        "aura_model_cognome_replay.py",
        '        if self.policy_mode in {CASCADE, PANEL} and len(self.profile_ids) < 2:\n            raise ValueError(f"{self.policy_mode} replay policies require at least two profiles")\n',
        '        if self.policy_mode in {CASCADE, PANEL} and len(self.profile_ids) < 2:\n            raise ValueError(f"{self.policy_mode} replay policies require at least two profiles")\n        if any(not str(profile_id).strip() for profile_id in self.profile_ids):\n            raise ValueError("replay policy profile IDs must not be empty")\n        if len(self.profile_ids) != len(set(self.profile_ids)):\n            raise ValueError("replay policies cannot contain duplicate profile IDs")\n',
    )


def patch_drift() -> None:
    insert_before(
        "aura_model_cognome_drift.py",
        "@dataclass(frozen=True)\nclass ProbeDefinition:",
        '''def _strict_bool(value: Any, name: str) -> bool:\n    if type(value) is not bool:\n        raise ValueError(f"{name} must be a boolean")\n    return value\n\n\n''',
        "def _strict_bool(",
    )
    replace_once(
        "aura_model_cognome_drift.py",
        '        _nonnegative(self.latency_ms, "latency_ms")\n',
        '        _strict_bool(self.verifier_pass, "verifier_pass")\n        _strict_bool(self.format_valid, "format_valid")\n        _nonnegative(self.latency_ms, "latency_ms")\n        _nonnegative(self.observed_at, "observed_at")\n',
    )
    replace_once(
        "aura_model_cognome_drift.py",
        '            verifier_pass=bool(value.get("verifier_pass")),\n            format_valid=bool(value.get("format_valid")),',
        '            verifier_pass=_strict_bool(value.get("verifier_pass"), "verifier_pass"),\n            format_valid=_strict_bool(value.get("format_valid"), "format_valid"),',
    )
    replace_once(
        "aura_model_cognome_drift.py",
        '            observed_at=float(value.get("observed_at") or time.time()),',
        '            observed_at=float(time.time() if value.get("observed_at") is None else value.get("observed_at")),',
    )
    replace_once(
        "aura_model_cognome_drift.py",
        '''    status = WARNING\n    if assessment.status == STABLE:\n        status = "STABLE"\n    elif approve_lifecycle_change:\n        if not str(approved_by).strip():\n            raise ValueError("approved_by is required for lifecycle changes")\n        if assessment.status == STALE_PROPOSED:\n            status = EndpointStatus.STALE.value\n        elif assessment.status == QUARANTINE_PROPOSED:\n            status = EndpointStatus.QUARANTINED.value\n''',
        '''    status = WARNING\n    lifecycle_change_approved = False\n    if assessment.status == STABLE:\n        status = "STABLE"\n    if approve_lifecycle_change:\n        if assessment.status not in {STALE_PROPOSED, QUARANTINE_PROPOSED}:\n            raise ValueError("only stale or quarantine proposals can approve a lifecycle change")\n        if not str(approved_by).strip():\n            raise ValueError("approved_by is required for lifecycle changes")\n        lifecycle_change_approved = True\n        if assessment.status == STALE_PROPOSED:\n            status = EndpointStatus.STALE.value\n        else:\n            status = EndpointStatus.QUARANTINED.value\n''',
    )
    replace_once(
        "aura_model_cognome_drift.py",
        '            "lifecycle_change_approved": bool(approve_lifecycle_change),\n            "approved_by": str(approved_by),',
        '            "lifecycle_change_approved": lifecycle_change_approved,\n            "approved_by": str(approved_by) if lifecycle_change_approved else "",',
    )


def patch_promotion() -> None:
    replace_once(
        "aura_model_cognome_promotion.py",
        '''        _finite(self.minimum_success_rate_delta, "minimum_success_rate_delta")\n        _finite(self.maximum_success_regression, "maximum_success_regression")\n        _finite(self.maximum_cost_increase_usd, "maximum_cost_increase_usd")\n        _finite(self.maximum_time_increase_ms, "maximum_time_increase_ms")\n        _finite(self.maximum_scope_violation_delta, "maximum_scope_violation_delta")\n''',
        '''        for name in (\n            "minimum_success_rate_delta",\n            "maximum_success_regression",\n            "maximum_cost_increase_usd",\n            "maximum_time_increase_ms",\n            "maximum_scope_violation_delta",\n        ):\n            if _finite(getattr(self, name), name) < 0:\n                raise ValueError(f"{name} must be non-negative")\n''',
    )
    replace_once(
        "aura_model_cognome_promotion.py",
        '    if not candidate_policy_id or not baseline_policy_id:\n        raise ValueError("candidate and baseline policy IDs must not be empty")\n',
        '    if not candidate_policy_id or not baseline_policy_id:\n        raise ValueError("candidate and baseline policy IDs must not be empty")\n    if candidate_policy_id == baseline_policy_id:\n        raise ValueError("candidate and baseline policy IDs must differ")\n',
    )
    replace_once(
        "aura_model_cognome_promotion.py",
        '        if self.status != PROMOTION_PROPOSED:\n            raise ValueError("route policy proposals must terminate at PROMOTION_PROPOSED")\n',
        '        if self.status != PROMOTION_PROPOSED:\n            raise ValueError("route policy proposals must terminate at PROMOTION_PROPOSED")\n        if not math.isfinite(float(self.created_at)) or self.created_at < 0:\n            raise ValueError("created_at must be finite and non-negative")\n',
    )


def patch_federation() -> None:
    replace_once("aura_model_cognome_federation.py", "import json\n", "import json\nimport math\nimport os\n")
    replace_once("aura_model_cognome_federation.py", "from pathlib import Path\n", "from pathlib import Path\nimport tempfile\n")
    insert_before(
        "aura_model_cognome_federation.py",
        "@dataclass(frozen=True)\nclass FederationEnvelope:",
        '''def _strict_bool(value: Any, name: str) -> bool:\n    if type(value) is not bool:\n        raise ValueError(f"{name} must be a boolean")\n    return value\n\n\ndef _finite(value: Any, name: str) -> float:\n    number = float(value)\n    if not math.isfinite(number):\n        raise ValueError(f"{name} must be finite")\n    return number\n\n\ndef _identity_basis(*, sender_id: str, recipient_scope: str, nonce: str, payload_digest: str, created_at: float, expires_at: float) -> dict[str, Any]:\n    return {\n        "sender_id": sender_id,\n        "recipient_scope": recipient_scope,\n        "nonce": nonce,\n        "payload_digest": payload_digest,\n        "created_at": created_at,\n        "expires_at": expires_at,\n    }\n\n\ndef _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))\n    temporary_path = Path(temporary_name)\n    try:\n        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:\n            json.dump(payload, handle, indent=2, sort_keys=True)\n            handle.flush()\n            os.fsync(handle.fileno())\n        os.replace(temporary_path, path)\n    finally:\n        temporary_path.unlink(missing_ok=True)\n\n\n''',
        "def _identity_basis(",
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''        if self.expires_at <= self.created_at:\n            raise ValueError("expires_at must be greater than created_at")\n        if stable_digest(self.payload) != self.payload_digest:\n''',
        '''        if self.version != FEDERATION_VERSION:\n            raise ValueError("unsupported federation envelope version")\n        if not str(self.signature_scheme).strip():\n            raise ValueError("signature_scheme must not be empty")\n        _finite(self.created_at, "created_at")\n        _finite(self.expires_at, "expires_at")\n        if self.expires_at <= self.created_at:\n            raise ValueError("expires_at must be greater than created_at")\n        _strict_bool(self.vsa_patch_authority, "vsa_patch_authority")\n        _strict_bool(self.runtime_authority, "runtime_authority")\n        _strict_bool(self.automatic_import, "automatic_import")\n        expected_id = stable_id("federation-envelope", _identity_basis(\n            sender_id=self.sender_id,\n            recipient_scope=self.recipient_scope,\n            nonce=self.nonce,\n            payload_digest=self.payload_digest,\n            created_at=self.created_at,\n            expires_at=self.expires_at,\n        ))\n        if self.envelope_id != expected_id:\n            raise ValueError("federation envelope ID mismatch")\n        if stable_digest(self.payload) != self.payload_digest:\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    @classmethod\n    def from_mapping(cls, value: Mapping[str, Any]) -> "FederationEnvelope":\n        return cls(\n            envelope_id=str(value.get("envelope_id") or ""),\n            sender_id=str(value.get("sender_id") or ""),\n            recipient_scope=str(value.get("recipient_scope") or ""),\n            nonce=str(value.get("nonce") or ""),\n            payload_digest=str(value.get("payload_digest") or ""),\n            payload=dict(value.get("payload") or {}),\n            created_at=float(value.get("created_at") or 0.0),\n            expires_at=float(value.get("expires_at") or 0.0),\n            signature=str(value.get("signature") or ""),\n            signature_scheme=str(value.get("signature_scheme") or "UNSIGNED_LOCAL"),\n            version=str(value.get("version") or FEDERATION_VERSION),\n            patch_authority=str(value.get("patch_authority") or PATCH_AUTHORITY),\n            vsa_patch_authority=bool(value.get("vsa_patch_authority", False)),\n            runtime_authority=bool(value.get("runtime_authority", False)),\n            automatic_import=bool(value.get("automatic_import", False)),\n        )\n''',
        '''    @classmethod\n    def from_mapping(cls, value: Mapping[str, Any]) -> "FederationEnvelope":\n        packet = cls(\n            envelope_id=str(value.get("envelope_id") or ""),\n            sender_id=str(value.get("sender_id") or ""),\n            recipient_scope=str(value.get("recipient_scope") or ""),\n            nonce=str(value.get("nonce") or ""),\n            payload_digest=str(value.get("payload_digest") or ""),\n            payload=dict(value.get("payload") or {}),\n            created_at=float(value.get("created_at") if value.get("created_at") is not None else 0.0),\n            expires_at=float(value.get("expires_at") if value.get("expires_at") is not None else 0.0),\n            signature=str(value.get("signature") or ""),\n            signature_scheme=str(value.get("signature_scheme") or "UNSIGNED_LOCAL"),\n            version=str(value.get("version") or FEDERATION_VERSION),\n            patch_authority=str(value.get("patch_authority") or PATCH_AUTHORITY),\n            vsa_patch_authority=_strict_bool(value.get("vsa_patch_authority", False), "vsa_patch_authority"),\n            runtime_authority=_strict_bool(value.get("runtime_authority", False), "runtime_authority"),\n            automatic_import=_strict_bool(value.get("automatic_import", False), "automatic_import"),\n        )\n        supplied_digest = str(value.get("envelope_digest") or "")\n        if supplied_digest and supplied_digest != stable_digest(asdict(packet)):\n            raise ValueError("federation envelope digest mismatch")\n        return packet\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    ttl = float(ttl_seconds)\n    if ttl <= 0:\n        raise ValueError("ttl_seconds must be positive")\n''',
        '''    ttl = _finite(ttl_seconds, "ttl_seconds")\n    if ttl <= 0:\n        raise ValueError("ttl_seconds must be positive")\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '    now = time.time() if created_at is None else float(created_at)\n',
        '    now = _finite(time.time() if created_at is None else created_at, "created_at")\n',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    basis = {\n        "sender_id": sender_id,\n        "recipient_scope": recipient_scope,\n        "nonce": nonce,\n        "payload_digest": digest,\n        "created_at": now,\n        "expires_at": now + ttl,\n    }\n''',
        '''    basis = _identity_basis(\n        sender_id=sender_id,\n        recipient_scope=recipient_scope,\n        nonce=nonce,\n        payload_digest=digest,\n        created_at=now,\n        expires_at=now + ttl,\n    )\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    timestamp = time.time() if now is None else float(now)\n    if timestamp < packet.created_at:\n        errors.append("envelope_not_yet_valid")\n    if timestamp >= packet.expires_at:\n        errors.append("envelope_expired")\n''',
        '''    try:\n        timestamp = _finite(time.time() if now is None else now, "validation time")\n    except (TypeError, ValueError):\n        errors.append("validation_time_invalid")\n        timestamp = packet.created_at\n    if "validation_time_invalid" not in errors and timestamp < packet.created_at:\n        errors.append("envelope_not_yet_valid")\n    if "validation_time_invalid" not in errors and timestamp >= packet.expires_at:\n        errors.append("envelope_expired")\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    packet = envelope if isinstance(envelope, FederationEnvelope) else FederationEnvelope.from_mapping(envelope)\n    validation = validate_federation_envelope(\n        packet,\n        allowed_senders=allowed_senders,\n        expected_recipient_scope=expected_recipient_scope,\n        seen_nonces=seen_nonces,\n        verifier=verifier,\n        allow_unsigned_local=allow_unsigned_local,\n        now=now,\n    )\n''',
        '''    packet = envelope if isinstance(envelope, FederationEnvelope) else FederationEnvelope.from_mapping(envelope)\n    validation_nonces = set(seen_nonces or ())\n    validation = validate_federation_envelope(\n        packet,\n        allowed_senders=allowed_senders,\n        expected_recipient_scope=expected_recipient_scope,\n        seen_nonces=validation_nonces,\n        verifier=verifier,\n        allow_unsigned_local=allow_unsigned_local,\n        now=now,\n    )\n''',
    )
    replace_once(
        "aura_model_cognome_federation.py",
        '''    destination = Path(staging_path).resolve()\n    destination.parent.mkdir(parents=True, exist_ok=True)\n    destination.write_text(json.dumps(packet.payload, indent=2, sort_keys=True), encoding="utf-8")\n    imported = store.import_bundle(destination)\n''',
        '''    destination = Path(staging_path).resolve()\n    _atomic_write_json(destination, packet.payload)\n    imported = store.import_bundle(destination)\n    if seen_nonces is not None:\n        seen_nonces.add(packet.nonce)\n''',
    )


def patch_jacobian() -> None:
    insert_before(
        "aura_open_weight_jacobian_adapter.py",
        "@dataclass(frozen=True)\nclass JacobianLensSummary:",
        '''def _strict_bool(value: Any, name: str) -> bool:\n    if type(value) is not bool:\n        raise ValueError(f"{name} must be a boolean")\n    return value\n\n\ndef _summary_basis(*, model_artifact_digest: str, method_version: str, layer_start: int, layer_end: int, sample_count: int, metrics: Mapping[str, float], task_bucket: str, dataset_digest: str, code_digest: str) -> dict[str, Any]:\n    return {\n        "model_artifact_digest": model_artifact_digest,\n        "method_version": method_version,\n        "layer_start": int(layer_start),\n        "layer_end": int(layer_end),\n        "sample_count": int(sample_count),\n        "metrics": {str(key): float(value) for key, value in metrics.items()},\n        "task_bucket": task_bucket,\n        "dataset_digest": dataset_digest,\n        "code_digest": code_digest,\n    }\n\n\n''',
        "def _summary_basis(",
    )
    replace_once(
        "aura_open_weight_jacobian_adapter.py",
        '''        expected = stable_digest(\n            {\n                "model_artifact_digest": self.model_artifact_digest,\n                "method_version": self.method_version,\n                "layer_start": self.layer_start,\n                "layer_end": self.layer_end,\n                "sample_count": self.sample_count,\n                "metrics": self.metrics,\n                "task_bucket": self.task_bucket,\n                "dataset_digest": self.dataset_digest,\n                "code_digest": self.code_digest,\n            }\n        )\n        if expected != self.analysis_artifact_digest:\n            raise ValueError("analysis_artifact_digest does not match the canonical summary")\n''',
        '''        if self.version != JACOBIAN_ADAPTER_VERSION:\n            raise ValueError("unsupported Jacobian summary version")\n        if not math.isfinite(float(self.created_at)) or self.created_at < 0:\n            raise ValueError("created_at must be finite and non-negative")\n        _strict_bool(self.raw_activations_stored, "raw_activations_stored")\n        _strict_bool(self.raw_prompts_stored, "raw_prompts_stored")\n        _strict_bool(self.private_reasoning_stored, "private_reasoning_stored")\n        basis = _summary_basis(\n            model_artifact_digest=self.model_artifact_digest,\n            method_version=self.method_version,\n            layer_start=self.layer_start,\n            layer_end=self.layer_end,\n            sample_count=self.sample_count,\n            metrics=self.metrics,\n            task_bucket=self.task_bucket,\n            dataset_digest=self.dataset_digest,\n            code_digest=self.code_digest,\n        )\n        expected = stable_digest(basis)\n        if expected != self.analysis_artifact_digest:\n            raise ValueError("analysis_artifact_digest does not match the canonical summary")\n        if self.summary_id != stable_id("jacobian-summary", basis):\n            raise ValueError("summary_id does not match the canonical summary")\n''',
    )
    replace_once(
        "aura_open_weight_jacobian_adapter.py",
        '''        basis = {\n            "model_artifact_digest": model_artifact_digest,\n            "method_version": method_version,\n            "layer_start": int(layer_start),\n            "layer_end": int(layer_end),\n            "sample_count": int(sample_count),\n            "metrics": clean_metrics,\n            "task_bucket": task_bucket,\n            "dataset_digest": dataset_digest,\n            "code_digest": code_digest,\n        }\n''',
        '''        basis = _summary_basis(\n            model_artifact_digest=model_artifact_digest,\n            method_version=method_version,\n            layer_start=layer_start,\n            layer_end=layer_end,\n            sample_count=sample_count,\n            metrics=clean_metrics,\n            task_bucket=task_bucket,\n            dataset_digest=dataset_digest,\n            code_digest=code_digest,\n        )\n''',
    )
    replace_once(
        "aura_open_weight_jacobian_adapter.py",
        '''            raw_activations_stored=bool(value.get("raw_activations_stored", False)),\n            raw_prompts_stored=bool(value.get("raw_prompts_stored", False)),\n            private_reasoning_stored=bool(value.get("private_reasoning_stored", False)),\n''',
        '''            raw_activations_stored=_strict_bool(value.get("raw_activations_stored", False), "raw_activations_stored"),\n            raw_prompts_stored=_strict_bool(value.get("raw_prompts_stored", False), "raw_prompts_stored"),\n            private_reasoning_stored=_strict_bool(value.get("private_reasoning_stored", False), "private_reasoning_stored"),\n''',
    )
    replace_once(
        "aura_open_weight_jacobian_adapter.py",
        '''    if endpoint.endpoint_fingerprint and packet.model_artifact_digest != endpoint.endpoint_fingerprint:\n        raise ValueError("Jacobian model artifact digest does not match endpoint fingerprint")\n''',
        '''    if not endpoint.endpoint_fingerprint:\n        raise ValueError("Jacobian mechanistic evidence requires an endpoint artifact fingerprint")\n    if packet.model_artifact_digest != endpoint.endpoint_fingerprint:\n        raise ValueError("Jacobian model artifact digest does not match endpoint fingerprint")\n''',
    )


def write_workflow() -> None:
    Path(".github/workflows/model-cognome-replay-probes.yml").write_text(
        '''name: Model Cognome Replay and Probes

on:
  pull_request:
    paths:
      - "aura_model_cognome_replay.py"
      - "aura_model_cognome_drift.py"
      - "aura_model_cognome_promotion.py"
      - "aura_model_cognome_federation.py"
      - "aura_open_weight_jacobian_adapter.py"
      - "tests/test_aura_model_cognome_replay_probes.py"
      - "tests/test_aura_model_cognome_manual_review.py"
      - "test_aura_icm_workspace.py"
      - ".github/workflows/model-cognome-replay-probes.yml"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  replay-probes:
    name: Replay and probe contracts (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    timeout-minutes: 35
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha || github.sha }}
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install tooling
        run: python -m pip install pytest ruff
      - name: Compile modules
        run: |
          python -m py_compile \
            aura_model_cognome_replay.py \
            aura_model_cognome_drift.py \
            aura_model_cognome_promotion.py \
            aura_model_cognome_federation.py \
            aura_open_weight_jacobian_adapter.py
      - name: Fatal lint checks
        run: |
          ruff check --select E9,F63,F7,F82 \
            aura_model_cognome_replay.py \
            aura_model_cognome_drift.py \
            aura_model_cognome_promotion.py \
            aura_model_cognome_federation.py \
            aura_open_weight_jacobian_adapter.py \
            tests/test_aura_model_cognome_replay_probes.py \
            tests/test_aura_model_cognome_manual_review.py \
            test_aura_icm_workspace.py
      - name: Run replay, probe, and ICM contracts
        run: |
          python -m pytest -q \
            tests/test_aura_model_cognome_replay_probes.py \
            tests/test_aura_model_cognome_manual_review.py \
            test_aura_icm_workspace.py
''',
        encoding="utf-8",
    )


def write_tests() -> None:
    Path("tests/test_aura_model_cognome_manual_review.py").write_text(
        '''from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aura_codebase_navigator import DEFAULT_SKIP_DIRS
from aura_model_cognome import ModelAccessClass, ModelEndpointIdentity
from aura_model_cognome_drift import ProbeResult, STABLE, DriftAssessment, persist_drift_assessment
from aura_model_cognome_federation import (
    FederationEnvelope,
    create_federation_envelope,
    import_validated_envelope,
    validate_federation_envelope,
)
from aura_model_cognome_promotion import RoutePromotionPolicy, evaluate_route_policy_promotion
from aura_model_cognome_replay import CASCADE, ReplayOutcome, ReplayPolicy
from aura_open_weight_jacobian_adapter import JacobianLensSummary, build_open_weight_observation


def test_codemap_excludes_generated_sandbox_vault() -> None:
    assert "Aura_Sandbox" in DEFAULT_SKIP_DIRS


def test_replay_and_probe_boolean_fields_are_strict() -> None:
    with pytest.raises(ValueError, match="boolean"):
        ReplayOutcome.from_mapping({
            "observation_id": "obs",
            "profile_id": "profile",
            "verifier_pass": "false",
            "evidence_digest": "digest",
        })
    with pytest.raises(ValueError, match="boolean"):
        ProbeResult.from_mapping({
            "probe_id": "probe",
            "profile_id": "profile",
            "endpoint_fingerprint": "fp",
            "verifier_pass": "false",
            "format_valid": True,
            "latency_ms": 1,
        })


def test_replay_policy_rejects_duplicate_profiles() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ReplayPolicy.create(policy_mode=CASCADE, profile_ids=("same", "same"))


def _signed_envelope():
    def signer(message: bytes) -> str:
        return "sig:" + message.hex()

    return create_federation_envelope(
        {"records": {}},
        sender_id="node-a",
        recipient_scope="community",
        nonce="nonce-a",
        signer=signer,
        signature_scheme="TEST",
        created_at=10,
        ttl_seconds=30,
    )


def test_federation_rejects_tampered_identity_and_string_authority_flags() -> None:
    envelope = _signed_envelope()
    tampered = envelope.to_dict()
    tampered["envelope_id"] = "forged-id"
    result = validate_federation_envelope(
        tampered,
        allowed_senders={"node-a"},
        expected_recipient_scope="community",
        verifier=lambda message, signature, sender: True,
        now=20,
    )
    assert result["ok"] is False
    assert "envelope_invalid" in result["errors"]

    invalid_flag = envelope.to_dict()
    invalid_flag["runtime_authority"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        FederationEnvelope.from_mapping(invalid_flag)


def test_federation_requires_finite_timing_and_consumes_nonce_after_import(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite"):
        create_federation_envelope(
            {"records": {}},
            sender_id="node-a",
            recipient_scope="community",
            nonce="nonce-inf",
            ttl_seconds=float("inf"),
            allow_unsigned_local=True,
        )

    class FailingStore:
        def import_bundle(self, path: Path):
            raise RuntimeError("import failed")

    envelope = create_federation_envelope(
        {"records": {}},
        sender_id="node-a",
        recipient_scope="community",
        nonce="nonce-import",
        allow_unsigned_local=True,
        created_at=10,
    )
    seen: set[str] = set()
    with pytest.raises(RuntimeError, match="import failed"):
        import_validated_envelope(
            FailingStore(),
            envelope,
            allowed_senders={"node-a"},
            expected_recipient_scope="community",
            seen_nonces=seen,
            allow_unsigned_local=True,
            staging_path=tmp_path / "manual-review-import.json",
            now=20,
        )
    assert "nonce-import" not in seen


def test_drift_approval_only_applies_to_lifecycle_proposals() -> None:
    assessment = DriftAssessment(
        assessment_id="assessment",
        profile_id="profile",
        reference_fingerprint="fp",
        current_fingerprint="fp",
        reference_count=3,
        current_count=3,
        drift_score=0.0,
        status=STABLE,
        metric_deltas={},
        evidence_digest="digest",
        policy_version="test",
        created_at=1,
    )
    with pytest.raises(ValueError, match="only stale or quarantine"):
        persist_drift_assessment(
            object(), assessment, approve_lifecycle_change=True, approved_by="reviewer"
        )


def test_promotion_thresholds_and_policy_identity_are_safe() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        RoutePromotionPolicy(maximum_cost_increase_usd=-1)
    with pytest.raises(ValueError, match="must differ"):
        evaluate_route_policy_promotion(
            candidate_policy_id="same",
            candidate_policy_mode="DIRECT",
            baseline_policy_id="same",
            replay_evidence={},
            shadow_evidence={},
        )


def test_jacobian_summary_is_content_addressed_and_privacy_flags_are_strict() -> None:
    summary = JacobianLensSummary.create(
        model_artifact_digest="model-fp",
        method_version="test",
        layer_start=1,
        layer_end=2,
        sample_count=3,
        metrics={"workspace_rank": 1},
        created_at=1,
    )
    tampered = summary.to_dict()
    tampered["summary_id"] = "forged-summary"
    with pytest.raises(ValueError, match="summary_id"):
        JacobianLensSummary.from_mapping(tampered)

    invalid_flag = summary.to_dict()
    invalid_flag["raw_prompts_stored"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        JacobianLensSummary.from_mapping(invalid_flag)

    endpoint = ModelEndpointIdentity.create(
        provider="test",
        requested_model="open-model",
        access_class=ModelAccessClass.OPEN_WEIGHT,
        endpoint_fingerprint="model-fp",
        first_seen_at=1,
        last_seen_at=1,
    )
    with pytest.raises(ValueError, match="artifact fingerprint"):
        build_open_weight_observation(replace(endpoint, endpoint_fingerprint=""), summary)
''',
        encoding="utf-8",
    )


def main() -> None:
    patch_navigator()
    patch_replay()
    patch_drift()
    patch_promotion()
    patch_federation()
    patch_jacobian()
    write_workflow()
    write_tests()


if __name__ == "__main__":
    main()
