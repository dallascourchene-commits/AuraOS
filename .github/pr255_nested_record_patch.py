from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    code_path = Path("aura_ephemeral_workspace_contracts.py")
    code = code_path.read_text(encoding="utf-8")

    code = replace_once(
        code,
        dedent('''\
        def _exact_authority_envelope(value: Any, name: str) -> AuthorityEnvelope:
            """Admit only the exact record type or one detached serialized mapping."""
            if type(value) is AuthorityEnvelope:
                return value
            if isinstance(value, Mapping):
                return AuthorityEnvelope.from_dict(value)
            raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")


        @dataclass(frozen=True)
        class CanonicalReference:
        '''),
        dedent('''\
        def _exact_authority_envelope(value: Any, name: str) -> AuthorityEnvelope:
            """Admit only the exact record type or one detached serialized mapping."""
            if type(value) is AuthorityEnvelope:
                return value
            if isinstance(value, Mapping):
                return AuthorityEnvelope.from_dict(value)
            raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")


        def _exact_contract_record(value: Any, record_type: type[Any], name: str) -> Any:
            """Admit an exact contract record or parse one detached serialized mapping."""
            if type(value) is record_type:
                return value
            if isinstance(value, Mapping):
                return record_type.from_dict(value)
            raise ValueError(
                f"{name} must be an exact {record_type.__name__} or serialized object"
            )


        @dataclass(frozen=True)
        class CanonicalReference:
        '''),
        "generic exact-record helper",
    )

    code = replace_once(
        code,
        '        reference = raw_reference if isinstance(raw_reference, CanonicalReference) else CanonicalReference.from_dict(raw_reference)\n',
        dedent('''\
                reference = _exact_contract_record(
                    raw_reference, CanonicalReference, f"{name} reference"
                )
        '''),
        "reference-map exactness",
    )

    code = replace_once(
        code,
        dedent('''\
                if not isinstance(self.repository_identity, RepositoryIdentity):
                    object.__setattr__(self, "repository_identity", RepositoryIdentity.from_dict(self.repository_identity))
        '''),
        dedent('''\
                object.__setattr__(
                    self,
                    "repository_identity",
                    _exact_contract_record(
                        self.repository_identity,
                        RepositoryIdentity,
                        "project.repository_identity",
                    ),
                )
        '''),
        "repository identity exactness",
    )

    code = replace_once(
        code,
        '            refs = tuple(item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item) for item in items)\n',
        dedent('''\
                    refs = tuple(
                        _exact_contract_record(
                            item, CanonicalReference, f"project.{name} item"
                        )
                        for item in items
                    )
        '''),
        "project reference exactness",
    )

    code = replace_once(
        code,
        dedent('''\
            result = tuple(
                item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item)
                for item in items
            )
        '''),
        dedent('''\
            result = tuple(
                _exact_contract_record(item, CanonicalReference, f"{name} item")
                for item in items
            )
        '''),
        "recipe reference exactness",
    )

    code = replace_once(
        code,
        dedent('''\
                if not isinstance(self.base_manifest_ref, CanonicalReference):
                    object.__setattr__(self, "base_manifest_ref", CanonicalReference.from_dict(self.base_manifest_ref))
        '''),
        dedent('''\
                object.__setattr__(
                    self,
                    "base_manifest_ref",
                    _exact_contract_record(
                        self.base_manifest_ref,
                        CanonicalReference,
                        "recipe.base_manifest_ref",
                    ),
                )
        '''),
        "base-manifest reference exactness",
    )

    code = replace_once(
        code,
        dedent('''\
                if not isinstance(self.budgets, WorkspaceBudget):
                    object.__setattr__(self, "budgets", WorkspaceBudget.from_dict(self.budgets))
        '''),
        dedent('''\
                object.__setattr__(
                    self,
                    "budgets",
                    _exact_contract_record(self.budgets, WorkspaceBudget, "recipe.budgets"),
                )
        '''),
        "recipe budget exactness",
    )

    code = replace_once(
        code,
        '        expected_manifest = expected_base_manifest_ref if isinstance(expected_base_manifest_ref, CanonicalReference) else CanonicalReference.from_dict(expected_base_manifest_ref)\n',
        dedent('''\
                expected_manifest = _exact_contract_record(
                    expected_base_manifest_ref,
                    CanonicalReference,
                    "expected_base_manifest_ref",
                )
        '''),
        "expected manifest reference exactness",
    )

    code = replace_once(
        code,
        dedent('''\
                if not isinstance(self.evidence_ref, CanonicalReference):
                    object.__setattr__(self, "evidence_ref", CanonicalReference.from_dict(self.evidence_ref))
        '''),
        dedent('''\
                object.__setattr__(
                    self,
                    "evidence_ref",
                    _exact_contract_record(
                        self.evidence_ref,
                        CanonicalReference,
                        "referent.evidence_ref",
                    ),
                )
        '''),
        "referent evidence exactness",
    )

    code = replace_once(
        code,
        dedent('''\
            elif isinstance(budgets, WorkspaceBudget):
                budget = budgets
            else:
                budget = WorkspaceBudget.from_dict(budgets)
        '''),
        dedent('''\
            else:
                budget = _exact_contract_record(budgets, WorkspaceBudget, "budgets")
        '''),
        "compiler budget exactness",
    )

    forbidden_fragments = (
        "isinstance(raw_reference, CanonicalReference)",
        "isinstance(item, CanonicalReference)",
        "isinstance(self.repository_identity, RepositoryIdentity)",
        "isinstance(self.base_manifest_ref, CanonicalReference)",
        "isinstance(self.budgets, WorkspaceBudget)",
        "isinstance(expected_base_manifest_ref, CanonicalReference)",
        "isinstance(self.evidence_ref, CanonicalReference)",
        "isinstance(budgets, WorkspaceBudget)",
    )
    for fragment in forbidden_fragments:
        if fragment in code:
            raise SystemExit(f"stale subclass-retaining branch remains: {fragment}")
    code_path.write_text(code, encoding="utf-8")

    test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
    tests = test_path.read_text(encoding="utf-8")
    marker = "def test_nested_contract_subclasses_are_rejected_before_parent_signing()"
    if marker in tests:
        raise SystemExit("nested-record regression already exists")
    tests += dedent('''\


    def test_nested_contract_subclasses_are_rejected_before_parent_signing() -> None:
        """Nested records must be exact types or detached serialized mappings."""
        class RedirectedReference(CanonicalReference):
            def to_dict(self) -> dict[str, Any]:
                payload = super().to_dict()
                payload["owner"] = "attacker.owner"
                return payload

        class RedirectedRepository(RepositoryIdentity):
            def to_dict(self) -> dict[str, Any]:
                payload = super().to_dict()
                payload["repository"] = "attacker/repository"
                return payload

        class RedirectedBudget(WorkspaceBudget):
            def to_dict(self) -> dict[str, int]:
                payload = super().to_dict()
                payload["memory_mb"] = 1
                return payload

        redirected_reference = RedirectedReference(
            "adapter:subclass",
            "canonical.owner",
            "owner://adapter:subclass",
            D["2"],
        )
        with pytest.raises(ValueError, match="exact CanonicalReference"):
            recipe(adapters=(redirected_reference,))

        trusted_project = project()
        repository = trusted_project.repository_identity
        redirected_repository = RedirectedRepository(
            repository.repository,
            repository.ref,
            repository.commit_sha,
            repository.source_tree_digest,
        )
        with pytest.raises(ValueError, match="exact RepositoryIdentity"):
            replace(trusted_project, repository_identity=redirected_repository)

        redirected_budget = RedirectedBudget(memory_mb=512)
        with pytest.raises(ValueError, match="exact WorkspaceBudget"):
            recipe(budgets=redirected_budget)
    '''))
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


if __name__ == "__main__":
    main()
