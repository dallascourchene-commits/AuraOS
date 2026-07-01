"""
Aura ATT FST Runtime
======================
Pure-Python AT&T format finite-state transducer runtime for OjibweMorph.

The OjibweMorph ojibwe.att is stored in the "generation" direction:
  input  = morphological analysis tags (e.g. "nibaa+VAI+Ind+Pos+Neu+3Sg")
  output = surface characters (e.g. "nibaa")

To analyse (surface → tags) we read the transitions in INVERSE direction,
treating output characters as input and collecting input tags as output.

AT&T format:
  Transition: src_state \\t dst_state \\t input_sym \\t output_sym [\\t weight]
  Final state: state [\\t weight]
  Epsilon: @0@

Performance strategy:
  Build two dicts on load:
    _gen_transitions:    analysis_char → surface_char  (for generation)
    _analyse_transitions: surface_char → analysis_tags (for analysis = inverse)
  DFS with 500ms timeout and MAX_ANALYSES cap.

Citation (please keep):
  OjibweMorph — ELF-Lab, University of British Columbia.
  Hammerly, C., Livesay, N., Arppe, A., Stacey, A., & Silfverberg, M. (2026).
  https://github.com/ELF-Lab/OjibweMorph — CC BY-NC-SA 4.0.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

EPSILON = "@0@"
MAX_ANALYSES = 10
TIMEOUT_SECONDS = 1.0


class ATTTransducer:
    """
    AT&T FST transducer for OjibweMorph.

    The ATT file is stored GENERATION direction (tags → surface).
    analyse()  runs the inverse path (surface → tags).
    generate() runs the forward path (tags → surface).

    Both use DFS with a timeout guard.
    """

    def __init__(self, att_path: Path) -> None:
        # Forward (generation): state → {analysis_tag → [(dst_state, surface_char)]}
        self._fwd: Dict[int, Dict[str, List[Tuple[int, str]]]] = {}
        # Inverse (analysis):   state → {surface_char → [(dst_state, analysis_tag)]}
        self._inv: Dict[int, Dict[str, List[Tuple[int, str]]]] = {}
        self._final_states: Set[int] = set()
        self._att_path = att_path
        self._load(att_path)

    def _load(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                n = len(parts)
                if n == 1:
                    try:
                        self._final_states.add(int(parts[0]))
                    except ValueError:
                        pass
                elif n == 2:
                    try:
                        self._final_states.add(int(parts[0]))
                    except ValueError:
                        pass
                elif n >= 4:
                    src = int(parts[0])
                    dst = int(parts[1])
                    tag = parts[2]   # analysis tag (input side = generation input)
                    ch  = parts[3]   # surface char (output side = generation output)
                    # Forward
                    self._fwd.setdefault(src, {}).setdefault(tag, []).append((dst, ch))
                    # Inverse (swap roles)
                    self._inv.setdefault(src, {}).setdefault(ch, []).append((dst, tag))

    def analyse(self, surface_form: str) -> List[str]:
        """
        Surface form → list of morphological analysis strings.
        Runs the inverse transducer (surface chars as input, tags as output).
        """
        results: List[str] = []
        deadline = time.monotonic() + TIMEOUT_SECONDS
        # Stack: (state, pos_in_surface, analysis_built_so_far)
        stack: List[Tuple[int, int, str]] = [(0, 0, "")]
        chars = list(surface_form)
        n = len(chars)
        visited = set()  # (state, pos) guard against loops

        while stack and len(results) < MAX_ANALYSES:
            if time.monotonic() > deadline:
                break
            state, pos, analysis = stack.pop()

            key = (state, pos)
            if key in visited:
                continue
            visited.add(key)

            # Accept?
            if pos == n and state in self._final_states and analysis:
                if analysis not in results:
                    results.append(analysis)
                continue

            arcs = self._inv.get(state, {})

            # Epsilon on surface side (skip surface char, accumulate tag)
            for (dst, tag) in arcs.get(EPSILON, []):
                new_analysis = analysis + ("" if tag == EPSILON else tag)
                stack.append((dst, pos, new_analysis))

            # Consume next surface character
            if pos < n:
                ch = chars[pos]
                for (dst, tag) in arcs.get(ch, []):
                    new_analysis = analysis + ("" if tag == EPSILON else tag)
                    stack.append((dst, pos + 1, new_analysis))

        return results

    def generate(self, analysis: str) -> List[str]:
        """
        Morphological analysis string → list of surface forms.
        Runs the forward transducer (tags as input, surface chars as output).
        Note: analysis tags in ATT can be multi-char (e.g. "nibaa+VAI+Ind+..."),
        so we tokenize by splitting on '+' and matching multi-char arc labels.
        """
        results: List[str] = []
        deadline = time.monotonic() + TIMEOUT_SECONDS
        # Stack: (state, pos_in_analysis_chars, surface_built_so_far)
        stack: List[Tuple[int, int, str]] = [(0, 0, "")]
        chars = list(analysis)
        n = len(chars)
        visited = set()

        while stack and len(results) < MAX_ANALYSES:
            if time.monotonic() > deadline:
                break
            state, pos, surface = stack.pop()

            key = (state, pos)
            if key in visited:
                continue
            visited.add(key)

            if pos == n and state in self._final_states and surface:
                if surface not in results:
                    results.append(surface)
                continue

            arcs = self._fwd.get(state, {})

            # Epsilon transitions
            for (dst, ch) in arcs.get(EPSILON, []):
                new_surf = surface + ("" if ch == EPSILON else ch)
                stack.append((dst, pos, new_surf))

            # Try all multi-char arc labels that match at current position
            remaining = analysis[pos:]
            for tag, arc_list in arcs.items():
                if tag == EPSILON:
                    continue
                if remaining.startswith(tag):
                    new_pos = pos + len(tag)
                    for (dst, ch) in arc_list:
                        new_surf = surface + ("" if ch == EPSILON else ch)
                        stack.append((dst, new_pos, new_surf))

        return results


# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

_TRANSDUCER: Optional[ATTTransducer] = None
_TRANSDUCER_PATH: Optional[Path] = None
_LOAD_ERROR: Optional[str] = None


def load_ojibwe_transducer(att_path: Optional[Path] = None) -> Optional[ATTTransducer]:
    """Load (or return cached) the OjibweMorph transducer."""
    global _TRANSDUCER, _TRANSDUCER_PATH, _LOAD_ERROR

    if att_path is None:
        att_path = Path(__file__).parent / "ojibwemorph_fst" / "ojibwe.att"

    if _TRANSDUCER is not None and _TRANSDUCER_PATH == att_path:
        return _TRANSDUCER

    if not att_path.exists():
        _LOAD_ERROR = f"OjibweMorph ATT file not found at {att_path}"
        return None

    try:
        _TRANSDUCER = ATTTransducer(att_path)
        _TRANSDUCER_PATH = att_path
        _LOAD_ERROR = None
        return _TRANSDUCER
    except Exception as exc:
        _LOAD_ERROR = str(exc)
        return None


def load_error() -> Optional[str]:
    return _LOAD_ERROR
