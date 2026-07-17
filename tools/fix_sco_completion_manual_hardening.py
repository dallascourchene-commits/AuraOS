"""Make manual-hardening anchors and generated test escapes deterministic."""
from pathlib import Path

path = Path(__file__).resolve().parent / "apply_sco_completion_manual_hardening.py"
text = path.read_text(encoding="utf-8")
old = '''        ''' + "'''" + '''            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
''' + "'''" + ''',
        ''' + "'''" + '''            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
''' + "'''" + ''',
'''
new = '''        ''' + "'''" + '''            "digital_baton_only": True,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "patch_authority": PATCH_AUTHORITY,
''' + "'''" + ''',
        ''' + "'''" + '''            "digital_baton_only": True,
            "human_review_required": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "professional_certification_authorized": False,
            "patch_authority": PATCH_AUTHORITY,
''' + "'''" + ''',
'''
if new not in text:
    if text.count(old) != 1:
        raise RuntimeError("expected one ambiguous handoff hardening block")
    text = text.replace(old, new, 1)

replacements = {
    'marker.write_text("exact head\\n", encoding="utf-8")': (
        'marker.write_text("exact head\\\\n", encoding="utf-8")'
    ),
    '(tmp_path / "owner.py").write_text("def other():\\n    return True\\n", encoding="utf-8")': (
        '(tmp_path / "owner.py").write_text('
        '"def other():\\\\n    return True\\\\n", encoding="utf-8")'
    ),
}
for old_escape, new_escape in replacements.items():
    if new_escape not in text:
        if text.count(old_escape) != 1:
            raise RuntimeError(f"expected one generated test escape: {old_escape!r}")
        text = text.replace(old_escape, new_escape, 1)

path.write_text(text, encoding="utf-8")
