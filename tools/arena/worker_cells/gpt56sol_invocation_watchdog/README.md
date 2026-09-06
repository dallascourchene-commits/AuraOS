# R10.3 direct-worker watchdog canary

Keeper:

- `BoundedCardinality != BoundedWallClock`
- `NonReturningNext => IsolateExecutionBeforeDeadlineEnforcement`
- `WatchdogTimeout != ExternalSideEffectRollback`

This is a D0 canary, not a production sandbox. It runs R10.2 materialization in a direct child process, uses a separate startup READY handshake, keeps the post-READY execution deadline in the parent, terminates/reaps a ready child whose caller `next()` never returns, and preserves distinct finite and governed-reject outcomes. The canary child intentionally spawns no descendants and performs no external effects.

No claim is made for descendant-process-tree containment, production sandbox security, host/provider authority, or rollback of effects outside the isolated process.

Failed-first scar: an initial single deadline conflated Python spawn/import time with hung-call execution. That proof is superseded; R10.3 starts the short execution deadline only after READY.
