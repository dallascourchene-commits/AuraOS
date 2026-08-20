from __future__ import annotations

import http.client
import socket
import unittest
import urllib.error

from tools.project006.provider_sidecar_reference.provider_sidecar import (
    CircuitState,
    DispatchBinding,
    InvalidContentType,
    ProviderSidecarReference,
    SidecarStatus,
    StrictJsonTransport,
    _Circuit,
)


_SECRET = "sk-test-DO-NOT-LEAK-1234567890"


def _credentials(provider: str, _cfg: dict) -> tuple[str, ...]:
    return (_SECRET,) if provider == "deepseek" else ()


class _UnavailableTransport:
    def post(self, endpoint, payload, *, bearer, timeout):
        raise urllib.error.HTTPError(endpoint, 503, "unavailable", {}, None)


class _HTTPProtocolErrorTransport:
    def post(self, endpoint, payload, *, bearer, timeout):
        raise http.client.IncompleteRead(b"partial", 10)


class _Response:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body = body
        self.headers = headers
        self.read_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit: int) -> bytes:
        self.read_calls += 1
        return self.body[:limit]


class _Opener:
    def __init__(self, result=None, error: BaseException | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def open(self, req, timeout):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class ProviderSidecarRepairG3Tests(unittest.TestCase):
    def binding(self, capsule_id="CAP-G3"):
        return DispatchBinding(
            capsule_id=capsule_id,
            lease_generation=4,
            fencing_token="FENCE-9",
            currentness_ref="SRC-94705ec7",
        )

    def test_terminal_receipts_bind_last_credentialed_route(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_UnavailableTransport(),
            circuit_failure_threshold=1,
            circuit_cooldown_sec=60.0,
        )
        first = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding("CAP-FIRST"),
            messages=[{"role": "user", "content": "first"}],
            retry_budget=0,
        )
        self.assertEqual(first.receipt.provider, "deepseek")
        self.assertEqual(first.receipt.circuit_state, CircuitState.OPEN)

        second = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding("CAP-SECOND"),
            messages=[{"role": "user", "content": "second"}],
            retry_budget=0,
        )
        self.assertEqual(second.receipt.status, SidecarStatus.CIRCUIT_OPEN)
        self.assertEqual(second.receipt.provider, "deepseek")
        self.assertEqual(second.receipt.circuit_state, CircuitState.OPEN)

    def test_http_protocol_error_releases_half_open_probe(self):
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=_HTTPProtocolErrorTransport(),
            circuit_failure_threshold=1,
            circuit_cooldown_sec=0.0,
        )
        sidecar._circuits["deepseek"] = _Circuit(
            state=CircuitState.OPEN,
            failures=1,
            opened_at=0.0,
            half_open_probe_active=False,
        )
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "probe"}],
            retry_budget=0,
        )
        self.assertIn(
            result.receipt.status,
            (SidecarStatus.CIRCUIT_OPEN, SidecarStatus.PROVIDER_UNAVAILABLE),
        )
        circuit = sidecar._circuits["deepseek"]
        self.assertEqual(circuit.state, CircuitState.OPEN)
        self.assertFalse(circuit.half_open_probe_active)

    def test_json_media_type_requires_exact_or_structured_suffix(self):
        for invalid in (
            "application/jsonp",
            "text/html; profile=application/json",
            "text/plain+jsonish",
        ):
            response = _Response(b"{}", {"Content-Type": invalid})
            transport = StrictJsonTransport(opener=_Opener(result=response))
            with self.assertRaises(InvalidContentType):
                transport.post(
                    "https://api.deepseek.com/chat/completions",
                    {"model": "x", "messages": []},
                    bearer=_SECRET,
                    timeout=1.0,
                )
            self.assertEqual(response.read_calls, 0)

        for valid in (
            "application/json",
            "application/json; charset=utf-8",
            "application/problem+json",
            "application/vnd.api+json; charset=utf-8",
        ):
            response = _Response(b"{}", {"Content-Type": valid})
            transport = StrictJsonTransport(opener=_Opener(result=response))
            self.assertEqual(
                transport.post(
                    "https://api.deepseek.com/chat/completions",
                    {"model": "x", "messages": []},
                    bearer=_SECRET,
                    timeout=1.0,
                ),
                {},
            )

    def test_wrapped_socket_timeout_preserves_timeout_semantics(self):
        opener = _Opener(error=urllib.error.URLError(socket.timeout("timed out")))
        sidecar = ProviderSidecarReference(
            credential_resolver=_credentials,
            transport=StrictJsonTransport(opener=opener),
            circuit_failure_threshold=1,
        )
        result = sidecar.dispatch(
            route_ref="premium",
            binding=self.binding(),
            messages=[{"role": "user", "content": "timeout"}],
            retry_budget=0,
        )
        self.assertEqual(result.receipt.status, SidecarStatus.TIMEOUT)
        self.assertEqual(result.receipt.provider, "deepseek")
        self.assertEqual(result.receipt.circuit_state, CircuitState.OPEN)
        self.assertEqual(opener.calls, 1)


if __name__ == "__main__":
    unittest.main()
