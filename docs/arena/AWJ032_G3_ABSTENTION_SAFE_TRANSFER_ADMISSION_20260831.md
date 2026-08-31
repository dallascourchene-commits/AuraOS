# AWJ032 GLM-5.3 G3 — Abstention-Safe Transfer Admission

Status: D0 / HS1 / NONPROMOTING

## Exactly two other-Agent artifacts

1. PR #722, exact green head `44831fd5454d08a97bd0b172337cf4c48a339dfe`: cost-aware speculative-transfer admission. It owns typed latency value/cost, calibration identity, bounded logical-byte/time/energy gates, and the separation `TransferPlanEligibility != TransferEffectAuthority != G2Admission`.
2. PR #723, exact green head `d0f71761b1d8692cc3797d4d8574b4082f404344`: safe predictor abstention. It proves `PrefetchPrediction(())` is lawful while the native route remains nonempty and authoritative, and that abstention demand-loads the exact native-selected experts without inventing physical-I/O savings.

True two-parent convergence: `e74bcbaa55f5d4f8b09427293a5638089d5dface`.

## Objective

Close the cross-artifact seam:

`SafePredictionAbstention + CostAwareTransferAdmission != LawfulZeroTransferPlanUntil EmptyForecastSet + ZeroColdBytes + ZeroReuseRequirement + NativeDemandContinuity + PhysicalIOUnknown Commute`.

Before G3, #723 makes the empty prediction lawful but #722 still calls the W4 `required_reuse()` reducer with zero logical bytes, which correctly rejects nonpositive demand. The composition therefore fails even though there is no speculative transfer to evaluate.

## Repair

- preserve #722's post-read pager result source/expert-set W3 guard;
- preserve #723's dedicated speculative-prediction canonicalizer that allows only the empty predictor set while keeping native-route expert sets nonempty;
- treat `cold_predicted_logical_bytes == 0` as `cold_required_reuse_for_window == 0.0`;
- require the forecast set to be exactly empty under abstention;
- preserve policy layer/binding/currentness checks even when no experts are predicted;
- keep admitted experts, logical bytes, transfer time and expected latency margin at zero;
- keep physical I/O unattested/UNKNOWN and transfer/G2/effect authority false;
- prove that native misses are still demand-loaded exactly and still subject to pager-result source proof.

## Laws

`PredictionAbstention != RoutingFailure`.
`EmptyPrediction => ZeroSpeculativeTransferPlan`.
`ZeroSpeculativeTransferPlan != EmptyNativeExecutionPlan`.
`ZeroPredictedBytes => ZeroReuseRequired`.
`ZeroReuseRequired != PhysicalBytesAvoided`.
`ForecastSetMustEqualPredictionSet`.
`AbstentionDoesNotBypassPagerResultSourceProof`.
`TransferPlanEligibility != TransferEffectAuthority != G2Admission`.
`K27Coordinate != TransformerKVCache != RoutingAuthority`.

## External Different-J pressure

- Speculative-expert and confidence-aware MoE prefetch research supports making prediction optional/adaptive rather than execution-authoritative.
- SPICE (arXiv:2608.21240) reinforces confidence-aware staging, while its approximation-on-miss path remains outside Aura's exact-demand recovery cone.
- Current LocalLLaMA reports show both substantial gains and regressions from expert caching/prefetch depending on workload and reuse, reinforcing abstention as a valid policy outcome rather than forced speculative traffic.
- Direct task-specific Google Scholar-native discovery returned no stable result in this pass: `SCHOLAR_DIRECT_GAP`.

External sources are falsification/methodology pressure only and grant no Aura authority.

## K27 / persistent-coordinate allocation

Existing expert-prefetch and cache-pressure coordinates are reused rather than duplicated. New relation coordinate is metadata-only:

`K27:AWJ032:G3:ABSTENTION_SAFE_TRANSFER_ADMISSION -> {parents:#722,#723, convergence:e74bcbaa..., reopen:[predictor_generation, calibration_generation, policy_generation, binding_digest, G1/G2 semantic generation]}`.

This coordinate is retrieval/currentness/reopen metadata only. It is not transformer KV, semantic truth, routing authority, pager authority, or effect authority.

## Crystalline / Triadic / Creation / HyperScale

W0: exact green #722 + #723 anchors.
W1: predictor abstains -> empty forecast set -> zero transfer plan -> native route remains independently executable/demand-bound.
W2: forecast injection, policy layer/binding substitution, dishonest pager-result source, authority/physical-I/O widening.
W3: composition contradiction `required_reuse(0)` -> minimum repair.
W4: prediction, calibration, plan, native route, pager result, physical I/O, execution and effect remain independent leaves.
W5: true two-parent Diamond at `e74bcbaa...`.
W6: duplicate/collision scan returned no pre-existing owner for this exact seam.
W7: predictor/calibration/policy generations remain identity-bearing reopen triggers.
W8: transfer/effect/G2/Gate-10 authority remains unearned.

HS1 remains sufficient; no swarm expansion is justified by this single deterministic relation cone.

## Claim ceiling

No GLM/provider/model execution, checkpoint download, host transfer, physical NVMe measurement, output-quality claim, G2 admission, native/private transformer KV access, semantic K27 authority, Gate-10, merge/deploy/spend, or public/financial/human effect is granted.
