from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tools.arena.effect_return_atomicity import (
    Action, EffectContract, EffectIntent, Phase, RecoveryContext,
    decide_recovery, effect_attempt_root,
)
from tools.project006.effect_attempt_recovery import EffectAttemptJournal, ProviderActionPermit
from tools.project006.o4_owner_row_convergence import (
    ProofAdmission, SemanticEffectIdentity, persist_owner_bound_provider_attempt,
    proof_action_currentness_root, stable_provider_operation_root,
)
from tools.project006.terminal_outbox import CommandIdentity

ProofAdmissionResolver = Callable[[CommandIdentity, EffectIntent, EffectContract], ProofAdmission | None]
NowResolver = Callable[[], int]


@dataclass(frozen=True)
class O4ProviderActionPermit(ProviderActionPermit):
    stable_provider_operation_root: str | None = None
    proof_bound_admission_root: str | None = None
    proof_action_currentness_root: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.action in (Action.CALL_PROVIDER_FIRST_TIME, Action.RETRY_EXACT_SAME_EFFECT):
            if not self.stable_provider_operation_root or not self.proof_bound_admission_root or not self.proof_action_currentness_root:
                raise ValueError("O4_PROVIDER_ACTION_REQUIRES_PROOF_OPERATION_BINDING")


class O4EffectAttemptJournal(EffectAttemptJournal):
    """Owner-adoption replacement for PR899's provider-candidate path.

    It reuses the exact PR899 effect_tx owner and transaction. No sidecar and no
    second journal exist. All inherited ACK/result/terminal-return ownership stays
    with PR899; only CALL/RETRY candidate persistence is strengthened.
    """

    def __init__(self, path, *, currentness_resolver, proof_admission_resolver: ProofAdmissionResolver,
                 now_resolver: NowResolver):
        super().__init__(path, currentness_resolver=currentness_resolver)
        self.proof_admission_resolver = proof_admission_resolver
        self.now_resolver = now_resolver

    @staticmethod
    def _semantic(ident: CommandIdentity, intent: EffectIntent, contract: EffectContract) -> SemanticEffectIdentity:
        return SemanticEffectIdentity(
            ident.command_id, ident.idempotency_key, ident.source_file_id, ident.source_revision,
            ident.source_digest, intent.identity_root, contract.contract_root,
            intent.effect_payload_root, contract.recovery_mode.value,
        )

    @staticmethod
    def _permit(action: Action, ident: CommandIdentity, row, currentness_root: str | None = None) -> O4ProviderActionPermit:
        return O4ProviderActionPermit(
            action, ident.command_id, row["intent_root"], row["contract_root"], row["effect_attempt_root"],
            row["provider_request_count"], currentness_root,
            stable_provider_operation_root=row.get("stable_provider_operation_root"),
            proof_bound_admission_root=row.get("proof_bound_admission_root"),
            proof_action_currentness_root=row.get("proof_action_currentness_root"),
        )

    def decide_and_persist(self, ident: CommandIdentity, intent: EffectIntent, contract: EffectContract,
                           context: RecoveryContext) -> O4ProviderActionPermit:
        self._bind(ident, intent, contract)
        with self._con(immediate=True) as con:
            row = con.execute("SELECT * FROM effect_tx WHERE command_id=?", (ident.command_id,)).fetchone()
            if row is None:
                raise ValueError("EFFECT_COMMAND_NOT_BOUND")
            self._assert_ident_row(row, ident)
            state = self._state(row)

            # Owed result publication is never erased by later proof expiry/movement.
            if state.phase in (Phase.RESULT_OBSERVED, Phase.ERROR_TERMINAL):
                return O4ProviderActionPermit(Action.RETRY_RETURN_WRITER_ONLY, ident.command_id,
                    row["intent_root"], row["contract_root"], row["effect_attempt_root"],
                    row["provider_request_count"], None)
            if state.phase is Phase.RETURN_WRITTEN:
                return O4ProviderActionPermit(Action.NOOP_TERMINAL, ident.command_id,
                    row["intent_root"], row["contract_root"], row["effect_attempt_root"],
                    row["provider_request_count"], None)

            self._assert_active_lineage(row, ident, intent, contract)
            currentness = self._resolve_currentness(intent, contract)
            decision = decide_recovery(state, intent, contract, context, currentness)
            currentness_root = decision.currentness_root
            if decision.action not in (Action.CALL_PROVIDER_FIRST_TIME, Action.RETRY_EXACT_SAME_EFFECT):
                return O4ProviderActionPermit(decision.action, ident.command_id, intent.identity_root,
                    contract.contract_root, state.effect_attempt_root, state.provider_request_count, currentness_root)
            if currentness_root is None:
                return O4ProviderActionPermit(Action.HOLD_REBIND_REQUIRED, ident.command_id,
                    intent.identity_root, contract.contract_root, state.effect_attempt_root,
                    state.provider_request_count, None)

            semantic = self._semantic(ident, intent, contract)
            try:
                admission = self.proof_admission_resolver(ident, intent, contract)
                if not isinstance(admission, ProofAdmission):
                    raise ValueError("PROOF_ADMISSION_OWNER_UNAVAILABLE")
                count = state.provider_request_count + 1
                parent_attempt = effect_attempt_root(intent, contract, count, currentness_root)
                bound_attempt = persist_owner_bound_provider_attempt(
                    con, semantic=semantic, admission=admission, now=self.now_resolver(),
                    parent_attempt_root=parent_attempt, provider_action_currentness_root=currentness_root,
                    provider_request_count=count,
                )
            except (ValueError, TypeError):
                # Same BEGIN IMMEDIATE has not committed a provider attempt; fail closed.
                return O4ProviderActionPermit(Action.HOLD_REBIND_REQUIRED, ident.command_id,
                    intent.identity_root, contract.contract_root, state.effect_attempt_root,
                    state.provider_request_count, currentness_root)

            return O4ProviderActionPermit(
                decision.action, ident.command_id, intent.identity_root, contract.contract_root,
                bound_attempt, count, currentness_root,
                stable_provider_operation_root=stable_provider_operation_root(semantic),
                proof_bound_admission_root=admission.proof_bound_admission_root,
                proof_action_currentness_root=proof_action_currentness_root(admission),
            )
