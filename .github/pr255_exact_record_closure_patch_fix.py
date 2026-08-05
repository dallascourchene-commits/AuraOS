from pathlib import Path

source = Path(__file__).with_name("pr255_exact_record_closure_patch.py")
target = Path("/tmp/pr255_exact_record_closure_patch_fixed.py")
text = source.read_text(encoding="utf-8")
old = "    '''))\n    test_path.write_text"
new = "    ''')\n    test_path.write_text"
if text.count(old) != 1:
    raise SystemExit(f"temporary patch syntax anchor count: {text.count(old)}")
target.write_text(text.replace(old, new, 1), encoding="utf-8")
