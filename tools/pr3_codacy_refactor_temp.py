from pathlib import Path
from textwrap import dedent

PATH = Path('aura_project_context_compiler.py')
text = PATH.read_text(encoding='utf-8')


def replace_between(source: str, start_marker: str, end_marker: str, replacement: str, *, start_from: int = 0) -> str:
    start = source.index(start_marker, start_from)
    end = source.index(end_marker, start)
    return source[:start] + replacement + source[end:]


# 1. Candidate constructor: preserve exact semantics, move validation into small helpers.
candidate_class = '@dataclass(frozen=True)\nclass ProjectContextCandidate:\n'
candidate_pos = text.index(candidate_class)
post_start = text.index('    def __post_init__(self) -> None:\n', candidate_pos)
post_end = text.index('    @property\n    def origin_bound', post_start)
candidate_post = dedent('''
    def __post_init__(self) -> None:
        _normalize_candidate_identity(self)
        _normalize_candidate_relationships(self)
        _validate_candidate_reference(self)
        _validate_candidate_authority(self)

''').replace('\ndef __post_init__', '\n    def __post_init__')
# dedent above needs class indentation on all method body lines.
candidate_post = '''    def __post_init__(self) -> None:\n        _normalize_candidate_identity(self)\n        _normalize_candidate_relationships(self)\n        _validate_candidate_reference(self)\n        _validate_candidate_authority(self)\n\n'''
text = text[:post_start] + candidate_post + text[post_end:]

candidate_helpers = dedent('''

def _normalize_candidate_identity(candidate: Any) -> None:
    object.__setattr__(candidate, "candidate_id", _id(candidate.candidate_id, "candidate_id"))
    object.__setattr__(candidate, "category", _enum(CandidateCategory, candidate.category, "category"))
    object.__setattr__(candidate, "source_adapter", _id(candidate.source_adapter, "source_adapter"))
    object.__setattr__(candidate, "origin_ref", _text(candidate.origin_ref, "origin_ref"))
    object.__setattr__(
        candidate,
        "authority_class",
        _enum(ContextAuthorityClass, candidate.authority_class, "authority_class"),
    )
    object.__setattr__(
        candidate,
        "truth_class",
        _enum(CandidateTruthClass, candidate.truth_class, "truth_class"),
    )
    object.__setattr__(
        candidate,
        "availability",
        _enum(CandidateAvailability, candidate.availability, "availability"),
    )
    object.__setattr__(
        candidate,
        "relevance_score",
        _int(candidate.relevance_score, "relevance_score", maximum=1_000_000),
    )


def _normalize_candidate_relationships(candidate: Any) -> None:
    if type(candidate.required) is not bool or type(candidate.answer_determining) is not bool:
        raise TypeError("required and answer_determining must be booleans")
    object.__setattr__(
        candidate,
        "dependency_ids",
        _ids(candidate.dependency_ids, "dependency_ids", maximum=MAX_DEPENDENCIES),
    )
    if type(candidate.conflict_key) is not str:
        raise TypeError("conflict_key must be a string")
    if candidate.conflict_key:
        object.__setattr__(candidate, "conflict_key", _id(candidate.conflict_key, "conflict_key"))
    bindings = tuple(candidate.temporal_bindings)
    if len(bindings) > MAX_TEMPORAL_BINDINGS or any(
        type(item) is not TemporalBinding for item in bindings
    ):
        raise ValueError("temporal_bindings must contain bounded exact TemporalBinding records")
    if len({item.key for item in bindings}) != len(bindings):
        raise ValueError("temporal_bindings contains duplicate binding keys")
    object.__setattr__(
        candidate,
        "temporal_bindings",
        tuple(sorted(bindings, key=lambda item: item.key)),
    )


def _validate_candidate_reference(candidate: Any) -> None:
    if candidate.availability is CandidateAvailability.AVAILABLE:
        if type(candidate.reference) is not CanonicalReference:
            raise ValueError("available candidate requires an exact CanonicalReference")
        return
    if candidate.reference is not None:
        raise ValueError("unavailable candidate must not carry a canonical reference")


def _validate_candidate_authority(candidate: Any) -> None:
    authoritative = {
        CandidateTruthClass.EXACT_CURRENT,
        CandidateTruthClass.DERIVED_VERIFIED,
    }
    if candidate.truth_class not in authoritative:
        if candidate.authority_class is not ContextAuthorityClass.ADVISORY_NONE:
            raise ValueError(
                "advisory/hypothesis/stale/unavailable candidates cannot carry authority"
            )
        return
    if candidate.reference is None or candidate.reference.truth_class != "EXACT":
        raise ValueError("authoritative read candidate requires an EXACT canonical reference")
    expected = (
        ContextAuthorityClass.CANONICAL_READ
        if candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
        else ContextAuthorityClass.DERIVED_READ
    )
    if candidate.authority_class is not expected:
        raise ValueError("candidate authority class does not match its truth class")
    if candidate.origin_ref != candidate.reference.canonical_ref:
        raise ValueError(
            "authoritative candidate origin_ref must equal its canonical reference origin"
        )
''')
# Helpers are globals resolved when instances are created; place before ProjectContextEdge.
edge_marker = '\n\n@dataclass(frozen=True)\nclass ProjectContextEdge:\n'
text = text.replace(edge_marker, candidate_helpers + edge_marker, 1)

# 2. Compilation constructor: make public-boundary parity checks independently readable.
compilation_class = '@dataclass(frozen=True)\nclass ProjectContextCompilation:\n'
compilation_pos = text.index(compilation_class)
comp_post = text.index('    def __post_init__(self) -> None:\n', compilation_pos)
comp_to_dict = text.index('    def to_dict(self, *, include_digest: bool = True)', comp_post)
compact_post = '''    def __post_init__(self) -> None:\n        _validate_compilation_identity(self)\n        selected = _canonical_compilation_candidates(self)\n        _validate_compilation_candidates(self, selected)\n        _canonicalize_compilation_edges(self, selected)\n        _validate_compilation_projection(self, selected)\n        _finalize_compilation(self)\n\n'''
text = text[:comp_post] + compact_post + text{comp_to_dict:]

compilation_helpers = dedent('''

def _validate_compilation_identity(compilation: ProjectContextCompilation) -> None:
    if compilation.version != PROJECT_CONTEXT_COMPILATION_VERSION:
        raise ValueError("unsupported project-context compilation version")
    object.__setattr__(compilation, "objective", _text(compilation.objective, "objective"))
    object.__setattr__(
        compilation,
        "objective_digest",
        _digest(compilation.objective_digest, "objective_digest"),
    )
    if compilation.objective_digest != stable_digest({"objective": compilation.objective}):
        raise ValueError("objective_digest is not bound to objective")
    if type(compilation.repository_identity) is not RepositoryIdentity:
        raise ValueError("compilation requires exact RepositoryIdentity")
    if compilation.projection is not None and type(compilation.projection) is not ProjectContextProjection:
        raise ValueError("projection must be exact ProjectContextProjection")
    if type(compilation.selection_receipt) is not ProjectionSelectionReceipt:
        raise ValueError("selection_receipt 