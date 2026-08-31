"""Bridge external discovery records into Aura external-knowledge ingress states.

Discovery does not directly mint CURRENT_REFERENCE. The bridge first creates an
L0 metadata-verified node. A second owner/provider observation of the same exact
source snapshot may promote that node to CURRENT_REFERENCE for read-only reuse.
The verifier/evidence generation is allowed to advance during that recheck.
Tool execution still requires separate admission.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from tools.aura_external_discovery import DiscoveryRecord
from tools.aura_external_knowledge_ingress import (
    ExternalKnowledgeNode,
    ExternalObservation,
    ExternalSubject,
    HydrationPayload,
    KnowledgeState,
    build_external_knowledge_node,
)


EXACT_REVISION_STRENGTHS = frozenset({
    "EXACT_VERSION_ID",
    "EXACT_COMMIT_SHA",
    "EXACT_REPO_SHA",
})

KIND_SECTOR = {
    "PAPER": "08_RSH",
    "REPOSITORY": "06_RUN",
    "MODEL": "02_SRC",
    "DATASET": "02_SRC",
    "SPACE": "06_RUN",
    "TOOLKIT": "06_RUN",
    "BENCHMARK": "04_TRU",
    "DOCUMENTATION": "08_RSH",
    "DISCUSSION": "08_RSH",
    "PACKAGE": "06_RUN",
    "WEB_PAGE": "08_RSH",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _security_flags(record: DiscoveryRecord) -> tuple[str, ...]:
    flags: set[str] = set()
    if record.provider == "HUGGING_FACE":
        gated = record.metadata.get("gated")
        if gated not in (False, None):
            flags.add("GATED_REPOSITORY")
        status = record.metadata.get("securityStatus")
        if status:
            flags.add("PROVIDER_SECURITY_METADATA_PRESENT")
    if record.provider == "GITHUB" and record.metadata.get("archived"):
        flags.add("ARCHIVED_REPOSITORY")
    if record.remote_code_authorized is False:
        flags.add("REMOTE_CODE_NOT_AUTHORIZED")
    return tuple(sorted(flags))


def _source_snapshot_identity(observation: ExternalObservation) -> tuple[object, ...]:
    """Fields describing the external source snapshot, excluding verifier/process state."""
    return (
        observation.provider_revision,
        observation.content_digest,
        observation.source_generated_at,
        observation.exact_source_uri,
        observation.etag,
        observation.last_modified,
        observation.license_id,
        observation.security_flags,
        observation.provider_metadata_digest,
    )


def discovery_to_l0_node(
    record: DiscoveryRecord,
    *,
    observed_at: str | None = None,
    validator_generation: str = "eki1-discovery-bridge-v1",
) -> ExternalKnowledgeNode:
    """Admit provider metadata to L0 without claiming current read-only reuse."""
    subject = ExternalSubject(
        provider=record.provider,
        source_kind=record.source_kind,
        canonical_id=record.canonical_id,
        canonical_uri=record.canonical_uri,
        sector=KIND_SECTOR[record.source_kind],
    )
    observation = ExternalObservation(
        provider_revision=record.provider_revision,
        content_digest=record.provider_metadata_digest,
        observed_at=observed_at or _now(),
        source_generated_at=record.source_generated_at,
        exact_source_uri=record.exact_source_uri,
        verifier_generation=validator_generation,
        verified_fields=("canonical_id", "exact_source_uri", "provider_metadata", "provider_revision"),
        license_id=(record.metadata.get("license") if isinstance(record.metadata.get("license"), str) else None),
        security_flags=_security_flags(record),
        provider_metadata_digest=record.provider_metadata_digest,
    )
    hydration = (
        HydrationPayload(
            level="L0",
            data={
                "title": record.title,
                "canonical_id": record.canonical_id,
                "canonical_uri": record.canonical_uri,
                "provider": record.provider,
                "source_kind": record.source_kind,
                "provider_revision": record.provider_revision,
                "exact_source_uri": record.exact_source_uri,
                "revision_strength": record.revision_strength,
            },
            derivation_method="PROVIDER_METADATA_EXTRACT",
        ),
    )
    state = (
        KnowledgeState.METADATA_VERIFIED
        if record.revision_strength in EXACT_REVISION_STRENGTHS
        else KnowledgeState.SOURCE_RESOLVED
    )
    return build_external_knowledge_node(
        subject=subject,
        observation=observation,
        knowledge_state=state,
        hydration=hydration,
        validator_generation=validator_generation,
    )


def promote_if_same_current_generation(
    node: ExternalKnowledgeNode,
    current_record: DiscoveryRecord,
    *,
    observed_at: str | None = None,
    validator_generation: str = "eki1-currentness-recheck-v1",
) -> ExternalKnowledgeNode:
    """Promote when an independently observed exact source snapshot is unchanged."""
    node.validate()
    candidate = discovery_to_l0_node(
        current_record,
        observed_at=observed_at,
        validator_generation=validator_generation,
    )
    if node.subject_key != candidate.subject_key:
        return replace(node, knowledge_state=KnowledgeState.INVALIDATED, read_only_reference_admissible=False)
    if candidate.knowledge_state != KnowledgeState.METADATA_VERIFIED:
        return replace(node, knowledge_state=KnowledgeState.STALE_REVERIFY_REQUIRED, read_only_reference_admissible=False)
    if _source_snapshot_identity(node.observation) != _source_snapshot_identity(candidate.observation):
        return replace(node, knowledge_state=KnowledgeState.STALE_REVERIFY_REQUIRED, read_only_reference_admissible=False)
    return build_external_knowledge_node(
        subject=candidate.subject,
        observation=candidate.observation,
        knowledge_state=KnowledgeState.CURRENT_REFERENCE,
        hydration=node.hydration,
        validator_generation=validator_generation,
    )


LAWS = (
    "Discovery!=CurrentReference",
    "SourceSnapshotIdentity!=EvidenceGenerationKey",
    "ExactProviderRevision+SecondMatchingSourceSnapshot=>ReadOnlyCurrentReferenceCandidate",
    "MatchingSourceSnapshotMayAdvanceEGKViaVerifierRefresh",
    "ChangedSourceSnapshot=>StaleReverifyRequired",
    "ChangedSubject=>Invalidated",
    "CurrentReadOnlyReference!=ToolExecutionAdmission",
)
