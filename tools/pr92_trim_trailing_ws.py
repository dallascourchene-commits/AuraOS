from pathlib import Path

FILES = (
    Path("README.md"),
    Path("USER_GUIDE.md"),
    Path(".aura/ARCHITECTURE.md"),
    Path("aura_matrix_benchmark.py"),
    Path("test_aura_substrate.py"),
    Path("test_aura_coding_arena_workflow.py"),
)

for path in FILES:
    text = path.read_text(encoding="utf-8")
    had_final_newline = text.endswith("\n")
    normalized = "\n".join(line.rstrip() for line in text.splitlines())
    if had_final_newline:
        normalized += "\n"
    path.write_text(normalized, encoding="utf-8")

print("normalized trailing whitespace in closeout source and documentation")
