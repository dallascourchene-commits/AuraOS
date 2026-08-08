from pathlib import Path

p = Path("aura_project_context_compiler.py")
s = p.read_text()
marker = '''\n\ndef _validate_compilation_identity(compilation: Any) -> None:\n'''
helper = '''\n\ndef _revalidate_selection_receipt(receipt: Any) -> ProjectionSelectionReceipt:\n    \"\"\"Reconstruct the receipt and nested budget before public admission.\"\"\"\n    if type(receipt) is not ProjectionSelectionReceipt:\n        raise ValueError(\"selection_receipt must be exact ProjectionSelectionReceipt\")\n    budget = receipt.budget\n    if type(budget) is not ProjectionBudget:\n        raise ValueError(\"selection receipt requires exact ProjectionBudget\")\n    try:\n        canonical_budget = ProjectionBudget(budget.max_nodes, budget.max_edges)\n    except Exception as exc:\n        raise ValueError(\"selection receipt budget failed revalidation\") from exc\n    try:\n        rebuilt = ProjectionSelectionReceipt(\n            objective_digest=receipt.objective_digest,\n            repository_identity_digest=receipt.repository_identity_digest,\n            canonical_owner=receipt.canonical_owner,\n            selected=receipt.selected,\n            omitted_irrelevant=receipt.omitted_irrelevant,\n            omitted_by_budget=receipt.omitted_by_budget,\n            stale=receipt.stale,\n            unavailable=receipt.unavailable,\n            conflicting=receipt.conflicting,\n            source_adapter_missing=receipt.source_adapter_missing,\n            mandatory_evidence_missing=receipt.mandatory_evidence_missing,\n            status=receipt.status,\n            budget=canonical_budget,\n            receipt_digest=receipt.receipt_digest,\n            version=receipt.version,\n        )\n    except Exception as exc:\n        if isinstance(exc, ValueError) and str(exc) == \"selection receipt digest mismatch\":\n            raise\n        raise ValueError(\"selection receipt failed canonical revalidation\") from exc\n    try:\n        if rebuilt.to_dict() != receipt.to_dict():\n            raise ValueError(\"selection receipt is not in canonical form\")\n    except ValueError:\n        raise\n    except Exception as exc:\n        raise ValueError(\"selection receipt failed canonical revalidation\") from exc\n    return rebuilt\n'''
assert s.count(marker) == 1, "compilation identity marker"
s = s.replace(marker, helper + marker, 1)
old = '''    if type(compilation.selection_receipt) is not ProjectionSelectionReceipt:\n        raise ValueError(\n            \"selection_receipt must be exact ProjectionSelectionReceipt\"\n        )\n    if compilation.selection_receipt.objective_digest != compilation.objective_digest:\n'''
new = '''    canonical_receipt = _revalidate_selection_receipt(compilation.selection_receipt)\n    object.__setattr__(compilation, \"selection_receipt\", canonical_receipt)\n    if compilation.selection_receipt.objective_digest != compilation.objective_digest:\n'''
assert s.count(old) == 1, "receipt identity anchor"
s = s.replace(old, new, 1)
p.write_text(s.rstrip() + "\n")

t = Path("tests/test_aura_project_context_acceptance.py")
x = t.read_text().rstrip()
block = '''


def test_public_compilation_rejects_low_level_tampered_selection_receipt_vector() -> None:
    complete = _compile((_source(),))
    receipt = complete.selection_receipt
    object.__setattr__(receipt, "selected", ("source:target", "source:forged"))

    with pytest.raises(ValueError, match="selection receipt digest mismatch"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=receipt,
            selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_low_level_tampered_receipt_node_budget() -> None:
    complete = _compile((_source(),))
    receipt = complete.selection_receipt
    object.__setattr__(receipt.budget, "max_nodes", 257)

    with pytest.raises(ValueError, match="selection receipt budget failed revalidation"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=receipt,
            selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_low_level_tampered_receipt_edge_budget() -> None:
    complete = _compile((_source(),))
    receipt = complete.selection_receipt
    object.__setattr__(receipt.budget, "max_edges", 1025)

    with pytest.raises(ValueError, match="selection receipt budget failed revalidation"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=receipt,
            selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges, admissible=True,
        )
'''
assert "test_public_compilation_rejects_low_level_tampered_selection_receipt_vector" not in x
t.write_text((x + block).rstrip() + "\n")

d = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")
y = d.read_text()
needle = '- hand-assembled selected candidates contain low-level-tampered `CanonicalReference` or `TemporalBinding` records that no longer pass their canonical constructors;\n'
repl = needle + '- hand-assembled compilations contain a low-level-tampered selection receipt or nested projection budget whose canonical reconstruction or receipt digest no longer matches;\n'
assert y.count(needle) == 1, "receipt doc anchor"
d.write_text(y.replace(needle, repl, 1).rstrip() + "\n")
