from pathlib import Path

path = Path("tests/test_aura_project_context_compiler.py")
text = path.read_text()
old_a = 'with pytest.raises(TypeError, match="edges must be a sequence"):'
old_b = 'with pytest.raises(TypeError, match="exact built-in tuple or list"):'
new = 'with pytest.raises(TypeError, match="edges must be an exact immutable tuple"):'
assert text.count(old_a) == 1, "old non-sequence edge expectation missing"
assert text.count(old_b) == 1, "old hostile-sequence edge expectation missing"
text = text.replace(old_a, new, 1).replace(old_b, new, 1)
path.write_text(text.rstrip() + "\n")
