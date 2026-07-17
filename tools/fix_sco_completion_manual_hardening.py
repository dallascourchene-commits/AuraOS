"""Make the handoff authority replacement uniquely scoped before hardening."""
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
path.write_text(text, encoding="utf-8")
