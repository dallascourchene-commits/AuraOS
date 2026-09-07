# O15 Effect Transaction State Machine

`ADMITTED -> ACKED -> ATTEMPT_DURABLE -> RESULT_OBSERVED -> RETURN_INFLIGHT -> RETURN_WRITTEN`

Recovery rules:
- `ATTEMPT_DURABLE + ACCEPTED` => consume/reconcile same governed operation, never provider replay.
- `ATTEMPT_DURABLE + NOT_ACCEPTED + authenticated idempotent retry + current workcell + current governed basis` => retry same governed operation.
- `ATTEMPT_DURABLE + UNKNOWN/nonretryable/query-only` => HOLD or query; never blind provider replay.
- `RESULT_OBSERVED` => return-writer-only.
- `RETURN_INFLIGHT` => reconcile existing return or retry writer only.
- `RETURN_WRITTEN` => done.

No state transition mints provider/effect authority.
