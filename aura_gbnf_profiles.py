"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa880-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: __future__
FUNCTIONS: list_profiles, get_grammar_string, grammar_stop_tokens
SYNOPSIS: The Python module implements a strict, grammar-aware profile management system, utilizing `__future__` annotations for type clarity, while exposing `list_profiles` for enumerating available profiles, `get_grammar_string` for retrieving structured grammar definitions, and `grammar_stop_tokens` for identifying termination markers in parsed inputs.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

PROFILE_POLYSYNTHETIC = "polysynthetic"
PROFILE_PYTHON_PATCH = "python_patch"
PROFILE_UNIT_INTERVAL = "unit_interval"
PROFILE_MC_LETTER = "mc_letter"

# Polysynthetic trace + [CODE] block (Aura operator / catalyze outputs)
GRAMMAR_POLYSYNTHETIC = """
root           ::= thought-block code-block
thought-block  ::= "[POLYSYNTHETIC_TRACE]\\n" spatial-slot " " aspect-slot " " class-slot " " subject-slot " " voice-slot " " stem-slot "\\n[/POLYSYNTHETIC_TRACE]\\n"
spatial-slot   ::= "SLOT_1_SPATIAL=" [A-Za-z0-9_]+
aspect-slot    ::= "SLOT_2_ASPECT=" [A-Za-z0-9_]+
class-slot     ::= "SLOT_3_CLASS=" [A-Za-z0-9_]+
subject-slot   ::= "SLOT_4_SUBJECT=" [A-Za-z0-9_]+
voice-slot     ::= "SLOT_5_VOICE=" [A-Za-z0-9_]+
stem-slot      ::= "SLOT_6_STEM=" [A-Za-z0-9_]+
code-block     ::= "[CODE]\\n" python-lines "\\n[/CODE]"
python-lines   ::= [^\\x00-\\x1F\\[\\]]+ ("\\n" [^\\x00-\\x1F\\[\\]]+)*
"""

# Code-only patch grammar for LiquidFlashEvolve / self-heal (GBNF syntax guarantee)
GRAMMAR_PYTHON_PATCH = """
root         ::= "[CODE]\\n" python-lines "\\n[/CODE]"
python-lines ::= [^\\x00-\\x1F\\[\\]]+ ("\\n" [^\\x00-\\x1F\\[\\]]+)*
"""

# Leading-space unit interval score (0.0–1.0) for edge audits / confidence
GRAMMAR_UNIT_INTERVAL = """
root  ::= ws score
ws    ::= " "
score ::= "0." [0-9] | "1.0"
"""

# Leading-space multiple-choice letter (A–E)
GRAMMAR_MC_LETTER = """
root   ::= ws choice
ws     ::= " "
choice ::= "A" | "B" | "C" | "D" | "E"
"""

_PROFILE_TO_GRAMMAR: dict[str, str] = {
    PROFILE_POLYSYNTHETIC: GRAMMAR_POLYSYNTHETIC,
    PROFILE_PYTHON_PATCH: GRAMMAR_PYTHON_PATCH,
    PROFILE_UNIT_INTERVAL: GRAMMAR_UNIT_INTERVAL,
    PROFILE_MC_LETTER: GRAMMAR_MC_LETTER,
}

# Backward-compatible alias used across aura_node
AURA_POLYSYNTHETIC_GBNF = GRAMMAR_POLYSYNTHETIC


def list_profiles() -> list[str]:
    return list(_PROFILE_TO_GRAMMAR.keys())


def get_grammar_string(profile: str) -> str:
    if profile not in _PROFILE_TO_GRAMMAR:
        raise KeyError(
            f"Unknown GBNF profile '{profile}'. "
            f"Valid: {', '.join(list_profiles())}"
        )
    return _PROFILE_TO_GRAMMAR[profile]


def grammar_stop_tokens(profile: str) -> list[str]:
    """Extra stop sequences beyond chat template stops."""
    if profile in (PROFILE_POLYSYNTHETIC, PROFILE_PYTHON_PATCH):
        return ["[/CODE]"]
    return []
