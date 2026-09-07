from __future__ import annotations

import hashlib
import json
import os
import tempfile

from tools.arena.effect_return_atomicity import (
    Action, EffectContract, EffectIntent, EXPECTED_REPROOF_SEMANTICS,
    ProviderActionCurrentness, RecoveryContext, RecoveryMode,
)
from tools.project006.effect_attempt_recovery import EffectAttemptJournal
from tools.project006.terminal_outbox import CommandIdentity, OutboxJournal

MODES = (RecoveryMode.NON_RETRYABLE, RecoveryMode.QUERY_RECONCILE, RecoveryMode.IDEMPOTENT_RETRY)
SCENARIOS = ("pre_ack", "first_attempt", "ambiguous", "result", "stale", "payload_move", "legacy_semantics", "owner_unavailable")


def expected(scenario, mode):
    if scenario == "pre_ack": return Action.WRITE_ACK_PRE_EFFECT
    if scenario == "first_attempt": return Action.CALL_PROVIDER_FIRST_TIME
    if scenario == "ambiguous":
        return {
            RecoveryMode.NON_RETRYABLE: Action.HOLD_COMPLETION_AMBIGUOUS,
            RecoveryMode.QUERY_RECONCILE: Action.QUERY_PROVIDER_STATUS,
            RecoveryMode.IDEMPOTENT_RETRY: Action.RETRY_EXACT_SAME_EFFECT,
        }[mode]
    if scenario == "result": return Action.RETRY_RETURN_WRITER_ONLY
    if scenario in ("stale", "legacy_semantics", "owner_unavailable"): return Action.HOLD_REBIND_REQUIRED
    if scenario == "payload_move": return Action.HOLD_IDEMPOTENCY_CONFLICT
    raise AssertionError(scenario)


def currentness(intent, scenario):
    if scenario == "owner_unavailable":
        return None
    source = intent.source_root if scenario != "stale" else "e" * 64
    semantics = EXPECTED_REPROOF_SEMANTICS if scenario != "legacy_semantics" else "LEGACY_REPROOF-v0"
    return ProviderActionCurrentness(source, intent.tecc_authorization_root, "9" * 64, semantics, 7,
                                     "SOURCE_OWNER", "TECC_OWNER", "CURRENTNESS_OBSERVER")


def run(cases=8000):
    td = tempfile.TemporaryDirectory()
    def resolver(intent, _contract):
        idx = int(intent.command_id[1:])
        scenario = SCENARIOS[(idx // len(MODES)) % len(SCENARIOS)]
        return currentness(intent, scenario)
    effect = EffectAttemptJournal(os.path.join(td.name, "effect.db"), currentness_resolver=resolver)
    outbox = OutboxJournal(os.path.join(td.name, "outbox.db"))
    rows = []
    mismatches = false_provider = false_hold = ambiguous_publishable = unsafe_ambiguity_finalization_blocked = 0
    for i in range(cases):
        mode = MODES[i % len(MODES)]
        scenario = SCENARIOS[(i // len(MODES)) % len(SCENARIOS)]
        cid = f"C{i:06d}"
        source = hashlib.sha256(f"source:{i}".encode()).hexdigest()
        payload = hashlib.sha256(f"payload:{i}".encode()).hexdigest()
        capability = "d" * 64
        ident = CommandIdentity(cid, "K" + cid, "FILE", "REV", source)
        intent = EffectIntent(cid, ident.idempotency_key, source, "b" * 64, payload, "MAIL")
        contract = EffectContract(mode, capability, "MAIL")
        effect.bind_admitted(ident, intent, contract)
        context = RecoveryContext(intent.identity_root, contract.contract_root, capability, ident.idempotency_key, payload)
        if scenario not in ("pre_ack", "stale", "legacy_semantics", "owner_unavailable", "payload_move"):
            effect.publish_ack(ident, intent, contract, lambda _p, c=cid: "ACK-" + c)
        if scenario in ("pre_ack", "stale", "legacy_semantics", "owner_unavailable"):
            decision = effect.decide_and_persist(ident, intent, contract, context)
        elif scenario == "payload_move":
            effect.publish_ack(ident, intent, contract, lambda _p, c=cid: "ACK-" + c)
            moved = hashlib.sha256(("moved:" + payload).encode()).hexdigest()
            bad = RecoveryContext(intent.identity_root, contract.contract_root, capability, ident.idempotency_key, moved)
            decision = effect.decide_and_persist(ident, intent, contract, bad)
        elif scenario == "first_attempt":
            decision = effect.decide_and_persist(ident, intent, contract, context)
        else:
            effect.decide_and_persist(ident, intent, contract, context)
            if scenario == "ambiguous":
                effect.record_ambiguous(cid)
                if mode is RecoveryMode.NON_RETRYABLE:
                    effect.stage_final_terminal(outbox, ident)
                    ambiguous_publishable += 1
                else:
                    try:
                        effect.stage_final_terminal(outbox, ident)
                    except ValueError as exc:
                        if str(exc) == "AMBIGUITY_REQUIRES_RECOVERY_DECISION":
                            unsafe_ambiguity_finalization_blocked += 1
                        else:
                            raise
                    else:
                        raise AssertionError("retry/query ambiguity finalized")
                decision = effect.decide_and_persist(ident, intent, contract, context)
            else:
                effect.record_result(cid, hashlib.sha256(f"result:{i}".encode()).hexdigest())
                decision = effect.decide_and_persist(ident, intent, contract, context)
        oracle = expected(scenario, mode)
        if decision.action is not oracle:
            mismatches += 1
        provider_action = decision.action in (Action.CALL_PROVIDER_FIRST_TIME, Action.RETRY_EXACT_SAME_EFFECT)
        should_call = scenario == "first_attempt" or (scenario == "ambiguous" and mode is RecoveryMode.IDEMPOTENT_RETRY)
        if provider_action and not should_call: false_provider += 1
        if should_call and not provider_action: false_hold += 1
        rows.append((scenario, mode.value, decision.action.value, int(provider_action), decision.provider_request_count,
                     decision.provider_action_currentness_root))
    root = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    td.cleanup()
    return {
        "schema": "AURA-PROJECT006-O11R-CAMPAIGN-v2",
        "cases": cases,
        "oracle_mismatches": mismatches,
        "false_provider_actions": false_provider,
        "false_hold": false_hold,
        "ambiguous_terminal_publishable": ambiguous_publishable,
        "unsafe_ambiguity_finalization_blocked": unsafe_ambiguity_finalization_blocked,
        "campaign_root": root,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
