#!/usr/bin/env python3
"""Q20: revalidate the official GLM-5.3 repository revision before Gate-10 routing.

This membrane joins two independently proven parent consequences:
- Q18: bounded representative C2 proposal eligibility at an exact historical GLM-5.3 source revision.
- NAV-03B: explicit version selection must precede K27 locality navigation.

It proves only a bounded source-revision revalidation candidate. It does not bind tensor
payload bytes, execute a model, authorize a host trial, or promote Gate 10.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

SCHEMA = "AURA_GLM53_Q20_OFFICIAL_SOURCE_REVISION_REVALIDATION_V1"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA64_RE = re.compile(r"^[0-9a-f]{64}$")

Q18_HEAD = "87fde6b21675c7876acc63f4ca30b2dda89970d0"
Q18_SOURCE_BLOB = "4cee26edaf0759fc80d31889ab9e4e268f9a4fbe"
Q18_PROOF_RUN = 33436970079
Q18_PROOF_JOB = 99635635152
Q18_RECEIPT = "c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230"
Q18_DISPOSITION = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"

NAV03B_HEAD = "77e69373ea63288e64544861573ceeec51047154"
NAV03B_SOURCE_BLOB = "ef8c039a7a43ce92cb8ad29da5226101923d3056"
NAV03B_PROOF_RUN = 33440093097
NAV03B_PROOF_JOB = 99645898559

CONVERGENCE_COMMIT = "ad010b1ab2bf852c2b07d91487f01f8f10d243b8"

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
PINNED_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
CURRENT_OBSERVED_REVISION = "187fb9fff6319062325ff825627ef6db084d9bc6"

OBSERVED_REVISION_CHAIN = (
    PINNED_REVISION,
    "30333038ada1f1dacb294a93270305a890b50c14",
    "935644c05e76fc198714f4cca449fd8b970ff6d7",
    "e0b07fd2751b42d5efa199cc02c2b271deadc516",
    "eec49ed944209cb46d438f424f394bff9a54baa0",
    CURRENT_OBSERVED_REVISION,
)

OBSERVED_CHANGED_PATHS = (
    ".eval_results/deep-swe.yaml",
    ".eval_results/hle.yaml",
    ".eval_results/terminal-bench-2.1.yaml",
    ".eval_results/terminal-bench-3.0.yaml",
    "LICENSE",
    "README.md",
)

PINNED_SOURCE_URL = "https://huggingface.co/zai-org/GLM-5.3/commit/" + PINNED_REVISION
CURRENT_SOURCE_URL = "https://huggingface.co/zai-org/GLM-5.3/commit/" + CURRENT_OBSERVED_REVISION
PINNED_URL_SHA256 = "1ecdf3de72366eae1227f33cc20c152cc44c058badd8f44d061207c5a451e14b"
CURRENT_URL_SHA256 = "39ae483c9153f4b0426032335f4bf154d2460ed3ecbe8e1639572be7f58d7554"
PINNED_K27_B3MOD27_XYZ = (3, 16, 0)
CURRENT_K27_B3MOD27_XYZ = (3, 12, 18)

CANDIDATE = "GATE10_OFFICIAL_SOURCE_REVISION_REVALIDATION_CANDIDATE"
ALLOWED_METADATA_ONLY_EXACT = frozenset({"README.md", "LICENSE"})
ALLOWED_METADATA_ONLY_PREFIXES = (".eval_results/",)


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def k27_b3mod27_xyz(url: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(url.encode()).digest()
    return tuple(byte % 27 for byte in digest[:3])  # type: ignore[return-value]


def _valid_sha40(value: str) -> bool:
    return isinstance(value, str) and bool(SHA40_RE.fullmatch(value))


def _valid_sha64(value: str) -> bool:
    return isinstance(value, str) and bool(SHA64_RE.fullmatch(value))


def is_metadata_only_path(path: str) -> bool:
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        return False
    return path in ALLOWED_METADATA_ONLY_EXACT or path.startswith(ALLOWED_METADATA_ONLY_PREFIXES)


@dataclass(frozen=True)
class Q18Projection:
    producer_head: str
    proof_run: int
    proof_job: int
    source_blob: str
    receipt_digest: str
    disposition: str
    official_repository: str
    official_revision: str

    def validate(self) -> None:
        expected = (
            Q18_HEAD, Q18_PROOF_RUN, Q18_PROOF_JOB, Q18_SOURCE_BLOB,
            Q18_RECEIPT, Q18_DISPOSITION, OFFICIAL_REPOSITORY, PINNED_REVISION,
        )
        got = (
            self.producer_head, self.proof_run, self.proof_job, self.source_blob,
            self.receipt_digest, self.disposition, self.official_repository, self.official_revision,
        )
        if got != expected:
            raise ValueError("Q18_EXACT_GREEN_PROJECTION_MISMATCH")
        if not _valid_sha40(self.producer_head) or not _valid_sha40(self.source_blob):
            raise ValueError("Q18_GIT_IDENTITY_INVALID")
        if not _valid_sha64(self.receipt_digest):
            raise ValueError("Q18_RECEIPT_INVALID")


@dataclass(frozen=True)
class OfficialSourceRevisionObservation:
    repository: str
    pinned_revision: str
    observed_head_revision: str
    ancestry_chain: tuple[str, ...]
    changed_paths: tuple[str, ...]
    provider: str
    retrieval_epoch: str
    provider_head_observed: bool
    pinned_is_ancestor_of_observed_head: bool

    def validate(self) -> None:
        if self.repository != OFFICIAL_REPOSITORY:
            raise ValueError("OFFICIAL_REPOSITORY_MISMATCH")
        if self.pinned_revision != PINNED_REVISION:
            raise ValueError("PINNED_REVISION_MISMATCH")
        if self.observed_head_revision != CURRENT_OBSERVED_REVISION:
            raise ValueError("OBSERVED_HEAD_REVISION_REOPEN_REQUIRED")
        if not all(_valid_sha40(x) for x in self.ancestry_chain):
            raise ValueError("ANCESTRY_SHA_INVALID")
        if self.ancestry_chain != OBSERVED_REVISION_CHAIN:
            raise ValueError("EXACT_ANCESTRY_CHAIN_MISMATCH")
        if not self.provider_head_observed or not self.pinned_is_ancestor_of_observed_head:
            raise ValueError("LIVE_HEAD_OR_ANCESTRY_NOT_PROVEN")
        if not isinstance(self.provider, str) or not self.provider:
            raise ValueError("PROVIDER_REQUIRED")
        if not isinstance(self.retrieval_epoch, str) or not self.retrieval_epoch:
            raise ValueError("RETRIEVAL_EPOCH_REQUIRED")
        if len(self.changed_paths) != len(set(self.changed_paths)):
            raise ValueError("CHANGED_PATHS_MUST_BE_UNIQUE")
        if tuple(sorted(self.changed_paths)) != OBSERVED_CHANGED_PATHS:
            raise ValueError("OBSERVED_CHANGED_PATH_SET_MISMATCH")


def decision_tree(*, q18_eligible: bool, repository_exact: bool, pinned_revision_exact: bool,
                  current_head_exact: bool, ancestry_proven: bool,
                  model_relevant_paths_unchanged: bool) -> str:
    if not q18_eligible:
        return "HOLD_Q18_NOT_ELIGIBLE"
    if not repository_exact:
        return "HOLD_OFFICIAL_REPOSITORY_MISMATCH"
    if not pinned_revision_exact:
        return "HOLD_PINNED_REVISION_MISMATCH"
    if not current_head_exact:
        return "HOLD_CURRENT_HEAD_REOPEN_REQUIRED"
    if not ancestry_proven:
        return "HOLD_ANCESTRY_PROOF_REQUIRED"
    if not model_relevant_paths_unchanged:
        return "HOLD_MODEL_RELEVANT_SOURCE_CHANGE"
    return CANDIDATE


def decision_table(**state: bool) -> str:
    rules = (
        ("q18_eligible", "HOLD_Q18_NOT_ELIGIBLE"),
        ("repository_exact", "HOLD_OFFICIAL_REPOSITORY_MISMATCH"),
        ("pinned_revision_exact", "HOLD_PINNED_REVISION_MISMATCH"),
        ("current_head_exact", "HOLD_CURRENT_HEAD_REOPEN_REQUIRED"),
        ("ancestry_proven", "HOLD_ANCESTRY_PROOF_REQUIRED"),
        ("model_relevant_paths_unchanged", "HOLD_MODEL_RELEVANT_SOURCE_CHANGE"),
    )
    for key, failure in rules:
        if not state[key]:
            return failure
    return CANDIDATE


def assess_official_source_revision(*, q18: Q18Projection,
                                    observation: OfficialSourceRevisionObservation) -> dict[str, object]:
    q18.validate()
    observation.validate()
    model_relevant_changes = tuple(
        path for path in observation.changed_paths if not is_metadata_only_path(path)
    )
    state = dict(
        q18_eligible=q18.disposition == Q18_DISPOSITION,
        repository_exact=observation.repository == OFFICIAL_REPOSITORY,
        pinned_revision_exact=q18.official_revision == observation.pinned_revision == PINNED_REVISION,
        current_head_exact=observation.observed_head_revision == CURRENT_OBSERVED_REVISION,
        ancestry_proven=observation.pinned_is_ancestor_of_observed_head,
        model_relevant_paths_unchanged=not model_relevant_changes,
    )
    a = decision_tree(**state)
    b = decision_table(**state)
    if a != b:
        raise AssertionError("DIFFERENT_J_CLASSIFIER_DIVERGENCE")
    body: dict[str, object] = {
        "schema": SCHEMA,
        "exact_other_agent_heads": [Q18_HEAD, NAV03B_HEAD],
        "exact_other_agent_source_blobs": [Q18_SOURCE_BLOB, NAV03B_SOURCE_BLOB],
        "exact_parent_proof_runs": [Q18_PROOF_RUN, NAV03B_PROOF_RUN],
        "exact_parent_proof_jobs": [Q18_PROOF_JOB, NAV03B_PROOF_JOB],
        "true_two_parent_convergence": CONVERGENCE_COMMIT,
        "official_repository": OFFICIAL_REPOSITORY,
        "q18_pinned_revision": PINNED_REVISION,
        "provider_observed_head_revision": observation.observed_head_revision,
        "observed_revision_chain": list(observation.ancestry_chain),
        "changed_paths": list(observation.changed_paths),
        "metadata_only_changed_paths": [p for p in observation.changed_paths if is_metadata_only_path(p)],
        "model_relevant_changed_paths": list(model_relevant_changes),
        "repository_revision_changed": PINNED_REVISION != observation.observed_head_revision,
        "tracked_model_payload_or_config_path_changed": bool(model_relevant_changes),
        "tracked_model_payload_generation_unchanged_across_observed_diff": not model_relevant_changes,
        "provider_head_observed_at_retrieval": observation.provider_head_observed,
        "provider": observation.provider,
        "retrieval_epoch": observation.retrieval_epoch,
        "pinned_source_url": PINNED_SOURCE_URL,
        "current_source_url": CURRENT_SOURCE_URL,
        "pinned_url_sha256": PINNED_URL_SHA256,
        "current_url_sha256": CURRENT_URL_SHA256,
        "pinned_k27_b3mod27_xyz": list(PINNED_K27_B3MOD27_XYZ),
        "current_k27_b3mod27_xyz": list(CURRENT_K27_B3MOD27_XYZ),
        "k27_used_for_version_selection": False,
        "version_selected_before_k27_navigation": True,
        "disposition": a,
        "gate10_source_binding_candidate": a == CANDIDATE,
        "future_effect_source_revalidation_required": True,
        "source_currentness_at_future_effect_proven": False,
        "tensor_payload_bytes_observed_by_this_contract": False,
        "tensor_payload_bound": False,
        "real_quantization_observed": False,
        "model_execution_observed": False,
        "owner_host_execution_observed": False,
        "physical_io_observed": False,
        "auraos_resident_routing_observed": False,
        "replay_recovery_proven": False,
        "gate10_promoted": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "laws": [
            "RepositoryRevisionChanged!=ModelPayloadGenerationChanged",
            "TrackedPayloadPathUnchanged!=FutureSourceCurrentness",
            "ExplicitVersionSelection->K27Navigation",
            "K27Navigation!=VersionSelection",
            "K27Coordinate!=SourceIdentity!=Currentness!=Authority",
            "Q18ProposalEligible!=TensorPayloadBound",
            "SourceRevisionRevalidationCandidate!=OwnerHostExecutionAuthority",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ],
    }
    body["receipt_digest"] = _sha(body)
    return body


def current_q18_projection() -> Q18Projection:
    return Q18Projection(Q18_HEAD, Q18_PROOF_RUN, Q18_PROOF_JOB, Q18_SOURCE_BLOB,
                         Q18_RECEIPT, Q18_DISPOSITION, OFFICIAL_REPOSITORY, PINNED_REVISION)


def observed_current_source_fixture() -> OfficialSourceRevisionObservation:
    return OfficialSourceRevisionObservation(
        OFFICIAL_REPOSITORY, PINNED_REVISION, CURRENT_OBSERVED_REVISION,
        OBSERVED_REVISION_CHAIN, OBSERVED_CHANGED_PATHS, "huggingface-git",
        "2026-08-31T21:12Z", True, True,
    )


def prove_64_state_lattice() -> dict[str, int]:
    keys = (
        "q18_eligible", "repository_exact", "pinned_revision_exact",
        "current_head_exact", "ancestry_proven", "model_relevant_paths_unchanged",
    )
    counts: dict[str, int] = {}
    for mask in range(1 << len(keys)):
        state = {key: bool(mask & (1 << i)) for i, key in enumerate(keys)}
        a, b = decision_tree(**state), decision_table(**state)
        if a != b:
            raise AssertionError(f"DIFFERENT_J_DIVERGENCE:{mask}:{a}:{b}")
        counts[a] = counts.get(a, 0) + 1
    if sum(counts.values()) != 64 or counts.get(CANDIDATE) != 1:
        raise AssertionError("Q20_64_STATE_PROOF_INCOMPLETE")
    return counts


def main() -> None:
    receipt = assess_official_source_revision(
        q18=current_q18_projection(), observation=observed_current_source_fixture()
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
