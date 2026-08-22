from __future__ import annotations

import json
import unittest
from unittest import mock
import urllib.error

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


class _SuccessTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def post(self, endpoint, payload, *, bearer, timeout):
        self.calls.append((endpoint, bearer))
        return {"ok": True}


class _UnavailableTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def post(self, endpoint, payload, *, bearer, timeout):
        self.calls.append(endpoint)
        raise urllib.error.URLError("provider unavailable")


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

    def configure_two_provider_registry(
        self,
        sidecar: ProviderSidecarReference,
        *,
        config_side_effect=None,
        model_side_effect=None,
    ) -> None:
        if config_side_effect is None:
            config_side_effect = lambda provider: {
                "api": "openai",
                "base_url": f"https://{provider}.invalid/v1/chat/completions",
            }
        if model_side_effect is None:
            model_side_effect = lambda provider, _ref: f"{provider}-model"
        mock.patch.object(
            sidecar.registry,
            "provider_order",
            return_value=("alpha", "beta"),
        ).start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(
            sidecar.registry,
            "get_provider_config",
            side_effect=config_side_effect,
        ).start()
        mock.patch.object(
            sidecar.registry,
            "resolve_model",
            side_effect=model_side_effect,
        ).start()

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

    def test_f1_later_credential_failure_is_never_resolved_after_first_success(self):
        resolver_calls: list[str] = []
        transport = _SuccessTransport()

        def resolver(provider: str, _cfg: dict) -> tuple[str, ...]:
            resolver_calls.append(provider)
            if provider == "beta":
                raise RuntimeError(_SECRET_FRAGMENT)
            return ("alpha-key",)

        sidecar = ProviderSidecarReference(
            credential_resolver=resolver,
            transport=transport,
        )
        self.configure_two_provider_registry(sidecar)
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.OK)
        self.assertEqual(result.receipt.provider, "alpha")
        self.assertEqual(result.receipt.attempts, 1)
        self.assertEqual(resolver_calls, ["alpha"])
        self.assertEqual(len(transport.calls), 1)

    def test_f2_later_config_and_model_resolution_are_untouched_after_first_success(self):
        config_calls: list[str] = []
        model_calls: list[str] = []
        transport = _SuccessTransport()

        def config(provider: str):
            config_calls.append(provider)
            if provider == "beta":
                raise RuntimeError(_SECRET_FRAGMENT)
            return {
                "api": "openai",
                "base_url": f"https://{provider}.invalid/v1/chat/completions",
            }

        def model(provider: str, _ref: str):
            model_calls.append(provider)
            if provider == "beta":
                raise RuntimeError(_SECRET_FRAGMENT)
            return f"{provider}-model"

        sidecar = ProviderSidecarReference(
            credential_resolver=lambda provider, _cfg: (f"{provider}-key",),
            transport=transport,
        )
        self.configure_two_provider_registry(
            sidecar,
            config_side_effect=config,
            model_side_effect=model,
        )
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.OK)
        self.assertEqual(result.receipt.provider, "alpha")
        self.assertNotIn("beta", config_calls)
        self.assertNotIn("beta", model_calls)
        self.assertEqual(len(transport.calls), 1)

    def test_f3_uncredentialed_first_then_later_local_failure_is_pretransport(self):
        transport = _NoCallTransport()

        def config(provider: str):
            if provider == "beta":
                raise RuntimeError(_SECRET_FRAGMENT)
            return {
                "api": "openai",
                "base_url": f"https://{provider}.invalid/v1/chat/completions",
            }

        sidecar = ProviderSidecarReference(
            credential_resolver=lambda _provider, _cfg: (),
            transport=transport,
        )
        self.configure_two_provider_registry(sidecar, config_side_effect=config)
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.attempts, 0)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(result.receipt.queue_depth, 0)
        self.assertEqual(transport.calls, 0)
        self.assertEqual(sidecar._pressure_snapshot(), (0, 0))
        self.assertEqual(sidecar._circuits, {})
        self.assert_local_failure_is_secret_free(result.receipt.to_jsonable())

    def test_f4_prior_transport_attempt_is_preserved_when_later_resolution_fails(self):
        transport = _UnavailableTransport()

        def config(provider: str):
            if provider == "beta":
                raise RuntimeError(_SECRET_FRAGMENT)
            return {
                "api": "openai",
                "base_url": f"https://{provider}.invalid/v1/chat/completions",
            }

        sidecar = ProviderSidecarReference(
            credential_resolver=lambda provider, _cfg: ("alpha-key",) if provider == "alpha" else (),
            transport=transport,
            circuit_failure_threshold=3,
        )
        self.configure_two_provider_registry(sidecar, config_side_effect=config)
        with mock.patch.object(sidecar, "_release", wraps=sidecar._release) as release:
            result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.LOCAL_RESOLUTION_ERROR)
        self.assertEqual(result.receipt.attempts, 1)
        self.assertEqual(result.receipt.provider, "alpha")
        self.assertEqual(result.receipt.fallback_index, 0)
        self.assertEqual(result.receipt.in_flight, 0)
        self.assertEqual(result.receipt.queue_depth, 0)
        self.assertEqual(release.call_count, 1)
        self.assertEqual(sidecar._pressure_snapshot(), (0, 0))
        self.assertIn("alpha", sidecar._circuits)
        self.assertNotIn("beta", sidecar._circuits)
        self.assertEqual(len(transport.calls), 1)
        self.assert_local_failure_is_secret_free(result.receipt.to_jsonable())

    def test_f5_later_circuit_and_resolution_instrumentation_are_untouched_after_success(self):
        resolver_calls: list[str] = []
        config_calls: list[str] = []
        transport = _SuccessTransport()

        def config(provider: str):
            config_calls.append(provider)
            return {
                "api": "openai",
                "base_url": f"https://{provider}.invalid/v1/chat/completions",
            }

        def resolver(provider: str, _cfg: dict) -> tuple[str, ...]:
            resolver_calls.append(provider)
            return (f"{provider}-key",)

        sidecar = ProviderSidecarReference(
            credential_resolver=resolver,
            transport=transport,
        )
        self.configure_two_provider_registry(sidecar, config_side_effect=config)
        beta = _Circuit(
            state=CircuitState.HALF_OPEN,
            failures=2,
            opened_at=123.0,
            half_open_probe_active=False,
        )
        sidecar._circuits["beta"] = beta
        before = (beta.state, beta.failures, beta.opened_at, beta.half_open_probe_active)
        result = self.dispatch(sidecar)
        after = (beta.state, beta.failures, beta.opened_at, beta.half_open_probe_active)
        self.assertEqual(result.receipt.status, SidecarStatus.OK)
        self.assertEqual(result.receipt.provider, "alpha")
        self.assertEqual(before, after)
        self.assertNotIn("beta", resolver_calls)
        self.assertNotIn("beta", config_calls)

    def test_f6_uncredentialed_first_candidate_falls_through_to_valid_second(self):
        resolver_calls: list[str] = []
        transport = _SuccessTransport()

        def resolver(provider: str, _cfg: dict) -> tuple[str, ...]:
            resolver_calls.append(provider)
            return () if provider == "alpha" else ("beta-key",)

        sidecar = ProviderSidecarReference(
            credential_resolver=resolver,
            transport=transport,
        )
        self.configure_two_provider_registry(sidecar)
        result = self.dispatch(sidecar)
        self.assertEqual(result.receipt.status, SidecarStatus.OK)
        self.assertEqual(result.receipt.provider, "beta")
        self.assertEqual(result.receipt.fallback_index, 1)
        self.assertEqual(result.receipt.attempts, 1)
        self.assertEqual(resolver_calls, ["alpha", "beta"])
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(transport.calls[0][0].startswith("https://beta.invalid/"))


if __name__ == "__main__":
    unittest.main()
