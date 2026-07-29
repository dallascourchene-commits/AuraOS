#!/usr/bin/env python3
"""Apply structural follow-up fixes after the verified PR240 patch set."""
from __future__ import annotations

import base64
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{relative}: expected one follow-up replacement site")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# The exact-head workflow starts from a depth-one checkout. Deepen only the
# checked-out head enough to prove the retained review-lesson merge ancestry;
# do not fetch every branch or tag.
token = os.environ.get("GH_TOKEN", "")
if not token:
    raise RuntimeError("GH_TOKEN is required to fetch bounded review ancestry")
auth_header = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
head_sha = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT,
    text=True,
).strip()
subprocess.run(
    [
        "git",
        "-c",
        f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth_header}",
        "fetch",
        "--deepen=1024",
        "--no-tags",
        "origin",
        head_sha,
    ],
    cwd=ROOT,
    check=True,
)


# Arena Attempt Archive: exact, unbounded-by-recency lookup for retained proof identity.
replace_once(
    "aura_arena_attempt_archive.py",
    """        return [self._decode_summary(row) for row in rows]

    def get(self, artifact_id: str) -> dict[str, Any] | None:
""",
    """        return [self._decode_summary(row) for row in rows]

    def find_by_result_value(
        self,
        *,
        workflow_id: str,
        route: str,
        result_key: str,
        result_value: Any,
    ) -> dict[str, Any] | None:
        if result_key not in {"runtime_proof_digest"}:
            raise ValueError("unsupported Attempt Archive result lookup key")
        rows = self._conn.execute(
            "SELECT artifact_id FROM arena_attempt_artifacts "
            "WHERE workflow_id=? AND route=? ORDER BY created_at DESC",
            (str(workflow_id), str(route)),
        ).fetchall()
        for row in rows:
            artifact = self.get(str(row[0]))
            result = (artifact or {}).get("result")
            if isinstance(result, dict) and result.get(result_key) == result_value:
                return artifact
        return None

    def get(self, artifact_id: str) -> dict[str, Any] | None:
""",
)

# Runtime proof rehydration: target the exact archive result rather than a summary
# field that summaries do not expose, and do not impose the summary row cap.
runtime_path = ROOT / "aura_bilateral_live_repair_foundry_service_runtime.py"
runtime = runtime_path.read_text(encoding="utf-8")
method_start = runtime.index("    def _runtime_proof(")
lookup_start = runtime.index("        for summary in self.attempt_archive.list(", method_start)
raise_start = runtime.index(
    '        raise BilateralLiveRepairError("runtime proof reference was not retained by Runtime Profile V2 replay")',
    lookup_start,
)
replacement = """        artifact = self.attempt_archive.find_by_result_value(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/runtime-replay",
            result_key="runtime_proof_digest",
            result_value=proof_ref,
        )
        result = dict((artifact or {}).get("result") or {})
        proof: Any = result.get("runtime_proof")
        proof_json = result.get("runtime_proof_json")
        if isinstance(proof_json, str) and proof_json:
            try:
                proof = json.loads(proof_json)
            except json.JSONDecodeError as exc:
                raise BilateralLiveRepairError("archived runtime proof JSON is invalid") from exc
        if (
            result.get("packet_digest") == packet.packet_digest
            and result.get("runtime_proof_digest") == proof_ref
            and isinstance(proof, Mapping)
            and self._runtime_proof_identity_matches(proof, proof_ref)
        ):
            normalized = dict(proof)
            self._runtime_proofs[proof_ref] = (packet.packet_id, normalized)
            self._runtime_proofs.move_to_end(proof_ref)
            while len(self._runtime_proofs) > 32:
                self._runtime_proofs.popitem(last=False)
            return normalized
"""
runtime_path.write_text(runtime[:lookup_start] + replacement + runtime[raise_start:], encoding="utf-8")

# Focused tests: valid Runtime V2 fixtures must carry the proof-bound candidate.
tests_path = ROOT / "tests/test_aura_bilateral_live_repair_foundry.py"
tests = tests_path.read_text(encoding="utf-8")
candidate_anchor = '        "repository_identity_unchanged": True,\n'
if tests.count(candidate_anchor) != 1:
    raise RuntimeError("runtime proof fixture identity anchor drifted")
tests = tests.replace(
    candidate_anchor,
    candidate_anchor + '        "runtime_candidate_id": "candidate",\n',
    1,
)


def replace_in_test(text: str, name: str, old: str, new: str) -> str:
    start = text.index(f"def {name}(")
    next_start = text.find("\ndef ", start + 1)
    end = len(text) if next_start < 0 else next_start
    block = text[start:end]
    if block.count(old) != 1:
        raise RuntimeError(f"{name}: candidate fixture replacement drifted")
    return text[:start] + block.replace(old, new, 1) + text[end:]


tests = replace_in_test(
    tests,
    "test_missing_negative_proof_blocks_repair_promotion",
    'candidate_digest=sha("candidate"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_failed_runtime_proof_rehydrates_as_rejected_attempt",
    'candidate_digest=sha("candidate"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_failed_hypothesis_cannot_repeat_across_service_restart",
    'candidate_digest=sha("candidate-1"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_failed_hypothesis_cannot_repeat_across_service_restart",
    'candidate_digest=sha("candidate-2"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_repair_attempt_budget_is_persistent_and_bounded",
    'candidate_digest=sha(f"candidate-{index}"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_repair_attempt_budget_is_persistent_and_bounded",
    'candidate_digest=sha("candidate-9"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests = replace_in_test(
    tests,
    "test_projection_rejects_cross_incident_or_unverified_u7_evidence",
    'candidate_digest=sha("candidate"),',
    'candidate_digest=_runtime_binding_digest("candidate"),',
)
tests_path.write_text(tests, encoding="utf-8")

# The exact-head Review Learning workflow must install the repository's declared
# runtime dependencies before collecting its retained regression suites.
replace_once(
    ".github/workflows/aura-review-learning.yml",
    """      - name: Install focused verifier dependencies
        run: python -m pip install --disable-pip-version-check pytest jsonschema ruff
""",
    """      - name: Install focused verifier dependencies
        run: |
          python -m pip install --disable-pip-version-check -r requirements.txt
          python -m pip install --disable-pip-version-check pytest jsonschema ruff pyyaml
""",
)
replace_once(
    ".github/workflows/aura-review-learning.yml",
    """          git checkout --detach FETCH_HEAD
          git -c http.https://github.com/.extraheader="AUTHORIZATION: basic $AUTH_HEADER" \
            fetch --depth=1 --no-tags origin \
            "$AURA_REVIEW_BASE_REF:refs/remotes/origin/$AURA_REVIEW_BASE_REF"
""",
    """          git checkout --detach FETCH_HEAD
          # Keep the exact-head checkout while fetching only the bounded ancestry
          # required to prove the retained review-lesson merge is an ancestor.
          git -c http.https://github.com/.extraheader="AUTHORIZATION: basic $AUTH_HEADER" \
            fetch --deepen=1024 --no-tags origin "$AURA_REVIEW_HEAD_SHA"
          git -c http.https://github.com/.extraheader="AUTHORIZATION: basic $AUTH_HEADER" \
            fetch --depth=1 --no-tags origin \
            "$AURA_REVIEW_BASE_REF:refs/remotes/origin/$AURA_REVIEW_BASE_REF"
""",
)
replace_once(
    ".github/workflows/aura-review-learning.yml",
    """          python scripts/aura_review_learning_architect_harness.py \
""",
    """          PYTHONPATH=. python scripts/aura_review_learning_architect_harness.py \
""",
)

print("PR240 structural follow-up fixes applied")
