#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH='refactor/unified-memory-continuity'
TRANSPORT_COMMIT='1de0f438b330ef91bfc99cead2d288d003181e22'
: "${EVENT_HEAD:?EVENT_HEAD is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

PAYLOAD_FILE="${RUNNER_TEMP}/umc-five-file-payload.txt"

test "$(git rev-parse HEAD)" = "$EVENT_HEAD"
test -z "$(git status --porcelain=v1)"

git fetch --no-tags origin "$TRANSPORT_COMMIT"
: > "$PAYLOAD_FILE"
for number in 01 02 03; do
  git show "$TRANSPORT_COMMIT:.aura/refactor_payloads/umc_deep_review_v2/part-${number}" >> "$PAYLOAD_FILE"
done
export PAYLOAD_FILE

python - <<'PY'
import base64
import hashlib
import json
import os
from pathlib import Path
import zlib

payload = json.loads(
    zlib.decompress(
        base64.b64decode(Path(os.environ['PAYLOAD_FILE']).read_text(encoding='utf-8'), validate=True)
    )
)
payload_hashes = {
    'aura_unified_memory_continuity.py': 'c0240ccc01b5b54988f2859a81c3379b920fd3acca0b42d6e1fe739d40c50ae1',
    'tests/test_aura_unified_memory_continuity.py': '28e9f7683ea491aa43c321decc41eb4dcb3d806f18633fc530c5cebab74d04e8',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md': '262b2207468a918b196de925e46792146ffc7e97a46f5ced88d3e8d80c6614cd',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md': '7844267632cfba956817f1799e8095e7d5eefd51f087b73c8101281ed0beb4ea',
    '.aura/waboose_requests/unified_memory_continuity.v1.json': '9d9b193e206bd24d94a3592f8bd3d78da88241dece7da4c557a1bcc30691e2d3',
}
records = payload.get('files')
if payload.get('version') != 'AURA_UMC_DEEP_REVIEW_PAYLOAD_V2' or set(records or {}) != set(payload_hashes):
    raise SystemExit('reviewed payload identity or path set mismatch')
for relative, expected in payload_hashes.items():
    content = records[relative].get('content')
    if not isinstance(content, str):
        raise SystemExit(f'non-text payload: {relative}')
    data = content.encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected or digest != records[relative].get('sha256'):
        raise SystemExit(f'payload hash mismatch: {relative}')
    target = Path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

module_path = Path('aura_unified_memory_continuity.py')
module = module_path.read_text(encoding='utf-8')
import_anchor = 'from enum import Enum\nimport math\n'
dynamic_load = 'decoded = __import__("json").loads(normalized)'
if module.count(import_anchor) != 1 or module.count(dynamic_load) != 1:
    raise SystemExit('namespace repair anchors are ambiguous')
module = module.replace(import_anchor, 'from enum import Enum\nimport json\nimport math\n', 1)
module = module.replace(dynamic_load, 'decoded = json.loads(normalized)', 1)
module_path.write_text(module, encoding='utf-8')

tests_path = Path('tests/test_aura_unified_memory_continuity.py')
tests = tests_path.read_text(encoding='utf-8')
if 'test_module_avoids_dynamic_namespace_injection' in tests:
    raise SystemExit('namespace regression unexpectedly present')
tests += '''\n\ndef test_module_avoids_dynamic_namespace_injection() -> None:\n    with open("aura_unified_memory_continuity.py", encoding="utf-8") as source_file:\n        source = source_file.read()\n    assert "__import__(" not in source\n'''
tests_path.write_text(tests, encoding='utf-8')

final_hashes = {
    'aura_unified_memory_continuity.py': '933b5f4962a33a0aad13bb0979de98bd86032d35ebce1245cb75a75536e12af3',
    'tests/test_aura_unified_memory_continuity.py': '4793480ccc76a6216983a533ef1dc7aab33e5ddd25f8b41a25c7eba40cfb70d1',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md': '262b2207468a918b196de925e46792146ffc7e97a46f5ced88d3e8d80c6614cd',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md': '7844267632cfba956817f1799e8095e7d5eefd51f087b73c8101281ed0beb4ea',
    '.aura/waboose_requests/unified_memory_continuity.v1.json': '9d9b193e206bd24d94a3592f8bd3d78da88241dece7da4c557a1bcc30691e2d3',
}
actual = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in final_hashes}
if actual != final_hashes:
    raise SystemExit(f'final hash mismatch: {actual}')
PY

python -m py_compile aura_unified_memory_continuity.py tests/test_aura_unified_memory_continuity.py
git diff --check

git add \
  aura_unified_memory_continuity.py \
  tests/test_aura_unified_memory_continuity.py \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY.md \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md \
  .aura/waboose_requests/unified_memory_continuity.v1.json

git diff --cached --name-only | sort > "${RUNNER_TEMP}/actual-paths.txt"
printf '%s\n' \
  .aura/waboose_requests/unified_memory_continuity.v1.json \
  aura_unified_memory_continuity.py \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY.md \
  docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md \
  tests/test_aura_unified_memory_continuity.py \
  | sort > "${RUNNER_TEMP}/expected-paths.txt"
diff -u "${RUNNER_TEMP}/expected-paths.txt" "${RUNNER_TEMP}/actual-paths.txt"

git config user.name 'AuraOS Verified Patch Bot'
git config user.email 'actions@users.noreply.github.com'
git commit -m 'fix: apply verified five-file continuity patch'

for attempt in $(seq 1 12); do
  git fetch --no-tags origin "refs/heads/${TARGET_BRANCH}:refs/remotes/origin/${TARGET_BRANCH}"
  latest="$(git rev-parse "origin/${TARGET_BRANCH}")"
  if [ "$latest" != "$EVENT_HEAD" ]; then
    git merge-base --is-ancestor "$EVENT_HEAD" "$latest"
    git diff --name-only "$EVENT_HEAD" "$latest" > "${RUNNER_TEMP}/remote-movement-paths.txt"
    python - <<'PY'
from pathlib import Path
allowed = {
    '.aura/CODEMAP.json',
    '.aura/CODEMAP.md',
    'topology_map.json',
    'Aura_Memory/live_topology_ast.json',
}
movement_file = Path(__import__('os').environ['RUNNER_TEMP']) / 'remote-movement-paths.txt'
paths = set(movement_file.read_text(encoding='utf-8').splitlines())
unexpected = paths - allowed
if unexpected:
    raise SystemExit(f'non-CODEMAP branch movement detected: {sorted(unexpected)}')
PY
    git rebase "$latest"
  fi
  if git push origin "HEAD:${TARGET_BRANCH}"; then
    exit 0
  fi
  sleep 10
done

echo 'unable to publish after CODEMAP-only retries' >&2
exit 1
