from pathlib import Path

p = Path("aura_project_context_compiler.py")
s = p.read_text()

marker = '''\n\nclass CandidateCategory(str, Enum):\n'''
insert = '''\n\nclass _SelectionReceiptDigestMismatch(ValueError):\n    \"\"\"Identify deterministic receipt-integrity mismatch without string dispatch.\"\"\"\n\n\nclass CandidateCategory(str, Enum):\n'''
assert s.count(marker) == 1, "exception insertion anchor"
s = s.replace(marker, insert, 1)

old = '''    if receipt.receipt_digest and receipt.receipt_digest != expected:\n        raise ValueError("selection receipt digest mismatch")\n'''
new = '''    if receipt.receipt_digest and receipt.receipt_digest != expected:\n        raise _SelectionReceiptDigestMismatch("selection receipt digest mismatch")\n'''
assert s.count(old) == 1, "receipt digest raise anchor"
s = s.replace(old, new, 1)

old = '''    except Exception as exc:\n        if isinstance(exc, ValueError) and str(exc) == "selection receipt digest mismatch":\n            raise\n        raise ValueError("selection receipt failed canonical revalidation") from exc\n'''
new = '''    except _SelectionReceiptDigestMismatch:\n        raise\n    except Exception as exc:\n        raise ValueError("selection receipt failed canonical revalidation") from exc\n'''
assert s.count(old) == 1, "receipt exception dispatch anchor"
s = s.replace(old, new, 1)
p.write_text(s.rstrip() + "\n")

t = Path("tests/test_aura_project_context_acceptance.py")
x = t.read_text().rstrip()
block = '''


def test_recomputed_legal_budget_creates_new_compilation_identity_not_authenticity() -> None:
    complete = _compile((_source(),))
    receipt = complete.selection_receipt
    rebudgeted_receipt = ProjectionSelectionReceipt(
        objective_digest=receipt.objective_digest,
        repository_identity_digest=receipt.repository_identity_digest,
        canonical_owner=receipt.canonical_owner,
        selected=receipt.selected,
        omitted_irrelevant=receipt.omitted_irrelevant,
        omitted_by_budget=receipt.omitted_by_budget,
        stale=receipt.stale,
        unavailable=receipt.unavailable,
        conflicting=receipt.conflicting,
        source_adapter_missing=receipt.source_adapter_missing,
        mandatory_evidence_missing=receipt.mandatory_evidence_missing,
        status=receipt.status,
        budget=ProjectionBudget(max_nodes=32, max_edges=64),
    )

    rebudgeted = ProjectContextCompilation(
        project_ref=PROJECT_REF,
        objective=complete.objective,
        objective_digest=complete.objective_digest,
        repository_identity=complete.repository_identity,
        projection=complete.projection,
        selection_receipt=rebudgeted_receipt,
        selected_candidates=complete.selected_candidates,
        graph_edges=complete.graph_edges,
        admissible=True,
    )

    assert rebudgeted.selection_receipt.budget != complete.selection_receipt.budget
    assert rebudgeted.selection_receipt.receipt_digest != complete.selection_receipt.receipt_digest
    assert rebudgeted.compilation_digest != complete.compilation_digest
    assert rebudgeted.admissible is True
'''
assert "test_recomputed_legal_budget_creates_new_compilation_identity_not_authenticity" not in x
t.write_text((x + block).rstrip() + "\n")

d = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")
y = d.read_text()
needle = '''The receipt is bound to the objective digest, exact repository identity digest, and canonical project owner.\n\nA `COMPLETE` receipt cannot contain missing mandatory evidence. An `INCOMPLETE` receipt must expose at least one missing mandatory item.\n'''
replacement = '''The receipt is bound to the objective digest, exact repository identity digest, and canonical project owner.\n\n`receipt_digest` is a deterministic integrity checksum over receipt content. It is **not** an authenticity signature, authorization token, or proof that a particular budget was approved by an external authority. A stale or low-level-mutated receipt whose carried digest no longer matches its content fails closed. A caller that deliberately chooses another globally legal budget and recomputes the dependent receipt and compilation digests creates a **new compilation identity**; PR3 does not claim that local self-hashes can authenticate a prior budget. Budget authorization, if required by a host, must come from Aura's existing external authority/capability controls rather than a second signing plane inside PR3.\n\nA `COMPLETE` receipt cannot contain missing mandatory evidence. An `INCOMPLETE` receipt must expose at least one missing mandatory item.\n'''
assert y.count(needle) == 1, "receipt contract doc anchor"
y = y.replace(needle, replacement, 1)
y = y.replace(
    "- selected candidates exceed signed node/edge budgets, have incomplete dependency closure, or graph edges reference candidates outside the task-conditioned set;",
    "- selected candidates exceed the receipt-declared node/edge budgets, have incomplete dependency closure, or graph edges reference candidates outside the task-conditioned set;",
)
security_needle = '- hand-assembled compilations contain a low-level-tampered selection receipt or nested projection budget whose canonical reconstruction or receipt digest no longer matches;\n'
security_repl = security_needle + '- receipt and compilation digests are treated as deterministic integrity identities only; PR3 does not misrepresent them as authenticated budget signatures or create a second authority/signing plane;\n'
assert y.count(security_needle) == 1, "security contract anchor"
y = y.replace(security_needle, security_repl, 1)
d.write_text(y.rstrip() + "\n")
