# Aura Phase Capsules + Audit Trail

## Phase Capsules

Phase capsules carry phase-specific context between workflow gates. They become the persistent state object between cockpit checkpoints.

### Functions
- `plan_objective_with_goap(objective)` — decompose into phases via GOAP
- `objective_to_phase_capsules(objective)` — create phase capsules
- `phase_capsules_to_workflow_gates(capsules)` — map to gate states
- `phase_capsules_to_agent_runbook(capsules)` — convert to runbook

### Phase Sequence
1. Discovery phase
2. Grounding phase
3. Planning phase
4. Agent handoff phase
5. Patch phase
6. Verification phase
7. Repair phase
8. Approval phase
9. PR phase

Each phase includes: allowed_actions, blocked_actions, required_evidence, token_budget, output_packet, human_approval_required.

## Audit Trail

The audit trail records workflow gate transitions, human approvals, agent handoffs, verifier results, and research evidence. It works offline with optional blockchain/memory staking.

### Functions
- `record_gate_transition(from_state, to_state)` — record transition
- `record_human_approval(gate_state)` — record approval
- `record_agent_handoff(agent, handoff_packet)` — record handoff
- `record_verifier_result(result)` — record verifier result
- `record_research_evidence(evidence_packet)` — record evidence
- `export_cockpit_audit_packet()` — export full audit trail

## CLI

```powershell
python -m aura_agent_arena_cli phase-capsules --objective "..."
python -m aura_agent_arena_cli live-stage-plan --objective "..."
python -m aura_agent_arena_cli cockpit-audit --objective "..."
```

## Safety
- Audit trail works offline. Blockchain/staking optional.
- Fail closed: if audit backend fails, return warning and continue.
- No raw sidecar/private memory dump.
- `patch_authority: "exact_source_spans_and_hashes_only"`
