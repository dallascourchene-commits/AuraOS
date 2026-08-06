from __future__ import annotations

import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "aura_ephemeral_workspace_contracts.py"
TESTS = ROOT / "tests" / "test_aura_ephemeral_workspace_contracts.py"


def replace_exact(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


contracts = CONTRACTS.read_text(encoding="utf-8")
contracts = replace_exact(
    contracts,
    "def compile_coding_spatial_workspace_recipe(*, base_manifest: Any,\n"
    "                                             project_projection: ProjectContextProjection | Mapping[str, Any],",
    "def compile_coding_spatial_workspace_recipe(*, base_manifest: Any,\n"
    "                                             expected_base_manifest: Any,\n"
    "                                             project_projection: ProjectContextProjection | Mapping[str, Any],",
    label="compiler signature",
)
contracts = replace_exact(
    contracts,
    '    """Compile the frozen recipe without invoking any canonical owner."""\n'
    "    exported = _bounded_manifest_export(base_manifest)\n"
    "    body, legacy_digest, source_snapshot_digest = _manifest_snapshot(exported)\n",
    '    """Compile only after binding the complete manifest to trusted expectation."""\n'
    "    expected_exported = _bounded_manifest_export(expected_base_manifest)\n"
    "    expected_body, expected_legacy_digest, expected_source_snapshot_digest = (\n"
    "        _manifest_snapshot(expected_exported)\n"
    "    )\n"
    "    exported = _bounded_manifest_export(base_manifest)\n"
    "    body, legacy_digest, source_snapshot_digest = _manifest_snapshot(exported)\n"
    "    if (\n"
    "        body != expected_body\n"
    "        or legacy_digest != expected_legacy_digest\n"
    "        or source_snapshot_digest != expected_source_snapshot_digest\n"
    "    ):\n"
    "        raise ValueError(\n"
    '            "base manifest does not match independently trusted complete identity"\n'
    "        )\n",
    label="complete manifest binding",
)
contracts = replace_exact(
    contracts,
    "    if (created_at, expires_at) != (expected_created_at, expected_expires_at):\n"
    '        raise ValueError("base manifest timestamp binding mismatch")\n',
    "    trusted_timestamps = (\n"
    "        _finite_number(\n"
    '            expected_body.get("created_at"),\n'
    '            "expected base manifest created_at",\n'
    "        ),\n"
    "        _finite_number(\n"
    '            expected_body.get("expires_at"),\n'
    '            "expected base manifest expires_at",\n'
    "        ),\n"
    "    )\n"
    "    if (expected_created_at, expected_expires_at) != trusted_timestamps:\n"
    "        raise ValueError(\n"
    '            "expected manifest timestamp binding disagrees with trusted complete identity"\n'
    "        )\n"
    "    if (created_at, expires_at) != trusted_timestamps:\n"
    '        raise ValueError("base manifest timestamp binding mismatch")\n',
    label="trusted timestamp cross-check",
)
CONTRACTS.write_text(contracts, encoding="utf-8")


tests = TESTS.read_text(encoding="utf-8")
lines = tests.splitlines(keepends=True)
output: list[str] = []
inserted = 0
for index, line in enumerate(lines):
    output.append(line)
    match = re.match(r"^(\s*)base_manifest=([^,\n]+),\s*$", line.rstrip("\n"))
    if not match:
        continue
    indent, expression = match.groups()
    next_line = lines[index + 1] if index + 1 < len(lines) else ""
    if "expected_base_manifest=" in next_line:
        continue
    output.append(f"{indent}expected_base_manifest=copy.deepcopy({expression}),\n")
    inserted += 1

tests = "".join(output)
if inserted < 5:
    raise SystemExit(f"expected to bind at least five compiler calls, bound {inserted}")

new_test = r'''


def test_compiler_rejects_self_consistent_manifest_substitution_against_complete_identity() -> None:
    """A replacement manifest cannot pass by preserving timestamps and recomputing self-hashes."""
    trusted = create_manifest(
        "Compile the trusted bounded coding workspace.",
        organ_id="EORG-trusted-complete-binding",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    substituted = copy.deepcopy(trusted)
    substituted.organ_id = "EORG-substituted-complete-binding"
    substituted.objective = "Compile a substituted but self-consistent workspace."
    substituted.objective_hash = workspace_contracts.hashlib.blake2b(
        substituted.objective.encode("utf-8"), digest_size=12
    ).hexdigest()
    substituted.phase_hash = substituted.compute_digest()

    with pytest.raises(
        ValueError,
        match="independently trusted complete identity",
    ):
        compile_coding_spatial_workspace_recipe(
            base_manifest=substituted,
            expected_base_manifest=trusted,
            expected_manifest_timestamps=_trusted_manifest_timestamps(trusted),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["4"]),),
        )
'''
if "test_compiler_rejects_self_consistent_manifest_substitution_against_complete_identity" in tests:
    raise SystemExit("complete-manifest regression test already exists")
tests += new_test

tree = ast.parse(tests)
missing: list[int] = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    if name != "compile_coding_spatial_workspace_recipe":
        continue
    keywords = {item.arg for item in node.keywords if item.arg is not None}
    if "expected_base_manifest" not in keywords:
        missing.append(node.lineno)
if missing:
    raise SystemExit(f"compiler calls missing expected_base_manifest at lines {missing}")

TESTS.write_text(tests, encoding="utf-8")
print(f"Phase 0 P2 transaction applied; bound {inserted} existing compiler calls")
