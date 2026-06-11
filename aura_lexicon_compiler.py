"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: os, ast, json
FUNCTIONS: compile_lexicon, __init__, visit_FunctionDef, visit_ClassDef, visit_Call, visit_Attribute
SYNOPSIS: The Python module, leveraging `os`, `ast`, and `json`, provides a strict static analysis framework via `compile_lexicon`, `__init__`, and AST visitor methods (`visit_FunctionDef`, `visit_ClassDef`, `visit_Call`, `visit_Attribute`) to enforce syntactic and structural validation of source code.
[/AURA_MASTER_KEY]
"""
import ast
import json
import os

TARGET_FILES = [
    "aura_node.py",
    os.path.expanduser("~/AuraSovereign/aura_heal.py"),
    "gateway.py",
    "aura_core.py"
]

OUTPUT_LEXICON = "aura_lexicon.json"

class LexiconCompiler(ast.NodeVisitor):
    def __init__(self):
        self.vocabulary = set()

    def visit_FunctionDef(self, node):
        self.vocabulary.add(f"def {node.name}()")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.vocabulary.add(f"class {node.name}:")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.vocabulary.add(f"{node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if hasattr(node, 'attr'):
            self.vocabulary.add(f".{node.attr}")
        self.generic_visit(node)

def compile_lexicon():
    print("[AURA] Initiating Edge-Native Lexicon Compiler...")
    compiler = LexiconCompiler()

    for file in TARGET_FILES:
        if os.path.exists(file):
            print(f"[*] Scanning AST topology of {file}...")
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read(), filename=file)
                    compiler.visit(tree)
                except SyntaxError:
                    print(f"[-] Syntax anomaly detected in {file}. Skipping malformed nodes.")
        else:
            print(f"[-] {file} not found. Skipping.")

    primitives = [
        "pass", "True", "False", "None", "async", "await", "self", "if", 
        "else:", "return", "dict", "list", "emit_ar_pulse", "websocket.send",
        "np.array", "np.dot", "math", "st3gg", "HOT", "COLD", "Sphere", "Tetrahedron"
    ]
    compiler.vocabulary.update(primitives)

    lexicon_list = sorted(list(compiler.vocabulary))
    semantic_decoder = {}

    for idx, word in enumerate(lexicon_list):
        if idx > 4095:  
            print("[!] Lexicon density threshold reached. Truncating at 4096 primitives.")
            break
        
        # 12-bit binary compression
        binary_key = format(idx, '012b')
        semantic_decoder[binary_key] = word

    with open(OUTPUT_LEXICON, 'w', encoding='utf-8') as f:
        json.dump(semantic_decoder, f, indent=4)
        
    print(f"[+] Lexicon compilation absolute. {len(semantic_decoder)} syntax primitives vectorized.")
    print(f"[+] Output locked to {OUTPUT_LEXICON}")

if __name__ == "__main__":
    compile_lexicon()
