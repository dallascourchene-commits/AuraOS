#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH='refactor/unified-memory-continuity'
EXPECTED_HEAD='__EXPECTED_HEAD__'
PAYLOAD_PREFIX='.aura/refactor_payloads/umc_deep_review_v2'
export EVIDENCE_DIR="${RUNNER_TEMP}/umc-deep-review-v2"
PAYLOAD_FILE="${EVIDENCE_DIR}/payload.encoded"
export PAYLOAD_FILE
WABOOSE_STATE="${EVIDENCE_DIR}/waboose-state.json"
export AURA_WABOOSE_LEARNING_ROOT="${EVIDENCE_DIR}/waboose-learning"
mkdir -p "$EVIDENCE_DIR"

test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
test -z "$(git status --porcelain=v1)"
: > "$PAYLOAD_FILE"
for number in 01 02 03; do
  git show "${TRANSPORT_COMMIT}:${PAYLOAD_PREFIX}/part-${number}" >> "$PAYLOAD_FILE"
done
test "$(sha256sum aura_unified_memory_continuity.py | awk '{print $1}')" = \
  'bb5c0c50e62b8edbb4cbdad4f9810709f67adf7866fcd8b0700eda334a030ade'
test "$(sha256sum tests/test_aura_unified_memory_continuity.py | awk '{print $1}')" = \
  'edddf3af030fd5e4cdeb8bc0bb0c4b2751e3dc7857068ba46c28c5bd905d19ee'
test "$(sha256sum docs/AURA_UNIFIED_MEMORY_CONTINUITY.md | awk '{print $1}')" = \
  '5d3c0736b04c4fd3b0dbee54964e43387dad7949a8a175d1d333f4e5c4962603'
test "$(sha256sum docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md | awk '{print $1}')" = \
  '0c72fcc9ff1f9bc3c9f0847d059b9d411ebd041bc3bb00e4698fcef35d8505c5'
test "$(sha256sum .aura/waboose_requests/unified_memory_continuity.v1.json | awk '{print $1}')" = \
  '0a3206477ffc6d1f1190a97245b9a4a41b14a2dad27b2bfc81229c3e5294bf34'

python - <<'PY'
import base64
import hashlib
import json
from pathlib import Path
import os
import zlib
encoded = (Path(os.environ['PAYLOAD_FILE'])).read_text(encoding='utf-8')
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
(Path(os.environ['EVIDENCE_DIR']) / 'payload-file-hashes.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

module_path = Path('aura_unified_memory_continuity.py')
module = module_path.read_text(encoding='utf-8')
old_import = 'from enum import Enum\nimport math\n'
new_import = 'from enum import Enum\nimport json\nimport math\n'
if module.count(old_import) != 1:
    raise SystemExit('module import insertion point is ambiguous')
module = module.replace(old_import, new_import, 1)
old_dynamic = 'decoded = __import__("json").loads(normalized)'
if module.count(old_dynamic) != 1:
    raise SystemExit('dynamic JSON import repair point is ambiguous')
module = module.replace(old_dynamic, 'decoded = json.loads(normalized)', 1)
module_path.write_text(module, encoding='utf-8')

tests_path = Path('tests/test_aura_unified_memory_continuity.py')
tests = tests_path.read_text(encoding='utf-8')
test_name = 'test_module_avoids_dynamic_namespace_injection'
if test_name in tests:
    raise SystemExit('namespace-injection regression already exists unexpectedly')
tests += '''\n\ndef test_module_avoids_dynamic_namespace_injection() -> None:\n    with open("aura_unified_memory_continuity.py", encoding="utf-8") as source_file:\n        source = source_file.read()\n    assert "__import__(" not in source\n'''
tests_path.write_text(tests, encoding='utf-8')

expected = {
    'aura_unified_memory_continuity.py': '933b5f4962a33a0aad13bb0979de98bd86032d35ebce1245cb75a75536e12af3',
    'tests/test_aura_unified_memory_continuity.py': '4793480ccc76a6216983a533ef1dc7aab33e5ddd25f8b41a25c7eba40cfb70d1',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md': '262b2207468a918b196de925e46792146ffc7e97a46f5ced88d3e8d80c6614cd',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md': '7844267632cfba956817f1799e8095e7d5eefd51f087b73c8101281ed0beb4ea',
    '.aura/waboose_requests/unified_memory_continuity.v1.json': '9d9b193e206bd24d94a3592f8bd3d78da88241dece7da4c557a1bcc30691e2d3',
}
actual = {
    path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for path in expected
}
if actual != expected:
    raise SystemExit(f'final bounded file hashes differ: {actual}')
(Path(os.environ['EVIDENCE_DIR']) / 'final-file-hashes.json').write_text(
    json.dumps(actual, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
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
grep -Eq '66 passed' "$EVIDENCE_DIR/pytest.log"

python - <<'PY' 2>&1 | tee "$EVIDENCE_DIR/pvm-hard-gate.log"
from pathlib import Path
from pvm_arch_checker import PVMArchChecker
violations = PVMArchChecker(Path('.')).run()
hard = [
    violation
    for violation in violations
    if violation.rule in {'SYNTAX_ERROR', 'WILDCARD_IMPORT', 'CIRCULAR_IMPORT', 'NAMESPACE_INJECTION'}
]
print(f'hard_violations={hard}')
if hard:
    raise SystemExit('Aura PVM hard architecture gate failed')
PY

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
  --objective "Verify bounded deep-review repairs for evidence saturation, canonical Model Cognome identity, P0 runtime binding, Relationship Experience/QDKT governance identity, canonical JSON key safety, and explicit namespace-safe imports without a parallel owner or mutation authority." \
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
unexpected = changed - allowed
if not required.issubset(changed):
    raise SystemExit(f'missing reviewed paths: {sorted(required - changed)}')
if unexpected:
    raise SystemExit(f'unexpected staged paths: {sorted(unexpected)}')
PY

git commit -m 'fix: close deep continuity and namespace review gaps'
git push origin "HEAD:${TARGET_BRANCH}"
git rev-parse HEAD | tee "$EVIDENCE_DIR/materialized-commit.txt"
