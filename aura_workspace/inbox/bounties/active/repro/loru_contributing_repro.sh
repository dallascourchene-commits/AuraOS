#!/usr/bin/env bash
set -euo pipefail
expected="a2d332c790ea88bb2139c386d913195e7c8dce9e"
actual="$(git rev-parse HEAD)"
test "$actual" = "$expected"
test ! -e CONTRIBUTING.md
printf '%s\n' "REPRO_PASS: CONTRIBUTING.md required by bounty #19 is absent at $expected"
