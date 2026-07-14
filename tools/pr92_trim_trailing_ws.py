from pathlib import Path

FILES = (
    Path("README.md"),
    Path("USER_GUIDE.md"),
    Path(".aura/ARCHITECTURE.md"),
    Path("aura_matrix_benchmark.py"),
    Path("test_aura_substrate.py"),
    Path("test_aura_coding_arena_workflow.py"),
    Path("tests/test_aura_adaptive_security.py"),
)

for path in FILES:
    lines = path.read_text(encoding="utf-8").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    normalized = "\n".join(line.rstrip() for line in lines) + "\n"
    path.write_text(normalized, encoding="utf-8")

print("normalized trailing whitespace and final newlines in closeout files")
