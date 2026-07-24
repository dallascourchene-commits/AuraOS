#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH='refactor/unified-memory-continuity'
TRANSPORT_REF='refs/remotes/origin/main'
TRANSPORT_SHA256='76e6cde1d76beb2f916a39f3a9a176ee287f3887038226f89f527986c34d6606'
: "${EVENT_HEAD:?EVENT_HEAD is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

PAYLOAD_FILE="${RUNNER_TEMP}/umc-final5-payload.txt"

test "$(git rev-parse HEAD)" = "$EVENT_HEAD"
test -z "$(git status --porcelain=v1)"

: > "$PAYLOAD_FILE"
for number in $(seq -w 1 21); do
  git show "${TRANSPORT_REF}:.github/umc_final5_payload/part-${number}" >> "$PAYLOAD_FILE"
done
export PAYLOAD_FILE TRANSPORT_SHA256

python - <<'PY'
import base64
import hashlib
import json
import os
from pathlib import Path
import zlib

payload_path = Path(os.environ['PAYLOAD_FILE'])
encoded = payload_path.read_text(encoding='utf-8')
if hashlib.sha256(encoded.encode('utf-8')).hexdigest() != os.environ['TRANSPORT_SHA256']:
    raise SystemExit('verified transport hash mismatch')

payload = json.loads(zlib.decompress(base64.b64decode(encoded, validate=True)))
final_hashes = {
    'aura_unified_memory_continuity.py': '933b5f4962a33a0aad13bb0979de98bd86032d35ebce1245cb75a75536e12af3',
    'tests/test_aura_unified_memory_continuity.py': '4793480ccc76a6216983a533ef1dc7aab33e5ddd25f8b41a25c7eba40cfb70d1',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY.md': '262b2207468a918b196de925e46792146ffc7e97a46f5ced88d3e8d80c6614cd',
    'docs/AURA_UNIFIED_MEMORY_CONTINUITY_VERIFICATION.md': '7844267632cfba956817f1799e8095e7d5eefd51f087b73c8101281ed0beb4ea',
    '.aura/waboose_requests/unified_memory_continuity.v1.json': '9d9b193e206bd24d94a3592f8bd3d78da88241dece7da4c557a1bcc30691e2d3',
}
records = payload.get('files')
if payload.get('version') != 'FINAL5' or not isinstance(records, dict) or set(records) != set(final_hashes):
    raise SystemExit('verified payload identity or path set mismatch')

for relative, expected in final_hashes.items():
    content = records[relative]
    if not isinstance(content, str):
        raise SystemExit(f'non-text payload: {relative}')
    data = content.encode('utf-8')
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f'final file hash mismatch: {relative}')
    target = Path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

actual = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in final_hashes}
if actual != final_hashes:
    raise SystemExit(f'materialized file hash mismatch: {actual}')
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
  git fetch -q --no-tags origin "refs/heads/${TARGET_BRANCH}:refs/remotes/origin/${TARGET_BRANCH}"
  latest="$(git rev-parse "origin/${TARGET_BRANCH}")"
  if [ "$latest" != "$EVENT_HEAD" ]; then
    git merge-base --is-ancestor "$EVENT_HEAD" "$latest"
    git diff --name-only "$EVENT_HEAD" "$latest" > "${RUNNER_TEMP}/remote-movement-paths.txt"
    python - <<'PY'
import os
from pathlib import Path

allowed = {
    '.aura/CODEMAP.json',
    '.aura/CODEMAP.md',
    'topology_map.json',
    'Aura_Memory/live_topology_ast.json',
}
movement_file = Path(os.environ['RUNNER_TEMP']) / 'remote-movement-paths.txt'
paths = set(movement_file.read_text(encoding='utf-8').splitlines())
unexpected = paths - allowed
if unexpected:
    raise SystemExit(f'non-CODEMAP branch movement detected: {sorted(unexpected)}')
PY
    git rebase "$latest"
  fi
  if git push -q origin "HEAD:${TARGET_BRANCH}"; then
    exit 0
  fi
  sleep 10
done

echo 'unable to publish after CODEMAP-only retries' >&2
exit 1
