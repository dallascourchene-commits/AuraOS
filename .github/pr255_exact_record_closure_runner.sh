#!/usr/bin/env bash
set -euo pipefail

BASE=879b5fb056b70d150b1646e082223330a36c2912
FROZEN=38946f117da77285c318747fee232c6a663179a9
BRANCH=refactor/intent-native-spatial-workspace-pr1

current="$(git rev-parse HEAD)"
test "$current" = "$FROZEN"
git fetch --no-tags origin "$BASE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"

python -m py_compile ../control/.github/pr255_exact_record_closure_patch.py
python ../control/.github/pr255_exact_record_closure_patch.py
git diff --check

mapfile -t changed < <(git diff --name-only | sort)
printf '%s\n' \
  aura_ephemeral_workspace_contracts.py \
  docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md \
  tests/test_aura_ephemeral_workspace_contracts.py \
  | sort > /tmp/pr255-expected.txt
printf '%s\n' "${changed[@]}" > /tmp/pr255-actual.txt
diff -u /tmp/pr255-expected.txt /tmp/pr255-actual.txt

python -m pip install --upgrade pip
python -m pip install pytest jsonschema ruff
export PYTHONPATH=.
python -m py_compile aura_ephemeral_workspace_contracts.py tests/test_aura_ephemeral_workspace_contracts.py
python -m pytest -q tests/test_aura_ephemeral_workspace_contracts.py | tee /tmp/pr255-pytest.txt
grep -Eq '^45 passed in ' /tmp/pr255-pytest.txt
python -m pytest --collect-only -q tests/test_aura_ephemeral_workspace_contracts.py | tee /tmp/pr255-collect.txt
grep -Eq '^45 tests collected in ' /tmp/pr255-collect.txt
ruff check --select F401,F821,F841 aura_ephemeral_workspace_contracts.py tests/test_aura_ephemeral_workspace_contracts.py
python - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

for name in (
    "aura_project_context_projection.schema.json",
    "aura_ephemeral_workspace_recipe.schema.json",
    "aura_multimodal_spatial_observation.schema.json",
):
    schema = json.loads((Path("schemas") / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
PY

mapfile -t final_changed < <(git diff --name-only "$BASE" -- | sort)
printf '%s\n' \
  .aura/refactor_objectives/intent_native_spatial_workspace_pr1.v1.json \
  .aura/waboose_requests/intent_native_spatial_workspace_pr1.v1.json \
  aura_ephemeral_workspace_contracts.py \
  docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md \
  schemas/aura_ephemeral_workspace_recipe.schema.json \
  schemas/aura_multimodal_spatial_observation.schema.json \
  schemas/aura_project_context_projection.schema.json \
  tests/test_aura_ephemeral_workspace_contracts.py \
  | sort > /tmp/pr255-final-expected.txt
printf '%s\n' "${final_changed[@]}" > /tmp/pr255-final-actual.txt
diff -u /tmp/pr255-final-expected.txt /tmp/pr255-final-actual.txt

git diff --exit-code "$BASE" -- \
  .aura/CODEMAP.json \
  .aura/CODEMAP.md \
  topology_map.json \
  Aura_Memory/live_topology_ast.json

test ! -e .github/workflows/pr255-exact-record-closure.yml
test ! -e .github/pr255_exact_record_closure_patch.py
test ! -e .github/pr255_exact_record_closure_runner.sh
test -z "$(git status --porcelain=v1 --untracked-files=all | grep -E 'CODEMAP|topology_map|live_topology_ast|pr255-exact-record-closure|pr255_exact_record_closure' || true)"

remote_head="$(git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
test "$remote_head" = "$FROZEN"

git config user.name 'AuraOS ARCH v2 Repair'
git config user.email 'actions@users.noreply.github.com'
git add \
  aura_ephemeral_workspace_contracts.py \
  docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md \
  tests/test_aura_ephemeral_workspace_contracts.py
git diff --cached --check
test "$(git diff --cached --name-only | wc -l)" -eq 3
git commit -m 'fix(pr1): close remaining exact-record admissions'

remote_head="$(git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
test "$remote_head" = "$FROZEN"
git push origin HEAD:"refs/heads/$BRANCH"
