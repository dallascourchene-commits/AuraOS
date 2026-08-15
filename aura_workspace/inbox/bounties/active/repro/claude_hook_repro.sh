#!/usr/bin/env bash
set -euo pipefail
expected="1aeae2adc82d33f971fd7731644348dcdd24b5a6"
actual="$(git rev-parse HEAD)"
test "$actual" = "$expected"
test ! -e hooks/block_destructive_commands.py
test ! -e hooks/test_block_destructive_commands.py
printf '%s\n' "REPRO_PASS: destructive-command PreToolUse guard and regression tests are absent at $expected"
