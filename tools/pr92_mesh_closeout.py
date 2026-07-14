from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def main() -> None:
    path = "aura_matrix_benchmark.py"
    text = _read(path)
    if "from pathlib import Path" not in text:
        text = text.replace("import os\nimport time\n", "import os\nfrom pathlib import Path\nimport time\n", 1)

    marker = "# --------------------------------------------------------------------------- #\n# Offline mock egress (deterministic; for pipeline testing only)\n# --------------------------------------------------------------------------- #\n"
    helper = '''# PR92:MESH_FIXTURE_HELPER:START
def _mesh_offload_fixture() -> tuple[int, str, str]:
    """Resolve the mock edit target inside offload_compute by symbol."""
    lines = (Path(REPO_ROOT) / "aura_mesh.py").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.lstrip().startswith("async def offload_compute("))
    function_indent = len(lines[start]) - len(lines[start].lstrip())
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].lstrip()
        indent = len(lines[i]) - len(stripped)
        if stripped.startswith(("def ", "async def ")) and indent == function_indent:
            end = i
            break
    target = next(
        i for i in range(start, end)
        if "secure_packet:" in lines[i]
        and "pack_length_prefixed_payload(payload_obj)" in lines[i]
    )
    original = lines[target]
    indentation = original[: len(original) - len(original.lstrip())]
    return target + 1, original, indentation
# PR92:MESH_FIXTURE_HELPER:END
'''
    if "# PR92:MESH_FIXTURE_HELPER:START" not in text:
        if marker not in text:
            raise RuntimeError("benchmark helper insertion marker not found")
        text = text.replace(marker, helper + "\n" + marker, 1)

    branch = '''        if is_aura:
            target_line, original_line, indentation = _mesh_offload_fixture()
            replacement = (
                f"{indentation}secure_packet = "
                "self.pack_secure_polysynthetic_packet([0, 0, 0, 0, 0, 0], 1.0)"
            )
        if is_aura and wants_edit_plan:
            text = json.dumps(
                {"edits": [{"file": "aura_mesh.py", "start_line": target_line,
                            "end_line": target_line, "replacement": replacement}]}
            )
        elif is_aura:
            text = (
                "--- a/aura_mesh.py\\n+++ b/aura_mesh.py\\n"
                f"@@ -{target_line},1 +{target_line},2 @@\\n"
                f"-{original_line}\\n"
                f"+{indentation}# validate target before packing (no new deps)\\n"
                f"+{replacement}\\n"
            )
'''
    pattern = re.compile(
        r"        if is_aura and wants_edit_plan:\n.*?"
        r"(?=        else:\n            text = \(\n"
        r"                \"Sure! Here is an improved version)",
        re.DOTALL,
    )
    text, count = pattern.subn(branch, text, count=1)
    if count != 1:
        raise RuntimeError(f"benchmark mock branch bounded matches: {count}")
    _write(path, text)

    path = "test_aura_substrate.py"
    text = _read(path)
    fixture = '''    original = ContextSelector().read("aura_mesh.py")
    function_source, function_start, _function_end = extract_function_source(
        original, "offload_compute"
    )
    assert function_source is not None
    target_offset = next(
        offset for offset, line in enumerate(function_source.splitlines())
        if "secure_packet:" in line
        and "pack_length_prefixed_payload(payload_obj)" in line
    )
    target_line = function_start + target_offset
    original_line = original.splitlines()[target_line - 1]
    indentation = original_line[: len(original_line) - len(original_line.lstrip())]
    good = json.dumps(
        {"edits": [{"file": "aura_mesh.py", "start_line": target_line,
                    "end_line": target_line,
                    "replacement": (
                        f"{indentation}secure_packet = "
                        "self.pack_secure_polysynthetic_packet("
                        "[0, 0, 0, 0, 0, 0], 1.0)"
                    )}]}
    )
'''
    pattern = re.compile(
        r'    original = ContextSelector\(\)\.read\("aura_mesh\.py"\)\n.*?'
        r"(?=    plan, note = parse_edit_plan\(good\))",
        re.DOTALL,
    )
    text, count = pattern.subn(fixture, text, count=1)
    if count != 1:
        raise RuntimeError(f"substrate fixture bounded matches: {count}")
    _write(path, text)
    print("mesh benchmark fixtures now resolve offload_compute by symbol")


if __name__ == "__main__":
    main()
