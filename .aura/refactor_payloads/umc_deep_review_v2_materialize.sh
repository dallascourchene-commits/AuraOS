#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH='refactor/unified-memory-continuity'
EXPECTED_HEAD='968f417cf55895ec788d89c0a97f37e40cf0612a'
EXPECTED_PARENT='096c02fac506b669dbee9c013f9dab270cf4b973'
PAYLOAD_DIR='Aura_Sandbox/umc_deep_review_payload_v2'
export EVIDENCE_DIR="${RUNNER_TEMP}/umc-deep-review-v2"
WABOOSE_STATE="${EVIDENCE_DIR}/waboose-state.json"
export AURA_WABOOSE_LEARNING_ROOT="${EVIDENCE_DIR}/waboose-learning"
mkdir -p "$EVIDENCE_DIR"

test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
test "$(git rev-parse HEAD^)" = "$EXPECTED_PARENT"
test -z "$(git status --porcelain=v1)"
git diff --name-only HEAD^ HEAD | sort > "${RUNNER_TEMP}/payload-paths.txt"
printf '%s\n' \
  Aura_Sandbox/umc_deep_review_payload_v2/part-01 \
  Aura_Sandbox/umc_deep_review_payload_v2/part-02 \
  Aura_Sandbox/umc_deep_review_payload_v2/part-03 \
  | sort > "${RUNNER_TEMP}/expected-payload-paths.txt"
diff -u "${RUNNER_TEMP}/expected-payload-paths.txt" "${RUNNER_TEMP}/payload-paths.txt"
test "$(sha256sum aura_unified_memory_continuity.py | awk '{print $1}')" = \
  'bb5c0c50e62b8edbb4cbdad4f9810709f67adf7866fcd8b0700eda334a030ade'
test "$(sha256sum tests/test_aura_unified_memory_continuity.py | awk '{print $1}')" = \
  'edddf3af030fd5e4cdeb8bc0bb0c4b2751e3dc7857068ba46c28c5bd905d19ee'

python - <<'PY'
import base64
import hashlib
import json
from pathlib import Path
import os
import shutil
import zlib
payload_dir = Path('Aura_Sandbox/umc_deep_review_payload_v2')
parts = sorted(payload_dir.glob('part-*'))
encoded = ''.join(part.read_text(encoding='utf-8') for part in parts)
payload = json.loads(zlib.decompress(base64.b64decode(encoded, validate=True)))
expected = {
    'aura_unified_memory_continuity.py': 'c0240ccc01b5b54988f2859a81c3379b920fd3acca0b42d6e1fe739d40c50ae1',
    'tests/test_aura_unified_memory_continuity.py': '28e9f7683ea491aa43c321decc41eb4dcb3d806f18633fc530c5cebab74d04e8',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md': '262b2207468a918b196de925e46792146ffc7e97a46f5ced88d3e8d80c6614cd',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md': '7844267632cfba956817f1799e8095e7d5eefd51f087b73c8101281ed0beb4ea',
    '.aura/waboose_requests/unified_memory_continuity.v1.json': '9d9b193e206bd24d94a3592f8bd3d78da88241dece7da4c557a1bcc30691e2d3',
}
if payload.get('version') != 'AURA_UMC_DEEP_REVIEW_PAYLOAD_V2':
    raise SystemExit('unsupported payload version')
records = payload.get('files')
if not isinstance(records, dict) or set(records) != set(expected):
    raise SystemExit('payload path set differs from reviewed scope')
receipt = {}
for relative, record in sorted(records.items()):
    content = record.get('content')
    if not isinstance(content, str):
        raise SystemExit(f'non-text payload for {relative}')
    data = content.encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    if digest != record.get('sha256') or digest != expected[relative]:
        raise SystemExit(f'hash mismatch for {relative}')
    target = Path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f'.{target.name}.reviewed.tmp')
    temporary.write_bytes(data)
    temporary.replace(target)
    receipt[relative] = digest
(Path(os.environ['EVIDENCE_DIR']) / 'file-hashes.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
shutil.rmtree(payload_dir)
PY

git diff --check
python -m pip install --upgrade pip > "$EVIDENCE_DIR/pip-upgrade.log" 2>&1
python -m pip install -r requirements.txt 'pytest>=8,<9' jsonschema ruff bandit \
  > "$EVIDENCE_DIR/install.log" 2>&1

python - <<'PY' 2>&1 | tee "$EVIDENCE_DIR/compile-all.log"
from pathlib import Path
import py_compile
failures = []
count = 0
for path in Path('.').rglob('*.py'):
    if any(part in {'.git', '.venv', 'venv', '__pycache__'} for part in path.parts):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
        count += 1
    except Exception as exc:
        failures.append((str(path), str(exc)))
print(f'compiled={count} failures={len(failures)}')
if failures:
    raise SystemExit('\n'.join(f'{path}: {exc}' for path, exc in failures))
PY

ruff check aura_unified_memory_continuity.py tests/test_aura_unified_memory_continuity.py \
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
  > "$EVIDENCE_DIR/waboose-result.json"
python - <<'PY'
import json
import os
from pathlib import Path
result = json.loads((Path(os.environ['EVIDENCE_DIR']) / 'waboose-result.json').read_text(encoding='utf-8'))
assert result.get('ok') is True, result
assert not (result.get('findings') or []), result
assert not (result.get('deterministic_findings') or []), result
assert result.get('production_mutation') is False, result
assert result.get('automatic_fix') is False, result
PY

python scripts/aura_architecture_harness.py \
  --repo-root . prepare \
  --venv "${RUNNER_TEMP}/umc-deep-review-venv" \
  --install-requirements > "$EVIDENCE_DIR/harness-prepare.log" 2>&1
python scripts/aura_architecture_harness.py \
  --repo-root . doctor \
  --venv "${RUNNER_TEMP}/umc-deep-review-venv" \
  > "$EVIDENCE_DIR/harness-doctor.log" 2>&1
python scripts/aura_architecture_harness.py \
  --repo-root . run \
  --venv "${RUNNER_TEMP}/umc-deep-review-venv" \
  --objective "Verify deep-review repairs for evidence saturation, canonical Model Cognome identity, P0 runtime binding, Relationship Experience/QDKT governance identity, and canonical JSON key safety without a parallel owner or mutation authority." \
  --combine-with Connectome "Relational Synthesis" Atlas \
  --atlas-profile MINIMAL \
  --output-dir "$EVIDENCE_DIR/harness-run" \
  > "$EVIDENCE_DIR/harness-run.log" 2>&1
python - <<'PY'
import json
import os
from pathlib import Path
summary = json.loads((Path(os.environ['EVIDENCE_DIR']) / 'harness-run' / 'harness_summary.json').read_text(encoding='utf-8'))
assert summary.get('ok') is True, summary
assert summary.get('production_mutation') is False, summary
assert summary.get('human_review_required') is True, summary
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
  .aura/waboose_requests/unified_memory_continuity.v1.json \
  .aura/CODEMAP.json \
  .aura/CODEMAP.md \
  topology_map.json
git add -f Aura_Memory/live_topology_ast.json
git add -u -- Aura_Sandbox/umc_deep_review_payload_v2
git diff --cached --check
git diff --cached --name-only > "$EVIDENCE_DIR/staged-paths.txt"
python - <<'PY'
import os
from pathlib import Path
changed = set((Path(os.environ['EVIDENCE_DIR']) / 'staged-paths.txt').read_text().splitlines())
required = {
    'aura_unified_memory_continuity.py',
    'tests/test_aura_unified_memory_continuity.py',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md',
    '.aura/waboose_requests/unified_memory_continuity.v1.json',
}
allowed = required | {
    '.aura/CODEMAP.json', '.aura/CODEMAP.md', 'topology_map.json',
    'Aura_Memory/live_topology_ast.json',
}
payload = {p for p in changed if p.startswith('Aura_Sandbox/umc_deep_review_payload_v2/')}
unexpected = changed - allowed - payload
if not required.issubset(changed):
    raise SystemExit(f'missing reviewed paths: {sorted(required - changed)}')
if unexpected:
    raise SystemExit(f'unexpected staged paths: {sorted(unexpected)}')
PY

git commit -m 'fix: close deep unified continuity review gaps'
git push origin "HEAD:${TARGET_BRANCH}"
git rev-parse HEAD | tee "$EVIDENCE_DIR/materialized-commit.txt"
