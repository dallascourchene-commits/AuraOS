from pathlib import Path

code_path = Path("aura_ephemeral_workspace_contracts.py")
code = code_path.read_text(encoding="utf-8")
code_old = '''    project_payload = (
        project_projection.to_dict()
        if isinstance(project_projection, ProjectContextProjection)
        else project_projection
    )
    project = validate_project_semantics(
        project_payload, expected_projection=expected_project_projection
    )
'''
code_new = '''    project_record = _exact_contract_record(
        project_projection, ProjectContextProjection, "project_projection"
    )
    project = validate_project_semantics(
        project_record.to_dict(), expected_projection=expected_project_projection
    )
'''
if code.count(code_old) != 1:
    raise SystemExit(f"compiler project boundary anchor count: {code.count(code_old)}")
code = code.replace(code_old, code_new, 1)
code_path.write_text(code, encoding="utf-8")

test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text(encoding="utf-8")
class_anchor = '''    trusted_project = project()
    redirected_project = clone_as_subclass(trusted_project, RedirectedProject)
'''
class_replacement = '''    class MasqueradingProject(ProjectContextProjection):
        def to_dict(self) -> dict[str, Any]:
            return project().to_dict()

    trusted_project = project()
    redirected_project = clone_as_subclass(trusted_project, RedirectedProject)
    masquerading_project = clone_as_subclass(trusted_project, MasqueradingProject)
'''
if tests.count(class_anchor) != 1:
    raise SystemExit(f"compiler subclass class anchor count: {tests.count(class_anchor)}")
tests = tests.replace(class_anchor, class_replacement, 1)

compiler_anchor = '''    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        validate_project_semantics(
            trusted_project.to_dict(), expected_projection=redirected_project
        )

    redirected_recipe = clone_as_subclass(workspace_recipe, RedirectedRecipe)
'''
compiler_replacement = '''    with pytest.raises(ValueError, match="exact ProjectContextProjection"):
        validate_project_semantics(
            trusted_project.to_dict(), expected_projection=redirected_project
        )

    manifest = create_manifest(
        "Reject projection subclasses at the compiler boundary.",
        organ_id="EORG-project-subclass-boundary",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    with pytest.raises(
        ValueError,
        match="project_projection must be an exact ProjectContextProjection",
    ):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=masquerading_project,
            expected_project_projection=trusted_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    redirected_recipe = clone_as_subclass(workspace_recipe, RedirectedRecipe)
'''
if tests.count(compiler_anchor) != 1:
    raise SystemExit(f"compiler subclass assertion anchor count: {tests.count(compiler_anchor)}")
tests = tests.replace(compiler_anchor, compiler_replacement, 1)
test_path.write_text(tests, encoding="utf-8")

doc_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
doc = doc_path.read_text(encoding="utf-8")
doc_old = '''`canonical_owner` is fixed to `aura_unified_memory_continuity`; privacy is fixed to `MINIMUM_SUFFICIENT`; egress is fixed to `LOCAL_ONLY`. Hypothesis/presentation references, stale references, duplicate IDs, redirected owners, and incomplete rebinding fail closed.

### `EphemeralWorkspaceRecipe`
'''
doc_new = '''`canonical_owner` is fixed to `aura_unified_memory_continuity`; privacy is fixed to `MINIMUM_SUFFICIENT`; egress is fixed to `LOCAL_ONLY`. Hypothesis/presentation references, stale references, duplicate IDs, redirected owners, and incomplete rebinding fail closed.

The compiler admits `project_projection` only as an exact `ProjectContextProjection` or a detached serialized mapping. Subclasses and other live objects are rejected before any overridable serializer can influence admission.

### `EphemeralWorkspaceRecipe`
'''
if doc.count(doc_old) != 1:
    raise SystemExit(f"project boundary documentation anchor count: {doc.count(doc_old)}")
doc = doc.replace(doc_old, doc_new, 1)
doc_path.write_text(doc, encoding="utf-8")
