from __future__ import annotations
import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / 'aura_construction_contracts.py', ROOT / 'aura_construction_state.py', ROOT / 'aura_construction_authority.py']
errors = []
for path in FILES:
    text = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        errors.append(f'{path.name}:syntax:{exc}')
        continue
    imports = {}
    used = set()
    module_defs = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    for name in sorted(set(module_defs)):
        if module_defs.count(name) > 1:
            errors.append(f'{path.name}:duplicate-module-definition:{name}')
    for class_node in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        member_defs = [node.name for node in class_node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for name in sorted(set(member_defs)):
            if member_defs.count(name) > 1:
                errors.append(f'{path.name}:duplicate-class-member:{class_node.name}.{name}')
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != '*':
                    imports[alias.asname or alias.name] = node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            errors.append(f'{path.name}:bare-except:{node.lineno}')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'eval', 'exec', 'compile', '__import__'}:
            errors.append(f'{path.name}:dynamic-execution:{node.func.id}:{node.lineno}')
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in [*node.args.defaults, *node.args.kw_defaults]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    errors.append(f'{path.name}:mutable-default:{node.name}:{node.lineno}')
    for name, line in imports.items():
        if name not in used and name != 'annotations':
            errors.append(f'{path.name}:unused-import:{name}:{line}')
    patterns = {
        'todo': r'\b(?:TODO|FIXME|HACK)\b',
        'authority_true': r'physical_work_authorized\s*=\s*True',
        'proposal_false': r'proposal_only\s*=\s*False',
        'vsa_true': r'vsa_patch_authority\s*=\s*True',
        'custom_crypto': r'\b(?:hmac|cryptography|nacl|Crypto)\b',
        'shell': r'\b(?:os\.system|subprocess\.|Popen\()',
    }
    for label, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            line = text.count('\n', 0, match.start()) + 1
            errors.append(f'{path.name}:{label}:{line}')
    for index, line in enumerate(text.splitlines(), 1):
        if len(line) > 119:
            errors.append(f'{path.name}:line-too-long:{index}:{len(line)}')
        if line.rstrip() != line:
            errors.append(f'{path.name}:trailing-whitespace:{index}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('MANUAL_FATAL_LINT_PASS')
