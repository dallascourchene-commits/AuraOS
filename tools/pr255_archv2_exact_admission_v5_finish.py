from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
CONTRACT = ROOT / "aura_ephemeral_workspace_contracts.py"
SCHEMA = ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json"
TESTS = ROOT / "tests/test_aura_ephemeral_workspace_contracts.py"
DOCS = ROOT / "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one replacement target, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def replace_in_section(path: Path, start: str, end: str, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    section = text[start_index:end_index]
    count = section.count(old)
    if count != 1:
        raise RuntimeError(
            f"{path}: expected one target in section {start!r}, found {count}"
        )
    section = section.replace(old, new)
    path.write_text(text[:start_index] + section + text[end_index:], encoding="utf-8")


replace_once(
    CONTRACT,
    '''    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityEnvelope":
        """Parse an exact serialized authority envelope."""
        detached = _detached_serialized_record(
            payload, {field.name for field in fields(cls)}, "authority"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
        return record


@dataclass(frozen=True)
class CanonicalReference:
''',
    '''    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityEnvelope":
        """Parse an exact serialized authority envelope."""
        detached = _detached_serialized_record(
            payload, {field.name for field in fields(cls)}, "authority"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
        return record


def _exact_authority_envelope(value: Any, name: str) -> AuthorityEnvelope:
    """Admit only the exact record type or one detached serialized mapping."""
    if type(value) is AuthorityEnvelope:
        return value
    if isinstance(value, Mapping):
        return AuthorityEnvelope.from_dict(value)
    raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")


@dataclass(frozen=True)
class CanonicalReference:
''',
)

authority_old = '''        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
'''
replace_in_section(
    CONTRACT,
    "class ProjectContextProjection:",
    "class WorkspaceBudget:",
    authority_old,
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "project.authority"),
        )
''',
)
replace_in_section(
    CONTRACT,
    "class EphemeralWorkspaceRecipe:",
    "class SpatialReferentBinding:",
    authority_old,
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "recipe.authority"),
        )
''',
)
replace_in_section(
    CONTRACT,
    "class MultimodalSpatialObservation:",
    "def validate_project_semantics",
    authority_old,
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "observation.authority"),
        )
''',
)

replace_once(
    SCHEMA,
    '''    "wall_time_ttl_binding": "mandatory semantic validator",
    "recipe_digest_equality": "mandatory semantic validator",
''',
    '''    "wall_time_ttl_binding": "mandatory semantic validator",
    "base_manifest_resource_budget_binding": "mandatory semantic validator",
    "recipe_digest_equality": "mandatory semantic validator",
''',
)
replace_once(
    SCHEMA,
    '''    "wall-time budget to TTL binding delegated to mandatory semantic validation",
    "recipe digest equality delegated to mandatory semantic validation",
''',
    '''    "wall-time budget to TTL binding delegated to mandatory semantic validation",
    "base-manifest and trusted compiled-recipe resource ceilings delegated to mandatory semantic validation",
    "recipe digest equality delegated to mandatory semantic validation",
''',
)

new_tests = '''\n\ndef test_enum_backed_strings_fail_before_record_signing() -> None:
    """String-backed enums cannot survive as signed record fields."""
    class Freshness(str, Enum):
        CURRENT = "CURRENT"

    class Evidence(str, Enum):
        DERIVED = "DERIVED"

    with pytest.raises(ValueError, match="project.freshness_class must be a string"):
        replace(
            project(),
            freshness_class=Freshness.CURRENT,
            projection_digest="",
        )
    with pytest.raises(ValueError, match="observation.evidence_class must be a string"):
        replace(
            observation(),
            evidence_class=Evidence.DERIVED,
            observation_digest="",
        )


def test_numeric_subclasses_cannot_spoof_json_or_budget_bounds() -> None:
    """Overloaded numeric subclasses are rejected before comparisons or hashing."""
    class SpoofInt(int):
        def __abs__(self) -> int:
            return 0

        def __ge__(self, other: object) -> bool:
            return True

        def __le__(self, other: object) -> bool:
            return True

    class SpoofFloat(float):
        pass

    hostile = SpoofInt(workspace_contracts.MAX_INTEGER + 1)
    with pytest.raises(ValueError, match="budget.memory_mb must be an integer"):
        WorkspaceBudget(memory_mb=hostile)
    with pytest.raises(ValueError, match="non-JSON value: SpoofInt"):
        canonical_json(hostile)
    with pytest.raises(ValueError, match="must be a finite JSON number"):
        workspace_contracts._finite_number(SpoofFloat(0.5), "hostile.float")
    with pytest.raises(ValueError, match="must be a JSON number"):
        workspace_contracts._prob(SpoofFloat(0.5), "hostile.probability")


def test_authority_subclasses_are_not_trusted_as_exact_records() -> None:
    """Authority subclasses cannot override serialization and become signed."""
    class ForgedAuthority(workspace_contracts.AuthorityEnvelope):
        def to_dict(self) -> dict[str, Any]:
            payload = super().to_dict()
            payload["automatic_merge"] = True
            return payload

    forged = ForgedAuthority()
    cases = (
        (project(), "projection_digest", "project.authority"),
        (recipe()[0], "recipe_digest", "recipe.authority"),
        (observation(), "observation_digest", "observation.authority"),
    )
    for record, digest_field, authority_name in cases:
        with pytest.raises(
            ValueError,
            match=rf"{authority_name} must be an exact AuthorityEnvelope",
        ):
            replace(record, authority=forged, **{digest_field: ""})
'''
replace_once(
    TESTS,
    '''\n\ndef test_schema_delegation_matches_canonical_path_and_text_policy() -> None:
''',
    new_tests + '''\n\ndef test_schema_delegation_matches_canonical_path_and_text_policy() -> None:
''',
)
replace_once(
    TESTS,
    '''        for pattern in patterns:
            assert workspace_contracts.re.fullmatch(pattern, "src/credential.txt")
            assert workspace_contracts.re.fullmatch(pattern, "src/credentials.txt") is None

    p = project()
''',
    '''        for pattern in patterns:
            assert workspace_contracts.re.fullmatch(pattern, "src/credential.txt")
            assert workspace_contracts.re.fullmatch(pattern, "src/credentials.txt") is None

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    assert recipe_schema["x-aura-semantic-delegations"][
        "base_manifest_resource_budget_binding"
    ] == "mandatory semantic validator"
    assert (
        "base-manifest and trusted compiled-recipe resource ceilings delegated to mandatory semantic validation"
        in recipe_schema["x-aura-semantic-invariants"]
    )

    p = project()
''',
)

replace_once(DOCS, "The focused suite contains **40 tests**", "The focused suite contains **43 tests**")
replace_once(DOCS, "- focused tests: **40 passed**;", "- focused tests: **43 passed**;")
replace_once(
    DOCS,
    "- strict bounded canonicalization and recursion handling;",
    "- strict bounded canonicalization, exact built-in scalar admission, and recursion handling;",
)
replace_once(
    DOCS,
    "- manifest/recipe TTL and budget ceilings;",
    "- manifest/recipe TTL, complete resource-budget ceilings, and exact authority-record admission;",
)
