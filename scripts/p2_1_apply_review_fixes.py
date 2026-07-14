from pathlib import Path

SOURCE = Path("aura_planning_board.py")
TESTS = Path("tests/test_aura_planning_board.py")

source = SOURCE.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")

old_preconditions = '''        preconditions=tuple(
            PredicateSpec(str(key), value)
            for key, value in sorted(preconditions.items(), key=lambda item: str(item[0]))
        ),
'''
new_preconditions = '''        preconditions=tuple(
            PredicateSpec(
                str(key),
                value,
                PredicateOperator.IN
                if isinstance(value, (set, tuple, list))
                else PredicateOperator.EQ,
            )
            for key, value in sorted(preconditions.items(), key=lambda item: str(item[0]))
        ),
'''
if source.count(old_preconditions) != 1:
    raise SystemExit("expected one legacy precondition adapter block")
source = source.replace(old_preconditions, new_preconditions, 1)

old_constraint_block = '''        if item is None or not item.constrained_evidence_refs:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "MISSING_CONSTRAINT_EVIDENCE",
                "no exact reference proves current constraints are satisfiable",
                action.action_id,
            )
        if action.reversibility is ReversibilityClass.UNSPECIFIED:
'''
new_constraint_block = '''        if item is None or not item.constrained_evidence_refs:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "MISSING_CONSTRAINT_EVIDENCE",
                "no exact reference proves current constraints are satisfiable",
                action.action_id,
            )
        constrained = set(() if item is None else item.constrained_evidence_refs)
        required_constraint_refs = {
            reference
            for constraint in (*board.goal.constraints, *action.constraints)
            if constraint.blocking
            for reference in constraint.evidence_refs
        }
        unresolved_constraints = required_constraint_refs - constrained
        if unresolved_constraints:
            _finding(
                findings,
                BoardContinuityLevel.BC2_CONSTRAINED,
                "UNRESOLVED_CONSTRAINT_REFERENCE",
                f"declared constraint refs were not resolved: {sorted(unresolved_constraints)}",
                action.action_id,
            )
        if action.reversibility is ReversibilityClass.UNSPECIFIED:
'''
if source.count(old_constraint_block) != 1:
    raise SystemExit("expected one BC2 constraint block")
source = source.replace(old_constraint_block, new_constraint_block, 1)

old_import_one = '''    BoardContinuityLevel,
    EffectSpec,
'''
new_import_one = '''    BoardContinuityLevel,
    ConstraintKind,
    ConstraintSpec,
    EffectSpec,
'''
if tests.count(old_import_one) != 1:
    raise SystemExit("expected one first import insertion point")
tests = tests.replace(old_import_one, new_import_one, 1)

old_import_two = '''    PortSpec,
    PredicateSpec,
'''
new_import_two = '''    PortSpec,
    PredicateOperator,
    PredicateSpec,
'''
if tests.count(old_import_two) != 1:
    raise SystemExit("expected one second import insertion point")
tests = tests.replace(old_import_two, new_import_two, 1)

membership_test = '''def test_goap_adapter_preserves_membership_precondition_semantics() -> None:
    legacy = LegacyGoalAction()
    legacy.preconditions = {"mode": ("safe", "dry_run")}
    action = action_spec_from_goal_action(legacy)
    assert action.preconditions[0].fact == "mode"
    assert action.preconditions[0].expected == ("safe", "dry_run")
    assert action.preconditions[0].operator is PredicateOperator.IN


'''
marker = "def test_goal_plan_shadow_projection_is_stable_and_non_authoritative() -> None:\n"
if tests.count(marker) != 1:
    raise SystemExit("expected one membership test insertion point")
tests = tests.replace(marker, membership_test + marker, 1)

constraint_tests = '''


def test_declared_blocking_constraint_refs_must_be_resolved() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "constraints": (
                ConstraintSpec(
                    constraint_id="budget-check",
                    kind=ConstraintKind.BUDGET,
                    description="Budget must be available",
                    evidence_refs=("budget:available",),
                ),
            ),
        }
    )
    board = _board(action)
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("unrelated-check",),
                grounded_evidence_refs=("sidecar:source:abc",),
                authority_decision_ids=("decision:1",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC2_CONSTRAINED not in report.passed_levels
    assert "UNRESOLVED_CONSTRAINT_REFERENCE" in {
        finding.code for finding in report.findings
    }


def test_nonblocking_constraint_refs_do_not_block_bc2() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "constraints": (
                ConstraintSpec(
                    constraint_id="advisory",
                    kind=ConstraintKind.DOMAIN,
                    description="Advisory only",
                    evidence_refs=("advisory:1",),
                    blocking=False,
                ),
            ),
        }
    )
    board = _board(action)
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
            ),
        ),
    )
    assert "UNRESOLVED_CONSTRAINT_REFERENCE" not in {
        finding.code for finding in report.findings
    }
'''
if "def test_declared_blocking_constraint_refs_must_be_resolved" in tests:
    raise SystemExit("constraint regression tests already present")
tests = tests.rstrip() + constraint_tests + "\n"

SOURCE.write_text(source, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
