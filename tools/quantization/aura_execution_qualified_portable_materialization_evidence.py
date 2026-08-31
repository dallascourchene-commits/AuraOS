#!/usr/bin/env python3
"""Q15: execution-qualified portable materialization evidence.

This membrane composes two exact post-cut semantic siblings:
- A7: execution-qualified portable evidence.
- Q14: bounded official-source -> canonical E8 page materialization.

The axes are deliberately independent. A page existing does not prove provider
execution; provider execution does not prove page identity; portability does not
reset semantic generation; and replay/currentness does not mint successor novelty.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "AURA_EXECUTION_QUALIFIED_PORTABLE_MATERIALIZATION_EVIDENCE_V1"
A6_CUT = "2026-08-31T13:36:29Z"

CONVERGENCE_COMMIT = "886a8282feedc4abb5ca517d6293945a1c34abc1"
Q14_HEAD = "ee70934e0c45572588829e742e512a897b23863f"
A7_HEAD = "10481aa76117c24e5fdf7f93752e7820713a8285"

# Q14's semantic source generation is the commit that first materialized the
# bounded official-source E8 pages. Q14_HEAD is the later terminal semantic
# repair/proof generation that revalidated the exact Q13 FP8 owners. Keeping
# both identities prevents replay/proof time from replacing source generation.
Q14_SEMANTIC_HEAD = "74e5ee32379ddabb498587b08ba40ff21cebf13d"
Q14_SEMANTIC_GENERATED_AT = "2026-08-31T13:43:26Z"
A7_SEMANTIC_HEAD = "1801de258fa88075565e62bd8f2ce9dbe6663f09"
A7_SEMANTIC_GENERATED_AT = "2026-08-31T13:44:56Z"

Q14_RUN = 33399560819
Q14_JOB = 99512130505
Q14_WORKFLOW = "Aura GLM-5.3 Official Source to E8 Materialization Canary"
A7_RUN = 33400287890
A7_JOB = 99514663480
A7_WORKFLOW = "Aura Execution-Qualified Portable Evidence Admission"

Q14_ARTIFACT_ID = 9760937399
Q14_ARTIFACT_DIGEST = "sha256:edc22355df8bfeff25f469f11b54d7948b10bbf72a831b769857068c63c77276"
Q14_JSON_SHA256 = "fe253b0a89bbe1cd97a0299053ae9b11582f03cd1437b35525242f54154ae2a0"
Q14_RECEIPT_DIGEST = "6a0fefe423b637d764cc0caee728fff62f7c68dc0ae66f0d97146bdebbbaaa1e"
Q14_PAGE_SET_DIGEST = "4811719dd71a1c8b3258000286955a7ae31895c46a0a34bbfcf5fec3717bdf41"

EXPECTED_ROLE_PAGES = {
    "down_proj": {
        "raw_fp8_tile_sha256": "a286b73895b59a5d7d32381e72e2374d68f87a9634a4fdb7a111049bb6e99e69",
        "raw_scale_cell_sha256": "ba046e869084014082242c8dbd366e6488752fccb2190c7df59d667909fad309",
        "canonical_tile_sha256": "8174eb3f4ba5de33ba048212ee16630b46ff67542892fdd77ac89ce5b58f068b",
        "page_identity_digest": "3183d404ab321865795d461234f007166dc8bd1e45742e016c93f1651f121bdf",
        "page_payload_sha256": "9888974d6371d2da3a0303f70783086ff312df5aa0e6afa59ac056394d2af77a",
    },
    "gate_up_proj": {
        "raw_fp8_tile_sha256": "c3828eb15a2bf682de75e6c6edef0e26bd8bbbd0cf80bc7c1026cf32c49c7648",
        "raw_scale_cell_sha256": "e9644209eeb514ef510ceaf0234c87684b213819288184f4b8e8f2aa6c418e8e",
        "canonical_tile_sha256": "bb454683745c2c20d50b21c58619012a174e4d00745d2727120d20ee9fe0e2b4",
        "page_identity_digest": "e89a377beb5381bfa9200321d5aa26c2ff0baa41da9a129ff115b8c0cef09b6a",
        "page_payload_sha256": "725e9d0c6aa25043a480a3ad745cf33b92d8dcdc042f00e583767a6871c96379",
    },
}

CLAIM_CEILING = (
    "execution-qualified portable bounded official-source-to-E8 materialization evidence only; "
    "not a full representative page set, not model execution, not inference, not generalized "
    "quality/performance, and not successor-semantic novelty by replay"
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_object(value: Any) -> str:
    return _sha_bytes(_canonical(value))


def _parse_ts(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("UTC_Z_TIMESTAMP_REQUIRED")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)


def _extract_jobs(value: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        jobs = value.get("jobs", [])
    else:
        jobs = value
    if not isinstance(jobs, list):
        raise ValueError("JOBS_LIST_REQUIRED")
    return jobs


def _run_job_exact(
    *,
    run: Mapping[str, Any],
    jobs_payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    expected_run: int,
    expected_job: int,
    expected_head: str,
    expected_workflow: str,
) -> tuple[bool, bool, bool, bool]:
    jobs = _extract_jobs(jobs_payload)
    run_exact = (
        run.get("id") == expected_run
        and run.get("head_sha") == expected_head
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    )
    workflow_exact = run.get("name") == expected_workflow
    matching = [j for j in jobs if j.get("id") == expected_job]
    job_once = len(matching) == 1
    job_success = bool(
        job_once
        and matching[0].get("status") == "completed"
        and matching[0].get("conclusion") == "success"
        and matching[0].get("run_id") == expected_run
    )
    return run_exact, workflow_exact, job_once, job_success


def validate_q14_receipt(raw: bytes) -> tuple[dict[str, Any], bool, bool, bool]:
    """Validate exact hosted Q14 JSON bytes and its internal source/page consequence."""
    file_exact = _sha_bytes(raw) == Q14_JSON_SHA256
    payload = json.loads(raw.decode("utf-8"))
    embedded_digest = payload.get("receipt_digest")
    receipt_body = {k: v for k, v in payload.items() if k not in {"receipt_digest", "laws"}}
    receipt_exact = (
        embedded_digest == Q14_RECEIPT_DIGEST
        and _sha_object(receipt_body) == Q14_RECEIPT_DIGEST
        and payload.get("schema") == "AURA_GLM53_OFFICIAL_SOURCE_E8_MATERIALIZATION_CANARY_V1"
        and payload.get("canary_page_set_digest") == Q14_PAGE_SET_DIGEST
        and payload.get("minimum_canary_cone_weights") == 128
        and payload.get("two_official_source_bound_tile_pages_materialized") is True
        and payload.get("full_role_page_payloads_materialized") is False
        and payload.get("full_source_set_page_set_materialized") is False
        and payload.get("model_execution_observed") is False
        and payload.get("semantic_k27_authority") is False
        and payload.get("native_private_transformer_kv_accessed") is False
        and payload.get("gate10_promoted") is False
        and payload.get("merge_or_deployment_authorized") is False
    )
    roles = payload.get("role_canaries")
    role_exact = isinstance(roles, list) and len(roles) == 2
    by_role = {}
    if role_exact:
        by_role = {r.get("tensor_role"): r for r in roles if isinstance(r, dict)}
        role_exact = set(by_role) == set(EXPECTED_ROLE_PAGES)
    if role_exact:
        for role, expected in EXPECTED_ROLE_PAGES.items():
            got = by_role[role]
            role_exact = role_exact and all(got.get(k) == v for k, v in expected.items())
            role_exact = role_exact and all(
                got.get(k) is True
                for k in (
                    "actual_e8_page_payload_materialized",
                    "official_source_to_e8_page_derivation_proven_for_tile",
                    "page_materialization_owner_bound_for_tile",
                    "page_source_identity_matches_canonical_tile",
                    "tile_relation_to_q13_role_bound",
                )
            )
            role_exact = role_exact and got.get("source_weight_count") == 64
    return payload, file_exact, receipt_exact, bool(role_exact)


@dataclass(frozen=True)
class ExecutionQualifiedPortableMaterializationReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    semantic_generation_heads: tuple[str, str]
    semantic_generation_times: tuple[str, str]
    prior_cut: str
    q14_run: int
    q14_job: int
    a7_run: int
    a7_job: int
    q14_artifact_id: int
    q14_artifact_digest: str
    q14_json_sha256: str
    q14_receipt_digest: str
    q14_page_set_digest: str
    role_page_payload_sha256: tuple[str, str]
    c0_parent_identity: bool
    c1_source_slice_identity: bool
    c2_page_consequence: bool
    c3_portability_integrity: bool
    c4_provider_execution: bool
    c5_semantic_freshness: bool
    c6_nonpromotion_invalidation: bool
    c7_claim_ceiling: bool
    execution_qualified_portable_materialization_evidence: bool
    page_existence_implies_execution: bool
    execution_implies_page_identity: bool
    portability_resets_semantic_clock: bool
    replay_mints_successor_novelty: bool
    k27_coordinate_is_semantic_authority: bool
    native_private_transformer_kv_accessed: bool
    full_representative_page_set_proven: bool
    model_execution_proven: bool
    inference_proven: bool
    generalized_quality_or_performance_proven: bool
    merge_or_deployment_authorized: bool
    claim_ceiling: str
    hyperscale_level: str
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha_object(asdict(self))


def admit(
    *,
    q14_raw: bytes,
    q14_artifact_digest: str,
    convergence_parents: Sequence[str],
    generation_evidence: Mapping[str, Mapping[str, Any]],
    a7_run: Mapping[str, Any],
    a7_jobs: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    q14_run: Mapping[str, Any],
    q14_jobs: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> ExecutionQualifiedPortableMaterializationReceipt:
    q14, file_exact, receipt_exact, role_exact = validate_q14_receipt(q14_raw)

    parent_identity = tuple(convergence_parents) == (Q14_HEAD, A7_HEAD)

    a7_gen = generation_evidence.get("a7", {})
    q14_gen = generation_evidence.get("q14", {})
    generation_exact = (
        a7_gen.get("head") == A7_SEMANTIC_HEAD
        and a7_gen.get("generated_at") == A7_SEMANTIC_GENERATED_AT
        and a7_gen.get("ancestor_of") == A7_HEAD
        and a7_gen.get("ancestor_proven") is True
        and q14_gen.get("head") == Q14_SEMANTIC_HEAD
        and q14_gen.get("generated_at") == Q14_SEMANTIC_GENERATED_AT
        and q14_gen.get("ancestor_of") == Q14_HEAD
        and q14_gen.get("ancestor_proven") is True
    )
    freshness = bool(
        generation_exact
        and _parse_ts(A7_SEMANTIC_GENERATED_AT) > _parse_ts(A6_CUT)
        and _parse_ts(Q14_SEMANTIC_GENERATED_AT) > _parse_ts(A6_CUT)
    )

    a7_re = _run_job_exact(
        run=a7_run, jobs_payload=a7_jobs, expected_run=A7_RUN, expected_job=A7_JOB,
        expected_head=A7_HEAD, expected_workflow=A7_WORKFLOW
    )
    q14_re = _run_job_exact(
        run=q14_run, jobs_payload=q14_jobs, expected_run=Q14_RUN, expected_job=Q14_JOB,
        expected_head=Q14_HEAD, expected_workflow=Q14_WORKFLOW
    )
    provider_execution = all(a7_re) and all(q14_re)

    source_slice_identity = bool(
        receipt_exact
        and role_exact
        and q14.get("official_repository") == "zai-org/GLM-5.3"
        and q14.get("official_revision") == "7cda81930d6e4cef42f48555de830aa32ecdde28"
        and q14.get("selected_layer") == 3
        and q14.get("selected_expert") == 0
        and q14.get("selected_shard") == "model-00038-of-00141.safetensors"
    )
    page_consequence = bool(receipt_exact and role_exact)
    portability_integrity = bool(
        file_exact
        and receipt_exact
        and q14_artifact_digest == Q14_ARTIFACT_DIGEST
    )
    nonpromotion = bool(
        q14.get("full_role_page_payloads_materialized") is False
        and q14.get("full_source_set_page_set_materialized") is False
        and q14.get("model_execution_observed") is False
        and q14.get("generalized_quality_proven") is False
        and q14.get("runtime_performance_proven") is False
        and q14.get("physical_io_performance_proven") is False
        and q14.get("semantic_k27_authority") is False
        and q14.get("native_private_transformer_kv_accessed") is False
        and q14.get("gate10_promoted") is False
        and q14.get("merge_or_deployment_authorized") is False
    )
    claim_ceiling = CLAIM_CEILING.endswith("successor-semantic novelty by replay")
    lattice = (
        parent_identity,
        source_slice_identity,
        page_consequence,
        portability_integrity,
        provider_execution,
        freshness,
        nonpromotion,
        claim_ceiling,
    )
    admitted = all(lattice)

    if not parent_identity:
        reason = "EXACT_TWO_PARENT_DIAMOND_NOT_BOUND"
    elif not source_slice_identity:
        reason = "OFFICIAL_SOURCE_SLICE_IDENTITY_NOT_BOUND"
    elif not page_consequence:
        reason = "CANONICAL_E8_PAGE_CONSEQUENCE_NOT_BOUND"
    elif not portability_integrity:
        reason = "HOSTED_Q14_ARTIFACT_INTEGRITY_NOT_BOUND"
    elif not provider_execution:
        reason = "EXACT_PROVIDER_EXECUTION_NOT_BOUND"
    elif not freshness:
        reason = "SEMANTIC_GENERATION_NOT_AUTHENTICATED_POST_CUT"
    elif not nonpromotion:
        reason = "Q14_CLAIM_CEILING_PROMOTED"
    elif not claim_ceiling:
        reason = "Q15_CLAIM_CEILING_DRIFT"
    else:
        reason = "EXECUTION_QUALIFIED_PORTABLE_MATERIALIZATION_EVIDENCE_ADMITTED"

    roles = sorted(q14["role_canaries"], key=lambda r: r["tensor_role"])
    return ExecutionQualifiedPortableMaterializationReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(Q14_HEAD, A7_HEAD),
        semantic_generation_heads=(Q14_SEMANTIC_HEAD, A7_SEMANTIC_HEAD),
        semantic_generation_times=(Q14_SEMANTIC_GENERATED_AT, A7_SEMANTIC_GENERATED_AT),
        prior_cut=A6_CUT,
        q14_run=Q14_RUN,
        q14_job=Q14_JOB,
        a7_run=A7_RUN,
        a7_job=A7_JOB,
        q14_artifact_id=Q14_ARTIFACT_ID,
        q14_artifact_digest=q14_artifact_digest,
        q14_json_sha256=_sha_bytes(q14_raw),
        q14_receipt_digest=str(q14.get("receipt_digest", "")),
        q14_page_set_digest=str(q14.get("canary_page_set_digest", "")),
        role_page_payload_sha256=tuple(str(r["page_payload_sha256"]) for r in roles),
        c0_parent_identity=parent_identity,
        c1_source_slice_identity=source_slice_identity,
        c2_page_consequence=page_consequence,
        c3_portability_integrity=portability_integrity,
        c4_provider_execution=provider_execution,
        c5_semantic_freshness=freshness,
        c6_nonpromotion_invalidation=nonpromotion,
        c7_claim_ceiling=claim_ceiling,
        execution_qualified_portable_materialization_evidence=admitted,
        page_existence_implies_execution=False,
        execution_implies_page_identity=False,
        portability_resets_semantic_clock=False,
        replay_mints_successor_novelty=False,
        k27_coordinate_is_semantic_authority=False,
        native_private_transformer_kv_accessed=False,
        full_representative_page_set_proven=False,
        model_execution_proven=False,
        inference_proven=False,
        generalized_quality_or_performance_proven=False,
        merge_or_deployment_authorized=False,
        claim_ceiling=CLAIM_CEILING,
        hyperscale_level="HS1",
        reason=reason,
    )


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q14-receipt", required=True)
    parser.add_argument("--q14-artifact-digest", required=True)
    parser.add_argument("--convergence-parents", required=True)
    parser.add_argument("--generation-evidence", required=True)
    parser.add_argument("--a7-run", required=True)
    parser.add_argument("--a7-jobs", required=True)
    parser.add_argument("--q14-run", required=True)
    parser.add_argument("--q14-jobs", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    receipt = admit(
        q14_raw=Path(args.q14_receipt).read_bytes(),
        q14_artifact_digest=args.q14_artifact_digest,
        convergence_parents=_load(args.convergence_parents),
        generation_evidence=_load(args.generation_evidence),
        a7_run=_load(args.a7_run),
        a7_jobs=_load(args.a7_jobs),
        q14_run=_load(args.q14_run),
        q14_jobs=_load(args.q14_jobs),
    )
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = [
        "PageExistence!=ProviderExecution!=PageIdentity",
        "PortableIntegrity!=ExecutionQualification!=SemanticFreshness",
        "InitialSemanticMaterializerGeneration!=TerminalSemanticRepairGeneration!=ReplayTimestamp",
        "AuthenticatedPostCutSemanticGeneration!=ReplayOrTransferTimestamp",
        "ExactOfficialSourceSlice+CanonicalE8Page+ExactSuccessfulProducerRunJob=>ExecutionQualifiedPortableMaterializationEvidence",
        "CoordinateMemory!=SemanticAuthority",
        "CoordinateMaterializedAfterCut!=SemanticGeneratedAfterCut",
        "BoundedMaterialization!=FullRepresentativePageSet!=ModelExecution!=Inference",
        "HS1UntilIndependentResidualFanoutIsEarned",
    ]
    text = json.dumps(body, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    if not receipt.execution_qualified_portable_materialization_evidence:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
