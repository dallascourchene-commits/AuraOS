from pathlib import Path

source = Path(__file__).with_name("pr255_exact_record_closure_patch.py")
target = Path("/tmp/pr255_exact_record_closure_patch_fixed.py")
text = source.read_text(encoding="utf-8")

syntax_old = "    '''))\n    test_path.write_text"
syntax_new = "    ''')\n    test_path.write_text"
if text.count(syntax_old) != 1:
    raise SystemExit(f"temporary patch syntax anchor count: {text.count(syntax_old)}")
text = text.replace(syntax_old, syntax_new, 1)

import_old = "from pathlib import Path\nfrom textwrap import dedent\n"
import_new = "from pathlib import Path\nimport re\nfrom textwrap import dedent\n"
if text.count(import_old) != 1:
    raise SystemExit(f"temporary patch import anchor count: {text.count(import_old)}")
text = text.replace(import_old, import_new, 1)

section_start = text.index("    project_old = (\n")
section_end = text.index("    key_guard = \"not isinstance(key, str)\"\n", section_start)
replacement = '''    def replace_expected_record(
        source_text: str,
        variable: str,
        record_type: str,
        expected_count: int,
    ) -> str:
        pattern = re.compile(
            rf"(?m)^(?P<indent>[ \\t]+)expected = \\(\\n"
            rf"(?P=indent)    {variable}\\n"
            rf"(?P=indent)    if isinstance\\({variable}, {record_type}\\)\\n"
            rf"(?P=indent)    else {record_type}\\.from_dict\\({variable}\\)\\n"
            rf"(?P=indent)\\)\\n"
        )

        def replacement_for(match: re.Match[str]) -> str:
            indent = match.group("indent")
            return (
                f"{indent}expected = _exact_contract_record(\\n"
                f"{indent}    {variable}, {record_type}, \\\"{variable}\\\"\\n"
                f"{indent})\\n"
            )

        result, count = pattern.subn(replacement_for, source_text)
        if count != expected_count:
            raise SystemExit(
                f"expected {variable} exact admission: expected {expected_count} anchors, found {count}"
            )
        return result

    code = replace_expected_record(
        code, "expected_projection", "ProjectContextProjection", 2
    )
    code = replace_expected_record(
        code, "expected_recipe", "EphemeralWorkspaceRecipe", 2
    )
    code = replace_expected_record(
        code, "expected_observation", "MultimodalSpatialObservation", 2
    )

'''
text = text[:section_start] + replacement + text[section_end:]
target.write_text(text, encoding="utf-8")
