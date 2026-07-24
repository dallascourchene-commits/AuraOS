#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH='refactor/unified-memory-continuity'
EXPECTED_HEAD='371e794a57dd37c8d293570b505ce4666340c217'
TRANSPORT_BRANCH='transport/umc-deep-review-20260724'
PAYLOAD_PREFIX='.aura/refactor_payloads/umc_deep_review_v2'
EVIDENCE_DIR="${RUNNER_TEMP}/umc-deep-review-evidence"
PAYLOAD_FILE="${RUNNER_TEMP}/umc-deep-payload.json"
WABOOSE_STATE="${RUNNER_TEMP}/umc-deep-waboose-state.json"
export AURA_WABOOSE_LEARNING_ROOT="${RUNNER_TEMP}/umc-deep-waboose-learning"

mkdir -p "$EVIDENCE_DIR"
test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
test -z "$(git status --porcelain=v1)"

git fetch --no-tags origin \
  "refs/heads/${TRANSPORT_BRANCH}:refs/remotes/origin/${TRANSPORT_BRANCH}"
: > "$PAYLOAD_FILE"
for number in 01 02 03 04 05 06 07 08; do
  git show "origin/${TRANSPORT_BRANCH}:${PAYLOAD_PREFIX}.part-${number}" >> "$PAYLOAD_FILE"
done
sha256sum "$PAYLOAD_FILE" | tee "$EVIDENCE_DIR/payload.sha256"
test "$(cut -d' ' -f1 "$EVIDENCE_DIR/payload.sha256")" = \
  'f880ce531b817d95ade8e1f3dd02ac377eb3fbaf5222c052a45a594c0ed33c46'

python - <<'PY'
import base64
import hashlib
import json
import os
from pathlib import Path
import zlib

runner_temp = Path(os.environ['RUNNER_TEMP'])
payload = json.loads((runner_temp / 'umc-deep-payload.json').read_text(encoding='utf-8'))
expected = {
    'aura_unified_memory_continuity.py',
    'tests/test_aura_unified_memory_continuity.py',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md',
}
if payload.get('version') != 'AURA_UMC_DEEP_REVIEW_PAYLOAD_V2':
    raise SystemExit('unsupported deep-review payload version')
records = payload.get('files')
if not isinstance(records, dict) or set(records) != expected:
    raise SystemExit('deep-review payload path set differs from reviewed scope')
receipt = {}
for relative, record in sorted(records.items()):
    compressed = base64.b64decode(record['zlib_base64'], validate=True)
    content = zlib.decompress(compressed)
    digest = hashlib.sha256(content).hexdigest()
    if digest != record['sha256']:
        raise SystemExit(f'hash mismatch for {relative}')
    target = Path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f'.{target.name}.deep-review.tmp')
    temporary.write_bytes(content)
    temporary.replace(target)
    receipt[relative] = digest
(runner_temp / 'umc-deep-review-evidence' / 'file_hashes.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

git diff --check
python -m py_compile \
  aura_unified_memory_continuity.py \
  tests/test_aura_unified_memory_continuity.py
python - <<'PY'
import ast
from pathlib import Path
for path in (
    'aura_unified_memory_continuity.py',
    'tests/test_aura_unified_memory_continuity.py',
):
    ast.parse(Path(path).read_text(encoding='utf-8'), filename=path, feature_version=(3, 10))
PY
python -m compileall -q . 2>&1 | tee "$EVIDENCE_DIR/compileall.log"

ruff check \
  aura_unified_memory_continuity.py \
  tests/test_aura_unified_memory_continuity.py \
  2>&1 | tee "$EVIDENCE_DIR/ruff.log"
bandit -q -ll aura_unified_memory_continuity.py \
  2>&1 | tee "$EVIDENCE_DIR/bandit.log"

python -m pytest -q \
  tests/test_aura_unified_memory_continuity.py \
  tests/test_aura_relationship_compass_finalization.py \
  --junitxml="$EVIDENCE_DIR/regressions.xml" \
  2>&1 | tee "$EVIDENCE_DIR/pytest.log"
grep -Eq '65 passed' "$EVIDENCE_DIR/pytest.log"

python aura_coding_waboose_cli.py \
  --repo-root . \
  --state-file "$WABOOSE_STATE" \
  run \
  --request .aura/waboose_requests/unified_memory_continuity.v1.json \
  > "$EVIDENCE_DIR/waboose.json"
python - <<'PY'
import json
import os
from pathlib import Path
result = json.loads(
    (Path(os.environ['RUNNER_TEMP']) / 'umc-deep-review-evidence' / 'waboose.json').read_text(encoding='utf-8')
)
assert result.get('ok') is True, result
assert not (result.get('findings') or []), result
assert not (result.get('deterministic_findings') or []), result
assert result.get('production_mutation') is False, result
assert result.get('automatic_fix') is False, result
PY

python aura_codebase_navigator.py > "$EVIDENCE_DIR/codemap-generation.log" 2>&1
test -s .aura/CODEMAP.json
test -s .aura/CODEMAP.md
test -s topology_map.json
test -s Aura_Memory/live_topology_ast.json
git diff --check

git config user.name 'AuraOS Deep Review Bot'
git config user.email 'actions@users.noreply.github.com'
git add \
  aura_unified_memory_continuity.py \
  tests/test_aura_unified_memory_continuity.py \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY.md \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md \
  .aura/CODEMAP.json \
  .aura/CODEMAP.md \
  topology_map.json
git add -f Aura_Memory/live_topology_ast.json
git diff --cached --check
git diff --cached --name-only > "$EVIDENCE_DIR/staged_paths.txt"
python - <<'PY'
import os
from pathlib import Path
changed = set(
    (Path(os.environ['RUNNER_TEMP']) / 'umc-deep-review-evidence' / 'staged_paths.txt')
    .read_text(encoding='utf-8')
    .splitlines()
)
required = {
    'aura_unified_memory_continuity.py',
    'tests/test_aura_unified_memory_continuity.py',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md',
}
allowed = required | {
    '.aura/CODEMAP.json',
    '.aura/CODEMAP.md',
    'topology_map.json',
    'Aura_Memory/live_topology_ast.json',
}
if not required.issubset(changed):
    raise SystemExit(f'missing reviewed paths: {sorted(required - changed)}')
if not changed.issubset(allowed):
    raise SystemExit(f'unexpected staged paths: {sorted(changed - allowed)}')
PY

git commit -m 'fix: harden continuity identity and governed evidence'
git push origin "HEAD:${TARGET_BRANCH}"
git rev-parse HEAD | tee "$EVIDENCE_DIR/materialized_commit.txt"
