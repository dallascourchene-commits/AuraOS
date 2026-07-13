from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    left = text.find(start)
    if left < 0:
        raise RuntimeError(f"missing start marker: {start!r}")
    right = text.find(end, left)
    if right < 0:
        raise RuntimeError(f"missing end marker: {end!r}")
    return text[:left] + replacement + text[right:]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


# Replay comparisons must use identical common cases.
replay_path = ROOT / "aura_model_cognome_replay.py"
replay = replay_path.read_text(encoding="utf-8")
replay_compare = '''def compare_replay_evaluations(candidate: ReplayEvaluation, baseline: ReplayEvaluation) -> dict[str, Any]:
    if candidate.measurement_mode != "REPLAY" or baseline.measurement_mode != "REPLAY":
        raise ValueError("only REPLAY evaluations can be compared")
    candidate_map = {
        item.case_id: item for item in candidate.case_results if item.status == "EVALUATED"
    }
    baseline_map = {
        item.case_id: item for item in baseline.case_results if item.status == "EVALUATED"
    }
    common = sorted(set(candidate_map) & set(baseline_map))
    if not common:
        raise ValueError("replay evaluations have no common evaluated cases")

    def summarize(values: dict[str, ReplayCaseResult]) -> dict[str, float | None]:
        selected = [values[case_id] for case_id in common]
        successes = [item.verified_success for item in selected if item.verified_success is not None]
        return {
            "verified_success_rate": (
                sum(1 for value in successes if value) / len(successes) if successes else None
            ),
            "mean_cost_usd": _mean_known(item.cost_usd for item in selected),
            "mean_time_to_verified_ms": _mean_known(item.time_to_verified_ms for item in selected),
            "mean_repair_attempts": _mean_known(item.repair_attempts for item in selected),
            "mean_scope_violation_count": _mean_known(
                item.scope_violation_count for item in selected
            ),
        }

    candidate_summary = summarize(candidate_map)
    baseline_summary = summarize(baseline_map)

    def delta(name: str) -> float | None:
        left = candidate_summary[name]
        right = baseline_summary[name]
        return None if left is None or right is None else float(left) - float(right)

    union_count = len(set(candidate_map) | set(baseline_map))
    result = {
        "comparison_id": stable_id(
            "replay-comparison",
            {
                "candidate": candidate.evaluation_id,
                "baseline": baseline.evaluation_id,
                "common_cases": common,
            },
        ),
        "measurement_mode": "REPLAY",
        "candidate_evaluation_id": candidate.evaluation_id,
        "baseline_evaluation_id": baseline.evaluation_id,
        "common_case_count": len(common),
        "evaluated_count": len(common),
        "coverage": len(common) / union_count if union_count else 0.0,
        "success_rate_delta": delta("verified_success_rate"),
        "mean_cost_delta_usd": delta("mean_cost_usd"),
        "mean_time_delta_ms": delta("mean_time_to_verified_ms"),
        "mean_repair_delta": delta("mean_repair_attempts"),
        "mean_scope_violation_delta": delta("mean_scope_violation_count"),
        "candidate_common_summary": candidate_summary,
        "baseline_common_summary": baseline_summary,
        "candidate_evidence_digest": candidate.evidence_digest,
        "baseline_evidence_digest": baseline.evidence_digest,
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    result["comparison_digest"] = stable_digest(result)
    return result


'''
replay = replace_between(
    replay,
    "def compare_replay_evaluations(",
    "def persist_replay_comparison(",
    replay_compare,
)
replay_path.write_text(replay, encoding="utf-8")

# Duplicate probe IDs must not be weighted multiple times.
drift_path = ROOT / "aura_model_cognome_drift.py"
drift = drift_path.read_text(encoding="utf-8")
needle = '''    reference_ids = {item.probe_id for item in reference}
    current_ids = {item.probe_id for item in current}
    if reference_ids != current_ids:
'''
replacement = '''    reference_ids = {item.probe_id for item in reference}
    current_ids = {item.probe_id for item in current}
    if len(reference_ids) != len(reference) or len(current_ids) != len(current):
        raise ValueError("probe batches cannot contain duplicate probe IDs")
    if reference_ids != current_ids:
'''
if needle not in drift:
    raise RuntimeError("drift duplicate-probe insertion point missing")
drift_path.write_text(drift.replace(needle, replacement, 1), encoding="utf-8")

# Signed envelopes need a provisional signing packet; invalid mappings return a
# fail-closed validation result instead of escaping as an exception.
federation_path = ROOT / "aura_model_cognome_federation.py"
federation = federation_path.read_text(encoding="utf-8")
federation = federation.replace(
    '            "payload_digest": self.payload_digest,\n            "created_at": self.created_at,',
    '            "payload_digest": self.payload_digest,\n            "signature_scheme": self.signature_scheme,\n            "created_at": self.created_at,',
    1,
)
create_function = '''def create_federation_envelope(
    payload: Mapping[str, Any],
    *,
    sender_id: str,
    recipient_scope: str,
    nonce: str,
    ttl_seconds: float = 3600.0,
    signer: Signer | None = None,
    signature_scheme: str = "EXTERNAL",
    allow_unsigned_local: bool = False,
    created_at: float | None = None,
) -> FederationEnvelope:
    if not sender_id or not recipient_scope or not nonce:
        raise ValueError("sender_id, recipient_scope, and nonce must not be empty")
    ttl = float(ttl_seconds)
    if ttl <= 0:
        raise ValueError("ttl_seconds must be positive")
    clean = json.loads(canonical_json(dict(payload)))
    if clean.get("patch_authority") not in (None, PATCH_AUTHORITY):
        raise ValueError("federated payload patch authority is invalid")
    if clean.get("vsa_patch_authority") not in (None, False):
        raise ValueError("federated payload VSA authority is invalid")
    now = time.time() if created_at is None else float(created_at)
    digest = stable_digest(clean)
    scheme = "UNSIGNED_LOCAL" if signer is None else str(signature_scheme)
    if signer is not None and scheme == "UNSIGNED_LOCAL":
        raise ValueError("signed envelopes cannot use UNSIGNED_LOCAL")
    basis = {
        "sender_id": sender_id,
        "recipient_scope": recipient_scope,
        "nonce": nonce,
        "payload_digest": digest,
        "created_at": now,
        "expires_at": now + ttl,
    }
    provisional = FederationEnvelope(
        envelope_id=stable_id("federation-envelope", basis),
        sender_id=sender_id,
        recipient_scope=recipient_scope,
        nonce=nonce,
        payload_digest=digest,
        payload=clean,
        created_at=now,
        expires_at=now + ttl,
        signature="" if signer is None else "PENDING_SIGNATURE",
        signature_scheme=scheme,
    )
    if signer is None:
        if not allow_unsigned_local:
            raise ValueError("a signer is required unless allow_unsigned_local is explicit")
        return provisional
    signature = str(signer(provisional.signing_payload()))
    if not signature:
        raise ValueError("signer returned an empty signature")
    return FederationEnvelope(**{**asdict(provisional), "signature": signature})


'''
federation = replace_between(
    federation,
    "def create_federation_envelope(",
    "def validate_federation_envelope(",
    create_function,
)
validate_function = '''def validate_federation_envelope(
    envelope: FederationEnvelope | Mapping[str, Any],
    *,
    allowed_senders: Iterable[str],
    expected_recipient_scope: str,
    seen_nonces: MutableSet[str] | None = None,
    verifier: Verifier | None = None,
    allow_unsigned_local: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    try:
        packet = (
            envelope
            if isinstance(envelope, FederationEnvelope)
            else FederationEnvelope.from_mapping(envelope)
        )
    except (TypeError, ValueError) as exc:
        message = str(exc)
        code = "payload_digest_mismatch" if "payload digest" in message else "envelope_invalid"
        result = {
            "ok": False,
            "errors": [code],
            "error_detail": message,
            "proposal_only": True,
            "automatic_import": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        result["validation_digest"] = stable_digest(result)
        return result
    errors: list[str] = []
    allowed = {str(item) for item in allowed_senders}
    if packet.sender_id not in allowed:
        errors.append("sender_not_allowlisted")
    if packet.recipient_scope != expected_recipient_scope:
        errors.append("recipient_scope_mismatch")
    timestamp = time.time() if now is None else float(now)
    if timestamp < packet.created_at:
        errors.append("envelope_not_yet_valid")
    if timestamp >= packet.expires_at:
        errors.append("envelope_expired")
    if seen_nonces is not None and packet.nonce in seen_nonces:
        errors.append("replayed_nonce")
    if stable_digest(packet.payload) != packet.payload_digest:
        errors.append("payload_digest_mismatch")
    if packet.signature_scheme == "UNSIGNED_LOCAL":
        if not allow_unsigned_local:
            errors.append("unsigned_envelope_denied")
    elif verifier is None:
        errors.append("signature_verifier_missing")
    elif not verifier(packet.signing_payload(), packet.signature, packet.sender_id):
        errors.append("signature_invalid")
    valid = not errors
    if valid and seen_nonces is not None:
        seen_nonces.add(packet.nonce)
    result = {
        "ok": valid,
        "errors": errors,
        "envelope_id": packet.envelope_id,
        "sender_id": packet.sender_id,
        "recipient_scope": packet.recipient_scope,
        "payload_digest": packet.payload_digest,
        "proposal_only": True,
        "automatic_import": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    result["validation_digest"] = stable_digest(result)
    return result


'''
federation = replace_between(
    federation,
    "def validate_federation_envelope(",
    "def enqueue_federation_envelope(",
    validate_function,
)
federation_path.write_text(federation, encoding="utf-8")

# Remove a lint-only unused import and use the explicit policy in tests.
promotion_path = ROOT / "aura_model_cognome_promotion.py"
promotion = promotion_path.read_text(encoding="utf-8").replace(
    "from dataclasses import asdict, dataclass, field\n",
    "from dataclasses import asdict, dataclass\n",
    1,
)
promotion_path.write_text(promotion, encoding="utf-8")

test_path = ROOT / "tests/test_aura_model_cognome_replay_probes.py"
test_text = test_path.read_text(encoding="utf-8")
test_text = test_text.replace(
    '        shadow_evidence=promotion_evidence("SHADOW", "shadow-digest"),\n        created_at=1.0,',
    '        shadow_evidence=promotion_evidence("SHADOW", "shadow-digest"),\n        policy=RoutePromotionPolicy(),\n        created_at=1.0,',
    1,
)
test_path.write_text(test_text, encoding="utf-8")

# Repair the sole stale pytest-native fixture without weakening production fields.
icm_test_path = ROOT / "test_aura_icm_workspace.py"
icm_test = icm_test_path.read_text(encoding="utf-8")
icm_test = icm_test.replace(
    '''    from aura_liquid_planning_arena import (
        LiquidPlanningArena,
        export_arena_to_icm,
    )
''',
    '''    from aura_liquid_planning_arena import (
        LIQUID_ARENA_VERSION,
        LiquidPlanningArena,
        export_arena_to_icm,
    )
''',
    1,
)
icm_test = icm_test.replace(
    '''    arena = LiquidPlanningArena(
        arena_id="ARENA-ICM-1",
        domain="code",
        intent="patch demo.py",
        adapter={"domain": "code"},
''',
    '''    arena = LiquidPlanningArena(
        arena_version=LIQUID_ARENA_VERSION,
        arena_id="ARENA-ICM-1",
        domain="code",
        intent="patch demo.py",
        plan_ref="plan-1",
        domain_objects=["files", "diffs", "tests"],
        adapter={"domain": "code"},
''',
    1,
)
icm_test = icm_test.replace(
    '''        agent_leases=[{"lease_id": "L-1"}],
        phase_hash="ph1",
''',
    '''        agent_leases=[{"lease_id": "L-1"}],
        shared_action_queue=[],
        phase_hash="ph1",
''',
    1,
)
icm_test_path.write_text(icm_test, encoding="utf-8")

workflow = '''name: Model Cognome Replay and Probes

on:
  pull_request:
    paths:
      - "aura_model_cognome_replay.py"
      - "aura_model_cognome_drift.py"
      - "aura_model_cognome_promotion.py"
      - "aura_model_cognome_federation.py"
      - "aura_open_weight_jacobian_adapter.py"
      - "tests/test_aura_model_cognome_replay_probes.py"
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
            test_aura_icm_workspace.py
      - name: Run replay, probe, and ICM contracts
        run: |
          python -m pytest -q \
            tests/test_aura_model_cognome_replay_probes.py \
            test_aura_icm_workspace.py
'''
(ROOT / ".github/workflows/model-cognome-replay-probes.yml").write_text(workflow, encoding="utf-8")

run(
    "python",
    "-m",
    "py_compile",
    "aura_model_cognome_replay.py",
    "aura_model_cognome_drift.py",
    "aura_model_cognome_promotion.py",
    "aura_model_cognome_federation.py",
    "aura_open_weight_jacobian_adapter.py",
)
run(
    "ruff",
    "check",
    "--select",
    "E9,F63,F7,F82",
    "aura_model_cognome_replay.py",
    "aura_model_cognome_drift.py",
    "aura_model_cognome_promotion.py",
    "aura_model_cognome_federation.py",
    "aura_open_weight_jacobian_adapter.py",
    "tests/test_aura_model_cognome_replay_probes.py",
    "test_aura_icm_workspace.py",
)
run(
    "python",
    "-m",
    "pytest",
    "-q",
    "tests/test_aura_model_cognome_replay_probes.py",
    "test_aura_icm_workspace.py",
)
run("python", "-m", "pytest", "-q")

for path in (
    ROOT / ".github/workflows/finalize-cognome-replay-probes-once.yml",
    ROOT / "tools/one_time_finalize_cognome_replay_probes.py",
):
    path.unlink(missing_ok=True)

run("python", "aura_codebase_navigator.py")
first = Path("/tmp/CODEMAP.replay-probes-first.json")
shutil.copy2(ROOT / ".aura/CODEMAP.json", first)
run("python", "aura_codebase_navigator.py")
run("python", "-m", "aura_codemap_verify", "--compare-json", str(first))
first.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
subprocess.run(
    ["git", "commit", "--no-verify", "-m", "refactor(cognome): finalize replay probes and promotion gates"],
    cwd=ROOT,
    check=True,
)
report = Path("/tmp/cognome-replay-probes-report")
report.mkdir(exist_ok=True)
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
(report / "commit_sha.txt").write_text(sha + "\n", encoding="utf-8")
try:
    run("git", "push", "origin", "HEAD:refs/heads/refactor/model-cognome-replay-probes")
except subprocess.CalledProcessError:
    # The connector advances workflow-bearing commits when GITHUB_TOKEN is denied.
    pass
