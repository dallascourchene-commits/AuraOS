from pathlib import Path

path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
text = path.read_text(encoding="utf-8")
old = '''        compile_coding_spatial_workspace_recipe(
            base_manifest=serialized_manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(serialized_manifest),
            project_projection=project(),
'''
new = '''        compile_coding_spatial_workspace_recipe(
            base_manifest=serialized_manifest,
            project_projection=project(),
'''
if text.count(old) != 1:
    raise RuntimeError(f"missing-binding negative test anchor changed: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("preserved the missing-timestamp negative test")
