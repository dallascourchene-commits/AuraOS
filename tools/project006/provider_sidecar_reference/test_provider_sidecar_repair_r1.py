from __future__ import annotations

import json
import unittest
from unittest import mock

from tools.project006.provider_sidecar_reference.provider_sidecar import (
    CircuitState,
    DispatchBinding,
    ProviderSidecarReference,
    SidecarStatus,
    _Circuit,
)


_SECRET_FRAGMENT = "sk-secret-fragment"


class _NoCallTransport:
    def __init__(self) -> None:
        self.calls = 0

    def post(self, endpoint, payload, *, bearer, timeout):
        self.calls += 1
        raise AssertionError("transport must not run after local resolution failure")


class ProviderSidecarLocalResolutionRepairTests(unittest.TestCase):
    def binding(self) -> DispatchBinding:
        return DispatchBinding(
            capsule_id="CAP-R1",
            lease_generation=7,
            fencing_token="FENCE-R1",
            currentness_ref="SRC-R1",
        )

    def dispatch(self, sidecar: ProviderSidecarReference):
        return sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "hello"}],
            retry_budget=0,
        )

    @staticmethod
    def raising_resolver(provider: str, _cfg: dict) -> tuple[str, ...]:
        raise RuntimeError(_SECRET_FRAGMENT)

    def assert_local_failure_is_secret_free(self, value) -> None:
        serialized = json.dumps(value, sort_keys=True)
        for fragment in (_SECRET_FRAGMENT, "sk-secret", "secret-fragment"):
            self.assertNotIn(fragment, serialized)

    def test_dispatch_credential_resolver_failure_is_typed_pretransport_and_released(self):
        transport = _NoCallTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=self.raising_resolver,
            transport=transport,
        )
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.attempts, 0)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._pressure_snapshot(), (0, 0))
        self.assertEqual(sidecar._circuits, {})
        self.assert_local_failure_is_secret_free(result.receipt.to_jsonable())

    def test_health_credential_resolver_failure_is_bounded_typed_and_secret_free(self):
        sidecar = ProviderSidecarReference(credential_resolver=self.raising_resolver)
        health = sidecar.health_report("premium")
        self.assertEqual(health["status"], SidecarStatus.LOCAL_RESOLUTION_ERROR.value)
        self.assertEqual(health["providers"], [])
        self.assertEqual(health["in_flight"], 0)
        self.assertEqual(health["queue_depth"], 0)
        self.assert_local_failure_is_secret_free(health)

    def test_provider_order_failure_is_typed_without_transport_or_circuit_mutation(self):
        transport = _NoCallTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=lambda _provider, _cfg: (),
            transport=transport,
        )
        with mock.patch.object(
            sidecar.registry,
            "provider_order",
            side_effect=RuntimeError(_SECRET_FRAGMENT),
        ):
            result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._circuits, {})
        self.assert_local_failure_is_secret_free(result.receipt.to_jsonable())

    def test_get_provider_config_failure_is_typed_fail_closed(self):
        transport = _NoCallTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=lambda _provider, _cfg: (),
            transport=transport,
        )
        with mock.patch.object(
            sidecar.registry,
            "get_provider_config",
            side_effect=RuntimeError(_SECRET_FRAGMENT),
        ):
            result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._circuits, {})

    def test_resolve_model_failure_is_typed_fail_closed(self):
        transport = _NoCallTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=lambda _provider, _cfg: (),
            transport=transport,
        )
        with mock.patch.object(
            sidecar.registry,
            "resolve_model",
            side_effect=RuntimeError(_SECRET_FRAGMENT),
        ):
            result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._circuits, {})

    def test_empty_credential_sequence_remains_no_credential(self):
        transport = _NoCallTransport()
        sidecar = ProviderSidecarReference(
            credential_resolver=lambda _provider, _cfg: (),
            transport=transport,
        )
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.NO_CREDENTIAL)
        self.assertNotEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._pressure_snapshot(), (0, 0))

    def test_secret_looking_exception_text_never_serializes_in_dispatch_or_health(self):
        sidecar = ProviderSidecarReference(credential_resolver=self.raising_resolver)
        result = self.dispatch(sidecar)
        health = sidecar.health_report("premium")
        self.assert_local_failure_is_secret_free(
            {"receipt": result.receipt.to_jsonable(), "health": health}
        )

    def test_local_resolution_failure_preserves_open_and_half_open_circuit_state(self):
        for state in (CircuitState.OPEN, CircuitState.HALF_OPEN):
            with self.subTest(state=state):
                transport = _NoCallTransport()
                sidecar = ProviderSidecarReference(
                    credential_resolver=self.raising_resolver,
                    transport=transport,
                )
                circuit = _Circuit(
                    state=state,
                    failures=2,
                    opened_at=123.0,
                    half_open_probe_active=False,
                )
                sidecar._circuits["deepseek"] = circuit
                before = (
                    circuit.state,
                    circuit.failures,
                    circuit.opened_at,
                    circuit.half_open_probe_active,
                )
                result = self.dispatch(sidecar)
                after = (
                    circuit.state,
                    circuit.failures,
                    circuit.opened_at,
                    circuit.half_open_probe_active,
                )
                self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
                self.assertEqual(before, after)
                self.assertEqual(transport.calls, 0)
                self.assertEqual(sidecar._pressure_snapshot(), (0, 0))


if __name__ == "__main__":
    unittest.main()
