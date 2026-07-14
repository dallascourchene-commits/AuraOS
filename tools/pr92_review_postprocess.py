from pathlib import Path

path = Path("tests/test_aura_ai_router_dynamic.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '''(tmp_path / "alpha.py").write_text("def target():
    return 'alpha'
", encoding="utf-8")''',
    '''(tmp_path / "alpha.py").write_text("def target():\\n    return 'alpha'\\n", encoding="utf-8")''',
)
text = text.replace(
    '''(tmp_path / "beta.py").write_text("def target():
    return 'beta'
", encoding="utf-8")''',
    '''(tmp_path / "beta.py").write_text("def target():\\n    return 'beta'\\n", encoding="utf-8")''',
)
path.write_text(text, encoding="utf-8")
