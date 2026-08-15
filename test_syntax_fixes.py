#!/usr/bin/env python3
"""Quick syntax validation for fixed files"""

import ast
import sys

files_to_test = [
    "aura_anthropic_router.py",
    "mistral_gate.py",
]

print("Testing syntax fixes...")
all_passed = True

for filepath in files_to_test:
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        print(f"✅ {filepath}: OK")
    except SyntaxError as e:
        print(f"❌ {filepath}: SYNTAX ERROR at line {e.lineno}: {e.msg}")
        all_passed = False
    except Exception as e:
        print(f"⚠️  {filepath}: {type(e).__name__}: {e}")
        all_passed = False

if all_passed:
    print("\n✅ All syntax fixes validated!")
else:
    print("\n❌ Some files still have syntax errors")

if __name__ == "__main__":
    raise SystemExit(0 if all_passed else 1)
if not all_passed:
    raise AssertionError("legacy syntax validation failed")

# Made with Bob
