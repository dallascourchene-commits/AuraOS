#!/usr/bin/env python3
"""Current exact frontier joining official-source and concrete-page trial owners.

Q8 has no public positive path. The exact parents leave two independent gaps:
(1) the official source transport/header/tensor frontier is not yet complete; and
(2) neither parent proves that PR641's concrete page source hashes/materialization
came from those exact official tensor bytes. Closing (1) alone must never mint (2).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

SCHEMA = "AURA_GLM53_OFFICIAL_SOURCE_CONCRETE_PAGE_PROVENANCE_JOIN_V1"
CONVERGENCE_COMMIT = "22625150948c3143b57400e58a6d09af418a9a28"
OFFICIAL_BRIDGE_HEAD = "023cc10c25372f0e871f287cc5a22b9196c8a094"
OFFICIAL_BRIDGE_RUN = 33370777504
OFFICIAL_BRIDGE_SOURCE_BLOB = "733e6cb7a0ef404b8d8348410ecfc56e70f0e987"
CONCRETE_TRIAL_HEAD = "a8d4605a36e04d64cf03f43f457be4bde553e602"
CONCRETE_TRIAL_RUN = 33370700852
CONCRETE_TRIAL_SOURCE_BLOB = "157afcb2e457c630d03a8c72aef09f0a6ba04a4d"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"

REQUIRED_SUCCESSOR_EVIDENCE = (
    "OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
    "EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
    "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
    "BASELINE_SAME_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OfficialSourceConcretePageProvenanceReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    exact_parent_source_blobs: tuple[str, str]
    official_repository: str
    official_revision: str
    concrete_candidate_identity_bound: bool
    concrete_candidate_sample_bound: bool
    concrete_independent_verifier_bound: bool
    official_source_transport_frontier_complete: bool
    official_source_tensor_payload_observed: bool
    official_source_byte_domain_bound_to_trial: bool
    concrete_page_official_source_authenticated: bool
    concrete_page_source_tensor_set_bound_to_official_source: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    source_transport_repair_alone_sufficient: bool
    cross_domain_provenance_reopen_required: bool
    disposition: str
    required_successor_evidence: tuple[str, ...]
    real_tensor_quantization_eligible: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def current_provenance_frontier() -> OfficialSourceConcretePageProvenanceReceipt:
    """Return only facts jointly entailed by the two exact parent contracts."""
    return OfficialSourceConcretePageProvenanceReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(OFFICIAL_BRIDGE_HEAD, CONCRETE_TRIAL_HEAD),
        exact_parent_runs=(OFFICIAL_BRIDGE_RUN, CONCRETE_TRIAL_RUN),
        exact_parent_source_blobs=(OFFICIAL_BRIDGE_SOURCE_BLOB, CONCRETE_TRIAL_SOURCE_BLOB),
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        concrete_candidate_identity_bound=True,
        concrete_candidate_sample_bound=True,
        concrete_independent_verifier_bound=True,
        official_source_transport_frontier_complete=False,
        official_source_tensor_payload_observed=False,
        official_source_byte_domain_bound_to_trial=False,
        concrete_page_official_source_authenticated=False,
        concrete_page_source_tensor_set_bound_to_official_source=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        source_transport_repair_alone_sufficient=False,
        cross_domain_provenance_reopen_required=True,
        disposition="HOLD_OFFICIAL_SOURCE_TO_CONCRETE_PAGE_PROVENANCE",
        required_successor_evidence=REQUIRED_SUCCESSOR_EVIDENCE,
        real_tensor_quantization_eligible=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    """Guard against adding caller-controlled booleans to the V1 current frontier."""
    return len(inspect.signature(current_provenance_frontier).parameters) != 0


def main() -> None:
    receipt = current_provenance_frontier()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
