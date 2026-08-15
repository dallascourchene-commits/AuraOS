#!/usr/bin/env bash
set -euo pipefail
expected="2b9ed0e3169026e5c809bf563c1e3c71f1afc30e"
actual="$(git rev-parse HEAD)"
test "$actual" = "$expected"
test ! -e schemas/identify-response.schema.json
test ! -e schemas/care-response.schema.json
test ! -e sdk/typescript/index.ts
printf '%s\n' "REPRO_PASS: published JSON Schema and TypeScript app contracts are absent at $expected"
