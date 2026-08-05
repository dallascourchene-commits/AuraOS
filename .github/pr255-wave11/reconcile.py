import json
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


source_path = Path("aura_ephemeral_workspace_contracts.py")
source = source_path.read_text()
source = replace_once(
    source,
    '''        for name, ceiling in _PR1_RESOURCE_CEILINGS.items():
            if getattr(self.budgets, name) > ceiling:
                raise ValueError(f"budget.{name} exceeds the PR1 safe ceiling")
        if self.budgets.network_calls != 0:
            raise ValueError("recipe budget must keep network_calls at zero")
        if self.budgets.model_calls != 0:
            raise ValueError("recipe budget must keep model_calls at zero")
''',
    '''        if self.budgets.network_calls != 0:
            raise ValueError("recipe budget must keep network_calls at zero")
        if self.budgets.model_calls != 0:
            raise ValueError("recipe budget must keep model_calls at zero")
        budget_values = self.budgets.to_dict()
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items():
            if budget_values[name] > ceiling:
                raise ValueError(f"budget.{name} exceeds the PR1 safe ceiling")
''',
    "preserve zero-call diagnostics without dynamic getattr",
)
source_path.write_text(source)


test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text()
tests = replace_once(
    tests,
    'good = ref("artifact:good", D["1"], metadata={"source_path": "aura.py", "line_start": 1})',
    'good = ref("artifact:good", D["1"], metadata={"source_path": "aura.py", "line_start": 1, "line_end": 1})',
    "complete legacy source-span fixture",
)
tests = replace_once(
    tests,
    'with pytest.raises(ValueError, match="context_tokens exceeds the PR1 safe ceiling"):',
    'with pytest.raises(ValueError, match="context_tokens exceeds (?:base manifest resource|the PR1 safe) ceiling"):',
    "context ceiling diagnostic compatibility",
)
test_path.write_text(tests)


safe_source_path_pattern = (
    r"^(?!/)(?![A-Za-z]:/)(?!.*\\)(?!.*(?:^|/)\.{1,2}(?:/|$))"
    r"(?!.*(?:^|/)\.[eE][nN][vV][^/]*(?:/|$))"
    r"(?!.*(?:^|/)[sS][eE][cC][rR][eE][tT][sS][^/]*(?:/|$))"
    r"(?!.*(?:^|/)\.[kK][eE][yY](?:/|$))"
    r"(?!.*(?:^|/)\.[gG][iI][tT]/[cC][rR][eE][dD][eE][nN][tT][iI][aA][lL][sS](?:/|$))"
    r"[^\u0000-\u001f]+$"
)


def tighten_metadata_copies(node: object) -> int:
    updated = 0
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict) and {
            "source_path", "line_start", "line_end"
        } <= set(properties):
            properties["source_path"]["pattern"] = safe_source_path_pattern
            properties["line_start"]["minimum"] = 1
            properties["line_end"]["minimum"] = 1
            node["dependentRequired"] = {
                "line_start": ["line_end", "source_path"],
                "line_end": ["line_start", "source_path"],
            }
            updated += 1
        for value in node.values():
            updated += tighten_metadata_copies(value)
    elif isinstance(node, list):
        for value in node:
            updated += tighten_metadata_copies(value)
    return updated


for schema_path in (
    Path("schemas/aura_project_context_projection.schema.json"),
    Path("schemas/aura_ephemeral_workspace_recipe.schema.json"),
    Path("schemas/aura_multimodal_spatial_observation.schema.json"),
):
    schema = json.loads(schema_path.read_text())
    updated = tighten_metadata_copies(schema)
    if updated < 2:
        raise RuntimeError(f"{schema_path}: expected duplicated metadata contracts, found {updated}")
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")

print("reconciled PR255 wave11 verification compatibility")
