# AWJ032 ThinkPad NVMe Residency / Prefetch Plan

This membrane converts a measured-or-synthetic host storage profile plus bounded tensor-slice metadata into a deterministic storage plan. It is intentionally below execution.

## ThinkPad-first decisions

- keep high-reuse hot slices inside an explicit RAM budget;
- use asynchronous NVMe prefetch only when the supplied host profile says `io_uring` is available and the estimated read fits inside bounded compute slack;
- assign bounded ping-pong buffer slots to eligible reads;
- coalesce adjacent reads only inside the same storage object / issue-step / buffer lane;
- fall back to `mmap` demand paging when asynchronous overlap cannot safely hide the supplied read estimate;
- use synchronous direct I/O only as a final explicitly supported fallback;
- fail closed if no storage path is supported.

## Boundary laws

`StoragePlan != PhysicalIO`.

`MeasuredBandwidthInput != ThroughputClaim`.

`AsyncPrefetchEligible != PrefetchExecuted`.

`RAMResidencyDecision != ModelExecution`.

`PlanDigest -> C2 storage_plan_digest` does not authorize the C2 attempt.

The implementation performs no host sampling, model download, file reads, weight loading, GPU transfer, inference, producer authentication, lifecycle admission, G2 admission, or effect.
