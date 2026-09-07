# O15 No-Blind-Replay Law

`TimeoutAfterRequest != ProviderFailure`.

If the provider outcome is ambiguous, recovery must query/reconcile the sink or use authenticated same-operation idempotent recovery. A new LLM decision is not evidence that the first external effect failed.

If an accepted sink result is established for the governed operation, consume it without provider replay. If a result has already been observed locally, subsequent pre-effect/workcell drift cannot erase the return obligation.
