"""Repository-wide pytest collection boundaries.

These root-level files are executable smoke harnesses with module-scope work and
standalone exit/report semantics.  They are verified explicitly by the CI/local
harness and are not ordinary pytest modules.
"""

collect_ignore = [
    "test_aura_functions.py",
    "test_synthesis_upgrades.py",
    "test_syntax_fixes.py",
]
