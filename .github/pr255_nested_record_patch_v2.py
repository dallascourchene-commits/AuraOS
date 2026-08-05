from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


code_path = Path("aura_ephemeral_workspace_contracts.py")
code = code_path.read_text(encoding="utf-8")

code = replace_once(
    code,
    '    raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")\n\n\n@dataclass(frozen=True)\nclass CanonicalReference:',
    '    raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")\n\n\ndef _exact_contract_record(value: Any, record_type: type[Any], name: str) -> Any:\n    """Admit an exact contract record or parse one detached serialized mapping."""\n    if type(value) is record_type:\n        return value\n    if isinstance(value, Mapping):\n        return record_type.from_dict(value)\n    raise ValueError(\n        f"{name} must be an exact {record_type.__name__} or serialized object"\n    )\n\n\n@dataclass(frozen=True)\nclass CanonicalReference:',
    "generic exact-record helper",
)

code = replace_once(
    code,
    '        reference = raw_reference if isinstance(raw_reference, CanonicalReference) else CanonicalReference.from_dict(raw_reference)\n',
    '        reference = _exact_contract_record(\n            raw_reference, CanonicalReference, f"{name} reference"\n        )\n',
    "reference-map exactness",
)

code = replace_once(
    code,
    '        if not isinstance(self.repository_identity, RepositoryIdentity):\n            object.__setattr__(self, "repository_identity", RepositoryIdentity.from_dict(self.repository_identity))\n',
    '        object.__setattr__(\n            self,\n            "repository_identity",\n            _exact_contract_record(\n                self.repository_identity,\n                RepositoryIdentity,\n                "project.repository_identity",\n            ),\n        )\n',
    "repository identity exactness",
)

code = replace_once(
    code,
    '            refs = tuple(item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item) for item in items)\n',
    '            refs = tuple(\n                _exact_contract_record(\n                    item, CanonicalReference, f"project.{name} item"\n                )\n                for item in items\n            )\n',
    "project reference exactness",
)

code = replace_once(
    code,
    '    result = tuple(\n        item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item)\n        for item in items\n    )\n',
    '    result = tuple(\n        _exact_contract_record(item, CanonicalReference, f"{name} item")\n        for item in items\n    )\n',
    "recipe reference exactness",
)

code = replace_once(
    code,
    '        if not isinstance(self.base_manifest_ref, CanonicalReference):\n            object.__setattr__(self, "base_manifest_ref", CanonicalReference.from_dict(self.base_manifest_ref))\n',
    '        object.__setattr__(\n            self,\n            "base_manifest_ref",\n            _exact_contract_record(\n                self.base_manifest_ref,\n                CanonicalReference,\n                "recipe.base_manifest_ref",\n            ),\n        )\n',
    "base-manifest reference exactness",
)

code = replace_once(
    code,
    '        if not isinstance(self.budgets, WorkspaceBudget):\n            object.__setattr__(self, "budgets", WorkspaceBudget.from_dict(self.budgets))\n',
    '        object.__setattr__(\n            self,\n            "budgets",\n            _exact_contract_record(self.budgets, WorkspaceBudget, "recipe.budgets"),\n        )\n',
    "recipe budget exactness",
)

code = replace_once(
    code,
    '        expected_manifest = expected_base_manifest_ref if isinstance(expected_base_manifest_ref, CanonicalReference) else CanonicalReference.from_dict(expected_base_manifest_ref)\n',
    '        expected_manifest = _exact_contract_record(\n            expected_base_manifest_ref,\n            CanonicalReference,\n            "expected_base_manifest_ref",\n        )\n',
    "expected manifest reference exactness",
)

code = replace_once(
    code,
    '        if not isinstance(self.evidence_ref, CanonicalReference):\n            object.__setattr__(self, "evidence_ref", CanonicalReference.from_dict(self.evidence_ref))\n',
    '        object.__setattr__(\n            self,\n            "evidence_ref",\n            _exact_contract_record(\n                self.evidence_ref,\n                CanonicalReference,\n                "referent.evidence_ref",\n            ),\n        )\n',
    "referent evidence exactness",
)

code = replace_once(
    code,
    '    elif isinstance(budgets, WorkspaceBudget):\n        budget = budgets\n    else:\n        budget = WorkspaceBudget.from_dict(budgets)\n',
    '    else:\n        budget = _exact_contract_record(budgets, WorkspaceBudget, "budgets")\n',
    "compiler budget exactness",
)

for fragment in (
    "isinstance(raw_reference, CanonicalReference)",
    "isinstance(item, CanonicalReference)",
    "isinstance(self.repository_identity, RepositoryIdentity)",
    "isinstance(self.base_manifest_ref, CanonicalReference)",
    "isinstance(self.budgets, WorkspaceBudget)",
    "isinstance(expected_base_manifest_ref, CanonicalReference)",
    "isinstance(self.evidence_ref, CanonicalReference)",
    "isinstance(budgets, WorkspaceBudget)",
):
    if fragment in code:
        raise SystemExit(f"stale subclass-retaining branch remains: {fragment}")

code_path.write_text(code, encoding="utf-8")

test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text(encoding="utf-8")
marker = "def test_nested_contract_subclasses_are_rejected_before_parent_signing()"
if marker in tests:
    raise SystemExit("nested-record regression already exists")
tests += '''\n\n\ndef test_nested_contract_subclasses_are_rejected_before_parent_signing() -> None:\n    """Nested records must be exact types or detached serialized mappings."""\n    class RedirectedReference(CanonicalReference):\n        def to_dict(self) -> dict[str, Any]:\n            payload = super().to_dict()\n            payload["owner"] = "attacker.owner"\n            return payload\n\n    class RedirectedRepository(RepositoryIdentity):\n        def to_dict(self) -> dict[str, Any]:\n            payload = super().to_dict()\n            payload["repository"] = "attacker/repository"\n            return payload\n\n    class RedirectedBudget(WorkspaceBudget):\n        def to_dict(self) -> dict[str, int]:\n            payload = super().to_dict()\n            payload["memory_mb"] = 1\n            return payload\n\n    redirected_reference = RedirectedReference(\n        "adapter:subclass",\n        "canonical.owner",\n        "owner://adapter:subclass",\n        D["2"],\n    )\n    with pytest.raises(ValueError, match="exact CanonicalReference"):\n        recipe(adapters=(redirected_reference,))\n\n    trusted_project = project()\n    repository = trusted_project.repository_identity\n    redirected_repository = RedirectedRepository(\n        repository.repository,\n        repository.ref,\n        repository.commit_sha,\n        repository.source_tree_digest,\n    )\n    with pytest.raises(ValueError, match="exact RepositoryIdentity"):\n        replace(trusted_project, repository_identity=redirected_repository)\n\n    redirected_budget = RedirectedBudget(memory_mb=512)\n    with pytest.raises(ValueError, match="exact WorkspaceBudget"):\n        recipe(budgets=redirected_budget)\n'''
test_path.write_text(tests, encoding="utf-8")

docs_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
docs = docs_path.read_text(encoding="utf-8")
docs = replace_once(
    docs,
    "The focused suite contains **43 tests** covering the original review waves plus the structural repair:",
    "The focused suite contains **44 tests** covering the original review waves plus the structural repair:",
    "documentation test count",
)
docs = replace_once(
    docs,
    "- manifest/recipe TTL, complete resource-budget ceilings, and exact authority-record admission;",
    "- manifest/recipe TTL, complete resource-budget ceilings, and exact authority/nested-record admission;",
    "documentation nested-record coverage",
)
docs = replace_once(
    docs,
    "- focused tests: **43 passed**;",
    "- focused tests: **44 passed**;",
    "documentation verification receipt",
)
docs_path.write_text(docs, encoding="utf-8")
