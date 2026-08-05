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


# Require exact built-in JSON scalar types before any overloaded comparison,
# conversion, abs(), or serialization behavior can influence admission.
replace_once(
    CONTRACT,
    '''    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON integer exceeds its numeric ceiling")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
''',
    '''    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON integer exceeds its numeric ceiling")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
''',
)
replace_once(
    CONTRACT,
    '''    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
''',
    '''    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
    if type(value) is float:
        if not math.isfinite(value) or abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
''',
)
replace_once(
    CONTRACT,
    '''def _finite_number(value: Any, name: str, *, minimum: float = 0.0) -> float:
    """Validate a finite non-boolean numeric value at or above a minimum."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite JSON number")
''',
    '''def _finite_number(value: Any, name: str, *, minimum: float = 0.0) -> float:
    """Validate an exact finite JSON number at or above a minimum."""
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite JSON number")
''',
)
replace_once(
    CONTRACT,
    '''def _bool(value: Any, name: str, required: bool) -> bool:
    """Require an exact boolean value."""
    if not isinstance(value, bool) or value is not required:
''',
    '''def _bool(value: Any, name: str, required: bool) -> bool:
    """Require an exact boolean value."""
    if type(value) is not bool or value is not required:
''',
)
replace_once(
    CONTRACT,
    '''def _int(value: Any, name: str, low: int, high: int) -> int:
    """Validate a bounded integer while rejecting booleans."""
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
''',
    '''def _int(value: Any, name: str, low: int, high: int) -> int:
    """Validate an exact bounded JSON integer."""
    if type(value) is not int or not low <= value <= high:
''',
)
replace_once(
    CONTRACT,
    '''def _prob(value: Any, name: str) -> int | float:
    """Validate an exact JSON numeric spelling in the inclusive unit interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
''',
    '''def _prob(value: Any, name: str) -> int | float:
    """Validate an exact JSON numeric spelling in the inclusive unit interval."""
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a JSON number")
    if type(value) is float and not math.isfinite(value):
''',
)

# Centralize exact built-in string admission for fixed and enumerated fields.
replace_once(
    CONTRACT,
    '''def _id(value: Any, name: str) -> str:
    """Validate an Aura identifier."""
    result = _text(value, name, maximum=192)
    if not _ID.fullmatch(result):
        raise ValueError(f"{name} contains unsupported characters")
    return result


def _digest(value: Any, name: str, *, optional: bool = False) -> str:
''',
    '''def _id(value: Any, name: str) -> str:
    """Validate an Aura identifier."""
    result = _text(value, name, maximum=192)
    if not _ID.fullmatch(result):
        raise ValueError(f"{name} contains unsupported characters")
    return result


def _fixed_text(value: Any, name: str, expected: str) -> str:
    """Require one exact built-in string constant."""
    result = _text(value, name, maximum=192)
    if result != expected:
        raise ValueError(f"{name} must be {expected}")
    return result


def _enum_text(value: Any, name: str, allowed: frozenset[str]) -> str:
    """Require an exact built-in string from a closed enumeration."""
    result = _text(value, name, maximum=64)
    if result not in allowed:
        raise ValueError(f"unsupported {name}")
    return result


def _digest(value: Any, name: str, *, optional: bool = False) -> str:
''',
)

# Fixed-record versions and enum/constant fields must be normalized before use.
replace_once(
    CONTRACT,
    '''        if self.version != AUTHORITY_ENVELOPE_VERSION:
            raise ValueError("unsupported authority version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "authority.version", AUTHORITY_ENVELOPE_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != CANONICAL_REFERENCE_VERSION:
            raise ValueError("unsupported reference version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "reference.version", CANONICAL_REFERENCE_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != REPOSITORY_IDENTITY_VERSION:
            raise ValueError("unsupported repository identity version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "repository.version", REPOSITORY_IDENTITY_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.freshness_class not in _FRESHNESS:
            raise ValueError("unsupported project freshness")
''',
    '''        object.__setattr__(
            self,
            "freshness_class",
            _enum_text(self.freshness_class, "project.freshness_class", _FRESHNESS),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.privacy_class != _PROJECT_PRIVACY_CLASS:
            raise ValueError(f"project.privacy_class must be {_PROJECT_PRIVACY_CLASS}")
        if self.egress_class != _PROJECT_EGRESS_CLASS:
            raise ValueError(f"project.egress_class must be {_PROJECT_EGRESS_CLASS}")
''',
    '''        object.__setattr__(
            self,
            "privacy_class",
            _fixed_text(self.privacy_class, "project.privacy_class", _PROJECT_PRIVACY_CLASS),
        )
        object.__setattr__(
            self,
            "egress_class",
            _fixed_text(self.egress_class, "project.egress_class", _PROJECT_EGRESS_CLASS),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != PROJECT_CONTEXT_PROJECTION_VERSION:
            raise ValueError("unsupported project version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "project.version", PROJECT_CONTEXT_PROJECTION_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.lifecycle_policy != _LIFECYCLE_POLICY:
            raise ValueError(f"recipe.lifecycle_policy must be {_LIFECYCLE_POLICY}")
        if self.dissolution_policy != _DISSOLUTION_POLICY:
            raise ValueError(f"recipe.dissolution_policy must be {_DISSOLUTION_POLICY}")
''',
    '''        object.__setattr__(
            self,
            "lifecycle_policy",
            _fixed_text(self.lifecycle_policy, "recipe.lifecycle_policy", _LIFECYCLE_POLICY),
        )
        object.__setattr__(
            self,
            "dissolution_policy",
            _fixed_text(self.dissolution_policy, "recipe.dissolution_policy", _DISSOLUTION_POLICY),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != EPHEMERAL_WORKSPACE_RECIPE_VERSION:
            raise ValueError("unsupported recipe version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "recipe.version", EPHEMERAL_WORKSPACE_RECIPE_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != SPATIAL_REFERENT_BINDING_VERSION:
            raise ValueError("unsupported referent version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "referent.version", SPATIAL_REFERENT_BINDING_VERSION),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.evidence_class not in _EVIDENCE:
            raise ValueError("unsupported observation evidence class")
''',
    '''        object.__setattr__(
            self,
            "evidence_class",
            _enum_text(self.evidence_class, "observation.evidence_class", _EVIDENCE),
        )
''',
)
replace_once(
    CONTRACT,
    '''        if self.version != MULTIMODAL_SPATIAL_OBSERVATION_VERSION:
            raise ValueError("unsupported observation version")
''',
    '''        object.__setattr__(
            self,
            "version",
            _fixed_text(
                self.version,
                "observation.version",
                MULTIMODAL_SPATIAL_OBSERVATION_VERSION,
            ),
        )
''',
)

# Only exact AuthorityEnvelope records or detached serialized mappings are admitted.
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
replace_once(
    CONTRACT,
    '''        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != PROJECT_CONTEXT_PROJECTION_VERSION:
''',
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "project.authority"),
        )
        if self.version != PROJECT_CONTEXT_PROJECTION_VERSION:
''',
)
replace_once(
    CONTRACT,
    '''        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != EPHEMERAL_WORKSPACE_RECIPE_VERSION:
''',
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "recipe.authority"),
        )
        if self.version != EPHEMERAL_WORKSPACE_RECIPE_VERSION:
''',
)
replace_once(
    CONTRACT,
    '''        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != MULTIMODAL_SPATIAL_OBSERVATION_VERSION:
''',
    '''        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "observation.authority"),
        )
        if self.version != MULTIMODAL_SPATIAL_OBSERVATION_VERSION:
''',
)

# Explicitly publish the source-manifest/compiled-recipe resource ceiling binding.
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

# Add adversarial regressions for each newly closed admission surface.
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
