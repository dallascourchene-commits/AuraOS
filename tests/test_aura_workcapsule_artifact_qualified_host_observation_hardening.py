from __future__ import annotations

import unittest

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    artifact_target_ref,
    verify_artifact_qualified_host_observation,
    verify_host_admission_envelope,
)
from tests.test_aura_workcapsule_artifact_qualified_host_observation import (
    WorkCapsuleArtifactQualifiedHostObservationTests,
    _reseal,
    _sha,
)


def _fixture() -> WorkCapsuleArtifactQualifiedHostObservationTests:
    case = WorkCapsuleArtifactQualifiedHostObservationTests(
        methodName="test_resolved_host_gate_is_bound_to_exact_local_artifact"
    )
    case.setUp()
    return case


def _structured_unknown_resolution(*, gate: str, target_ref: str) -> dict:
    resolution = {
        "schema": "AURA_HOST_OBSERVATION_RESOLUTION_V1",
        "version": 1,
        "gate": gate,
        "state": "UNKNOWN",
        "observation_ref": f"obs://{gate}",
        "producer_ref": "host://producer",
        "producer_generation": "7",
        "currentness_ref": "current://7",
        "authority_ref": "authority://bounded",
        "target_ref": target_ref,
        "resolver_ref": "resolver://fixture",
        "resolver_generation": "3",
        "revoked": False,
    }
    resolution["resolution_digest"] = _sha(resolution)
    return resolution


class ArtifactQualifiedHostObservationHardeningTests(unittest.TestCase):
    def test_valid_structured_unknown_resolution_preserves_unknown(self) -> None:
        case = _fixture()
        target_ref = artifact_target_ref(case.local_receipt())
        host = case.host_receipt()
        host["host_gate_resolutions"]["U_ROUTE"] = _structured_unknown_resolution(
            gate="U_ROUTE", target_ref=target_ref
        )
        _reseal(host)

        self.assertEqual([], verify_host_admission_envelope(host))
        self.assertEqual(
            [],
            verify_artifact_qualified_host_observation(**case.child_kwargs(host=host)),
        )

    def test_unhashable_host_gate_state_fails_closed(self) -> None:
        case = _fixture()
        host = case.host_receipt()
        host["host_gate_states"]["U_ROUTE"] = []
        _reseal(host)

        violations = verify_host_admission_envelope(host)
        self.assertIn("HOST_GATE_STATE_INVALID:U_ROUTE", violations)

    def test_unhashable_nested_resolution_state_fails_closed(self) -> None:
        case = _fixture()
        host = case.host_receipt(states={gate: "PASS" for gate in GATES})
        resolution = host["host_gate_resolutions"]["U_HEAD"]
        resolution["state"] = []
        resolution.pop("resolution_digest")
        resolution["resolution_digest"] = _sha(resolution)
        _reseal(host)

        violations = verify_host_admission_envelope(host)
        self.assertIn("HOST_RESOLUTION_STATE_INVALID:U_HEAD", violations)


if __name__ == "__main__":
    unittest.main()
