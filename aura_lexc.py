"""Compile Aura's ``aura.lexc`` source into a validated six-slot route graph.

The repository previously had two independent, lossy parsers for the same
lexicon.  This module is deliberately dependency-light so both the runtime PFST
and the claim-facing routing core can share one source of truth.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SlotName(str, Enum):
    DIR = "DIR"
    ASP = "ASP"
    CLASS = "CLASS"
    SUBJ = "SUBJ"
    VOICE = "VOICE"
    STEM = "STEM"


SLOT_ORDER = tuple(SlotName)


@dataclass(frozen=True)
class LexcDiagnostic:
    line: int
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class LexcArc:
    source: str
    target: str
    lexical: str
    surface: str
    line: int
    slot: SlotName


@dataclass(frozen=True)
class LexcRoute:
    states: tuple[str, ...]
    arcs: tuple[LexcArc, ...]

    @property
    def slots(self) -> tuple[SlotName, ...]:
        return tuple(arc.slot for arc in self.arcs)

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(arc.lexical for arc in self.arcs)

    @property
    def is_complete(self) -> bool:
        return self.slots == SLOT_ORDER and self.states[-1] == "#"

    def packet(self) -> dict[str, str]:
        if not self.is_complete:
            raise ValueError("route does not satisfy the complete six-slot contract")
        return {arc.slot.value: arc.lexical for arc in self.arcs}


class LexcCompileError(ValueError):
    def __init__(self, diagnostics: Iterable[LexcDiagnostic]):
        self.diagnostics = tuple(diagnostics)
        details = "; ".join(
            f"line {item.line} [{item.code}] {item.message}"
            for item in self.diagnostics
            if item.severity == "error"
        )
        super().__init__(details or "invalid lexc source")


def slot_for_source(source: str) -> SlotName:
    """Map a lexicon layer to Aura's canonical six-slot execution contract."""
    if source == "Root":
        return SlotName.DIR
    if source.startswith("Gate"):
        return SlotName.ASP
    if source.startswith("Action"):
        return SlotName.CLASS
    if source.startswith("Target") or source.startswith("Cloud"):
        return SlotName.SUBJ
    if source.startswith("Physics"):
        return SlotName.VOICE
    if source.startswith("Modifier") or source.startswith("Terminal"):
        return SlotName.STEM
    raise ValueError(f"cannot assign six-slot role to lexicon {source!r}")


def _split_mapping(raw: str) -> tuple[str, str]:
    if ":" not in raw:
        return raw, raw
    lexical, surface = raw.rsplit(":", 1)
    return lexical, surface


class AuraLexc:
    """Parsed, validated Aura lexc graph."""

    def __init__(
        self,
        arcs: Iterable[LexcArc],
        lexicons: Iterable[str],
        diagnostics: Iterable[LexcDiagnostic] = (),
    ) -> None:
        self.arcs = tuple(arcs)
        self.lexicons = frozenset(lexicons)
        self.diagnostics = tuple(diagnostics)
        graph: dict[str, list[LexcArc]] = {}
        for arc in self.arcs:
            graph.setdefault(arc.source, []).append(arc)
        self.graph = {state: tuple(items) for state, items in graph.items()}

    @classmethod
    def from_path(cls, path: str | Path, *, strict: bool = True) -> AuraLexc:
        return cls.from_text(
            Path(path).read_text(encoding="utf-8"),
            strict=strict,
        )

    @classmethod
    def from_text(cls, text: str, *, strict: bool = True) -> AuraLexc:
        arcs: list[LexcArc] = []
        diagnostics: list[LexcDiagnostic] = []
        lexicons: set[str] = set()
        current: str | None = None

        for line_number, original in enumerate(text.splitlines(), 1):
            line = original.split("!", 1)[0].strip()
            if not line or line.startswith("Multichar_Symbols"):
                continue
            if line.startswith("LEXICON"):
                parts = line.split()
                if len(parts) != 2:
                    diagnostics.append(
                        LexcDiagnostic(
                            line_number,
                            "error",
                            "INVALID_LEXICON",
                            "LEXICON declaration must contain exactly one name",
                        )
                    )
                    current = None
                    continue
                current = parts[1]
                if current in lexicons:
                    diagnostics.append(
                        LexcDiagnostic(
                            line_number,
                            "warning",
                            "LEXICON_CONTINUATION",
                            f"continuing previously declared lexicon {current}",
                        )
                    )
                lexicons.add(current)
                continue

            if current is None:
                # Xerox lexc permits Multichar_Symbols to continue over
                # subsequent lines until the first LEXICON declaration.
                continue
            if not line.endswith(";"):
                diagnostics.append(
                    LexcDiagnostic(
                        line_number,
                        "error",
                        "UNTERMINATED_ENTRY",
                        f"transition in {current} must end with ';'",
                    )
                )
                continue

            parts = line[:-1].strip().split()
            if parts == ["#"]:
                mapping, target = "#", "#"
            elif len(parts) == 2:
                mapping, target = parts
            else:
                diagnostics.append(
                    LexcDiagnostic(
                        line_number,
                        "error",
                        "INVALID_ENTRY",
                        f"transition in {current} must contain mapping and target",
                    )
                )
                continue
            try:
                slot = slot_for_source(current)
            except ValueError as exc:
                diagnostics.append(
                    LexcDiagnostic(
                        line_number,
                        "error",
                        "UNKNOWN_LAYER",
                        str(exc),
                    )
                )
                continue
            lexical, surface = _split_mapping(mapping)
            arcs.append(
                LexcArc(
                    source=current,
                    target=target,
                    lexical=lexical,
                    surface=surface,
                    line=line_number,
                    slot=slot,
                )
            )

        for arc in arcs:
            if arc.target != "#" and arc.target not in lexicons:
                diagnostics.append(
                    LexcDiagnostic(
                        arc.line,
                        "error",
                        "UNDEFINED_TARGET",
                        f"{arc.source} routes to undefined lexicon {arc.target}",
                    )
                )

        compiled = cls(arcs, lexicons, diagnostics)
        if "Root" not in compiled.lexicons:
            diagnostics.append(
                LexcDiagnostic(0, "error", "MISSING_ROOT", "LEXICON Root is required")
            )
            compiled = cls(arcs, lexicons, diagnostics)
        if strict and compiled.errors:
            raise LexcCompileError(compiled.errors)
        return compiled

    @property
    def errors(self) -> tuple[LexcDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "error")

    @property
    def warnings(self) -> tuple[LexcDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "warning")

    def complete_routes(self, *, limit: int = 256) -> tuple[LexcRoute, ...]:
        """Enumerate bounded, acyclic Root-to-terminal six-slot routes."""
        routes: list[LexcRoute] = []

        def visit(
            state: str,
            states: tuple[str, ...],
            arcs: tuple[LexcArc, ...],
        ) -> None:
            if len(routes) >= limit:
                return
            if state == "#":
                route = LexcRoute(states=states, arcs=arcs)
                if route.is_complete:
                    routes.append(route)
                return
            for arc in self.graph.get(state, ()):
                if arc.target in states and arc.target != "#":
                    continue
                next_arcs = (*arcs, arc)
                expected = SLOT_ORDER[: len(next_arcs)]
                if tuple(item.slot for item in next_arcs) != expected:
                    continue
                if len(next_arcs) > len(SLOT_ORDER):
                    continue
                visit(arc.target, (*states, arc.target), next_arcs)

        visit("Root", ("Root",), ())
        return tuple(routes)

    def validate_symbols(self, symbols: Iterable[str]) -> LexcRoute | None:
        """Validate one exact lexical route against the six-slot graph."""
        requested = tuple(symbols)
        if len(requested) != len(SLOT_ORDER):
            return None
        state = "Root"
        states = [state]
        selected: list[LexcArc] = []
        for expected_slot, symbol in zip(SLOT_ORDER, requested):
            match = next(
                (
                    arc
                    for arc in self.graph.get(state, ())
                    if arc.slot == expected_slot and arc.lexical == symbol
                ),
                None,
            )
            if match is None:
                return None
            selected.append(match)
            state = match.target
            states.append(state)
        route = LexcRoute(tuple(states), tuple(selected))
        return route if route.is_complete else None

    def stats(self) -> dict[str, int]:
        routes = self.complete_routes()
        return {
            "lexicons": len(self.lexicons),
            "transitions": len(self.arcs),
            "complete_six_slot_routes": len(routes),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
        }
