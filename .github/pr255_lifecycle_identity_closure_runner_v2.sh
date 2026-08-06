#!/usr/bin/env bash
set -euo pipefail

BASE=879b5fb056b70d150b1646e082223330a36c2912
FROZEN=b9db528ee06e97040712aeae185bc4fce79ceb98
BRANCH=refactor/intent-native-spatial-workspace-pr1

current="$(git rev-parse HEAD)"
test "$current" = "$FROZEN"
git fetch --no-tags origin "$BASE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"

python ../control/.github/pr255_lifecycle_identity_closure_patch.py
python - <<'PY'
from pathlib import Path
path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
path.write_text(path.read_text(encoding="utf-8").rstrip() + "\n", encoding="utf-8")
PY
git diff --check

mapfile -t changed < <(git diff --name-only | sort)
printf '%s\n' \
  aura_ephemeral_workspace_contracts.py \
  docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md \
  schemas/aura_ephemeral_workspace_recipe.schema.json \
  tests/test_aura_ephemeral_workspace_contracts.py \
  | sort > /tmp/pr255-lifecycle-expected.txt
printf '%s\n' "${changed[@]}" > /tmp/pr255-lifecycle-actual.txt
diff -u /tmp/pr255-lifecycle-expected.txt /tmp/pr255-lifecycle-actual.txt

python -m pip install --upgrade pip
python -m pip install pytest jsonschema ruff
export PYTHONPATH=.
python -m py_compile aura_ephemeral_workspace_contracts.py tests/test_aura_ephemeral_workspace_contracts.py
python -m pytest -q tests/test_aura_ephemeral_workspace_contracts.py | tee /tmp/pr255-lifecycle-pytest.txt
grep -Eq '^46 passed in ' /tmp/pr255-lifecycle-pytest.txt
python -m pytest --collect-only -q tests/test_aura_ephemeral_workspace_contracts.py | tee /tmp/pr255-lifecycle-collect.txt
grep -Eq '^46 tests collected in ' /tmp/pr255-lifecycle-collect.txt
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
recipe_schema = json.loads(
    (Path("schemas") / "aura_ephemeral_workspace_recipe.schema.json").read_text(
        encoding="utf-8"
    )
)
for field in ("issued_at_epoch_seconds", "expires_at_epoch_seconds"):
    assert field in recipe_schema["required"]
    assert recipe_schema["properties"][field]["type"] == "integer"
assert (
    recipe_schema["x-aura-semantic-delegations"][
        "absolute_recipe_expiration_admission"
    ]
    == "mandatory semantic validator"
)
PY

grep -q 'recipe absolute expiration must equal issue time plus TTL' aura_ephemeral_workspace_contracts.py
grep -q 'arena_lease lease_id does not match content' aura_ephemeral_workspace_contracts.py
grep -q 'duplicate recipe reference IDs across manifest, adapter, and evidence roles' aura_ephemeral_workspace_contracts.py
grep -q 'workspace recipe is expired' aura_ephemeral_workspace_contracts.py

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

for control_file in \
  .github/workflows/pr255-lifecycle-identity-closure.yml \
  .github/workflows/pr255-lifecycle-identity-closure-v2.yml \
  .github/pr255_lifecycle_identity_closure_patch.py \
  .github/pr255_lifecycle_identity_closure_runner.sh \
  .github/pr255_lifecycle_identity_closure_runner_v2.sh; do
  test ! -e "$control_file"
done
test -z "$(git status --porcelain=v1 --untracked-files=all | grep -E 'CODEMAP|topology_map|live_topology_ast|lifecycle-identity-closure|lifecycle_identity_closure' || true)"

remote_head="$(git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
test "$remote_head" = "$FROZEN"

git config user.name 'AuraOS Lifecycle Identity Repair'
git config user.email 'actions@users.noreply.github.com'
git add \
  aura_ephemeral_workspace_contracts.py \
  docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md \
  schemas/aura_ephemeral_workspace_recipe.schema.json \
  tests/test_aura_ephemeral_workspace_contracts.py
git diff --cached --check
test "$(git diff --cached --name-only | wc -l)" -eq 4
git commit -m 'fix(pr1): bind absolute recipe lifecycle identity'

remote_head="$(git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
test "$remote_head" = "$FROZEN"
git push origin HEAD:"refs/heads/$BRANCH"
