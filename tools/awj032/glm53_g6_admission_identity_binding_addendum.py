"""Compatibility tombstone for the absorbed G6 identity-binding W3.

The consequence-changing findings discovered here are now owned directly by
`glm53_g6_gate10_owner_host_evidence_request.py` v4:
- exact Q18 historical admission receipt binding;
- exact PR #769 reuse-digest relation;
- full current-use identity preservation;
- no caller-supplied precompiled-request + independent-identity join.

This file intentionally owns no independent G6 semantics and receives zero closure
or successor credit. It remains only as an audit/provenance coordinate for the W3
falsifier that caused the canonical repair.
"""
from __future__ import annotations

from tools.awj032 import glm53_g6_gate10_owner_host_evidence_request as canonical

ABSORBED_IN_CANONICAL_G6 = True
INDEPENDENT_SEMANTIC_OWNER = False
CANONICAL_SCHEMA = canonical.SCHEMA
CANONICAL_COMPILER = "tools.awj032.glm53_g6_gate10_owner_host_evidence_request.compile_gate10_owner_host_evidence_request"
ABSORBED_LAWS = (
    "ExactQ18AdmissionReceiptMustRemainBound",
    "PR769ReuseDigestMustCommitExactIdentityVector",
    "DigestShape!=DigestRelationProof",
    "SingleOwnerCompilerEliminatesPostHocIdentityJoin",
)


def canonical_owner_status() -> dict[str, object]:
    for law in ABSORBED_LAWS:
        if law not in canonical.LAWS:
            raise RuntimeError(f"ABSORBED_G6_LAW_MISSING:{law}")
    return {
        "absorbed": ABSORBED_IN_CANONICAL_G6,
        "independent_semantic_owner": INDEPENDENT_SEMANTIC_OWNER,
        "canonical_schema": CANONICAL_SCHEMA,
        "canonical_compiler": CANONICAL_COMPILER,
        "closure_credit": 0,
    }
