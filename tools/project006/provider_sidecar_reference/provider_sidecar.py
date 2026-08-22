"""Project006 Provider Dispatcher Sidecar reference.

This module is deliberately isolated from the Resident process. It accepts only
logical route references, resolves provider/model/endpoint from Aura's canonical
ProviderRegistry, keeps credentials inside the provider-facing process, and
emits typed receipts that never contain credential values.

It is a review/staging reference, not proof of deployment or live provider use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import http.client
import json
import math
import socket
import ssl
import threading
import time
from typing import Any, Callable, Mapping, Sequence
import urllib.error
import urllib.request

from aura_provider_registry import ProviderRegistry


_ALLOWED_ROUTE_REFS = frozenset(
    {
        "primary",
        "premium",
        "reasoner",
        "coding",
        "cheap_builder",
        "shadow",
        "summarizer",
    }
)


class SidecarStatus(str, Enum):
    OK = "OK"
    INVALID_ROUTE = "INVALID_ROUTE"
    NO_CREDENTIAL = "NO_CREDENTIAL"
    LOCAL_RESOLUTION_ERROR = "LOCAL_RESOLUTION_ERROR"
    QUEUE_FULL = "QUEUE_FULL"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    RETRYABLE_PROVIDER_PRESSURE = "RETRYABLE_PROVIDER_PRESSURE"
    TIMEOUT = "TIMEOUT"
    TLS_FAILURE = "TLS_FAILURE"
    REDIRECT_BLOCKED = "REDIRECT_BLOCKED"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_CONTENT_TYPE = "INVALID_CONTENT_TYPE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class StrictTLSFailure(RuntimeError):
    """Certificate or hostname validation failed; never retry insecurely."""


class RedirectBlocked(RuntimeError):
    """Provider attempted an HTTP redirect outside the frozen endpoint request."""


class ResponseTooLarge(RuntimeError):
    """Provider response exceeded the configured byte ceiling."""


class InvalidContentType(RuntimeError):
    """Provider response was not declared as JSON."""


class LocalResolutionFailure(RuntimeError):
    """Local provider capability resolution failed; never serialize the cause."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class ProviderRoute:
    route_ref: str
    provider: str
    model: str
    endpoint: str
    fallback_index: int


@dataclass(frozen=True)
class DispatchBinding:
    capsule_id: str
    lease_generation: int
    fencing_token: str
    currentness_ref: str

    def attempt_id(self, route_ref: str, execution_digest: str) -> str:
        material = "\x1f".join(
            (
                self.capsule_id,
                str(self.lease_generation),
                self.fencing_token,
                self.currentness_ref,
                route_ref,
                execution_digest,
            )
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class ProviderReceipt:
    status: SidecarStatus
    dispatch_attempt_id: str
    execution_digest: str
    route_ref: str
    provider: str | None
    model: str | None
    fallback_index: int | None
    circuit_state: CircuitState
    in_flight: int
    queue_depth: int
    retry_after_ms: int | None = None
    attempts: int = 0

    def to_jsonable(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["circuit_state"] = self.circuit_state.value
        return data


@dataclass(frozen=True)
class DispatchResult:
    response: Mapping[str, Any] | None
    receipt: ProviderReceipt


@dataclass
class _Circuit:
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: float = 0.0
    half_open_probe_active: bool = False


class StrictJsonTransport:
    """Bounded HTTPS JSON transport with verification and redirects fail closed."""

    def __init__(
        self,
        *,
        max_response_bytes: int = 4 * 1024 * 1024,
        require_json_content_type: bool = True,
        opener: Any | None = None,
    ) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self.max_response_bytes = int(max_response_bytes)
        self.require_json_content_type = bool(require_json_content_type)
        # The standard HTTPSHandler uses Python's verified default SSL context.
        # Redirects are disabled so a credential-bearing request cannot escape
        # the exact registry-selected endpoint through a provider-controlled 3xx.
        self._opener = opener or urllib.request.build_opener(_NoRedirectHandler())

    @staticmethod
    def _content_type(response: Any) -> str:
        headers = getattr(response, "headers", None)
        if headers is not None and hasattr(headers, "get"):
            value = headers.get("Content-Type")
            if value:
                return str(value)
        if hasattr(response, "getheader"):
            value = response.getheader("Content-Type")
            if value:
                return str(value)
        return ""

    @staticmethod
    def _is_json_media_type(content_type: str) -> bool:
        media_type = str(content_type or "").split(";", 1)[0].strip().lower()
        if media_type == "application/json":
            return True
        if "/" not in media_type:
            return False
        media_type_name, subtype = media_type.split("/", 1)
        return bool(
            media_type_name
            and subtype.endswith("+json")
            and len(subtype) > len("+json")
        )

    @staticmethod
    def _content_length(response: Any) -> int | None:
        headers = getattr(response, "headers", None)
        value = headers.get("Content-Length") if headers is not None and hasattr(headers, "get") else None
        if value is None and hasattr(response, "getheader"):
            value = response.getheader("Content-Length")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def post(
        self,
        endpoint: str,
        payload: Mapping[str, Any],
        *,
        bearer: str,
        timeout: float,
    ) -> Mapping[str, Any]:
        if not endpoint.lower().startswith("https://"):
            raise ValueError("provider endpoint must use https")
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(dict(payload)).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer}",
            },
            method="POST",
        )
        try:
            with self._opener.open(req, timeout=timeout) as response:
                content_type = self._content_type(response)
                if self.require_json_content_type and not self._is_json_media_type(content_type):
                    raise InvalidContentType("provider response content type is not JSON")
                declared = self._content_length(response)
                if declared is not None and declared > self.max_response_bytes:
                    raise ResponseTooLarge("provider response content length exceeds limit")
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ResponseTooLarge("provider response exceeds byte limit")
        except urllib.error.HTTPError as exc:
            if 300 <= int(exc.code) < 400:
                raise RedirectBlocked("provider redirect blocked") from exc
            raise
        except ssl.SSLError as exc:
            raise StrictTLSFailure("provider TLS verification failed") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, ssl.SSLError):
                raise StrictTLSFailure("provider TLS verification failed") from exc
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise socket.timeout(str(reason) or "provider request timed out") from exc
            raise

        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, Mapping):
            raise ValueError("provider response must be a JSON object")
        return decoded


CredentialResolver = Callable[[str, Mapping[str, Any]], Sequence[str]]


class ProviderSidecarReference:
    """Bounded provider-facing dispatcher for Project006 review/staging.

    The Resident is expected to provide ``route_ref`` only. It never supplies a
    URL, hostname, IP address, API key, or provider credential identifier.
    """

    def __init__(
        self,
        *,
        credential_resolver: CredentialResolver,
        registry: ProviderRegistry | None = None,
        transport: StrictJsonTransport | None = None,
        concurrency_limit: int = 9,
        queue_limit: int = 27,
        circuit_failure_threshold: int = 3,
        circuit_cooldown_sec: float = 30.0,
    ) -> None:
        if concurrency_limit <= 0:
            raise ValueError("concurrency_limit must be positive")
        if queue_limit < 0:
            raise ValueError("queue_limit cannot be negative")
        if circuit_failure_threshold <= 0:
            raise ValueError("circuit_failure_threshold must be positive")
        if circuit_cooldown_sec < 0:
            raise ValueError("circuit_cooldown_sec cannot be negative")
        self.registry = registry or ProviderRegistry()
        self.credential_resolver = credential_resolver
        self.transport = transport or StrictJsonTransport()
        self.concurrency_limit = concurrency_limit
        self.queue_limit = queue_limit
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_cooldown_sec = circuit_cooldown_sec
        self._condition = threading.Condition()
        self._in_flight = 0
        self._queued = 0
        self._circuits: dict[str, _Circuit] = {}

    @staticmethod
    def validate_route_ref(route_ref: str) -> str:
        ref = str(route_ref or "").strip().lower()
        if any(marker in ref for marker in ("://", "/", "\\", "@")):
            raise ValueError("route_ref cannot contain a network destination")
        if ref not in _ALLOWED_ROUTE_REFS:
            raise ValueError("route_ref must be a registered logical role")
        return ref

    @staticmethod
    def execution_digest(
        messages: Sequence[Mapping[str, str]],
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        material = {
            "messages": [dict(item) for item in messages],
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        canonical = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _provider_order(self, route_ref: str) -> tuple[str, tuple[str, ...]]:
        """Resolve only the logical ordered provider list for one route ref."""
        ref = self.validate_route_ref(route_ref)
        try:
            return ref, tuple(self.registry.provider_order(ref))
        except Exception as exc:
            raise LocalResolutionFailure from exc

    def _resolve_route(
        self,
        route_ref: str,
        provider: str,
        fallback_index: int,
    ) -> ProviderRoute | None:
        """Resolve one reached fallback candidate without touching later candidates."""
        try:
            cfg = self.registry.get_provider_config(provider)
            if not cfg or str(cfg.get("api") or "openai") != "openai":
                return None
            endpoint = str(cfg.get("base_url") or cfg.get("url") or "")
            if not endpoint.lower().startswith("https://"):
                return None
            model = self.registry.resolve_model(provider, route_ref)
        except Exception as exc:
            raise LocalResolutionFailure from exc
        return ProviderRoute(
            route_ref=route_ref,
            provider=provider,
            model=model,
            endpoint=endpoint,
            fallback_index=fallback_index,
        )

    def _routes(self, route_ref: str) -> list[ProviderRoute]:
        """Eager route enumeration retained for bounded health-report inspection."""
        ref, provider_order = self._provider_order(route_ref)
        routes: list[ProviderRoute] = []
        for index, provider in enumerate(provider_order):
            route = self._resolve_route(ref, provider, index)
            if route is not None:
                routes.append(route)
        return routes

    def _credentials_for_route(self, route: ProviderRoute) -> tuple[str, ...]:
        try:
            cfg = self.registry.get_provider_config(route.provider) or {}
            return tuple(self.credential_resolver(route.provider, cfg))
        except Exception as exc:
            raise LocalResolutionFailure from exc

    def _pressure_snapshot(self) -> tuple[int, int]:
        with self._condition:
            return self._in_flight, self._queued

    def _admit(self, deadline: float) -> SidecarStatus | None:
        """Admit or return the typed reason admission failed."""
        with self._condition:
            if self._in_flight < self.concurrency_limit:
                self._in_flight += 1
                return None
            if self._queued >= self.queue_limit:
                return SidecarStatus.QUEUE_FULL
            self._queued += 1
            try:
                while self._in_flight >= self.concurrency_limit:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return SidecarStatus.TIMEOUT
                    self._condition.wait(timeout=remaining)
                self._in_flight += 1
                return None
            finally:
                self._queued -= 1

    def _release(self) -> None:
        with self._condition:
            self._in_flight -= 1
            if self._in_flight < 0:
                self._in_flight = 0
                raise RuntimeError("provider admission accounting underflow")
            self._condition.notify()

    def _circuit_state(self, provider: str | None) -> CircuitState:
        """Pure circuit introspection: reporting must never create/mutate state."""
        if not provider:
            return CircuitState.CLOSED
        with self._condition:
            circuit = self._circuits.get(provider)
            return circuit.state if circuit is not None else CircuitState.CLOSED

    def _circuit_allows(self, provider: str) -> bool:
        """Mutating admission transition; call only for an actual dispatch probe."""
        now = time.monotonic()
        with self._condition:
            circuit = self._circuits.setdefault(provider, _Circuit())
            if circuit.state is CircuitState.CLOSED:
                return True
            if circuit.state is CircuitState.OPEN:
                if now - circuit.opened_at < self.circuit_cooldown_sec:
                    return False
                circuit.state = CircuitState.HALF_OPEN
                circuit.half_open_probe_active = False
            if circuit.half_open_probe_active:
                return False
            circuit.half_open_probe_active = True
            return True

    def _record_success(self, provider: str) -> None:
        with self._condition:
            circuit = self._circuits.setdefault(provider, _Circuit())
            circuit.state = CircuitState.CLOSED
            circuit.failures = 0
            circuit.opened_at = 0.0
            circuit.half_open_probe_active = False

    def _record_failure(self, provider: str) -> None:
        with self._condition:
            circuit = self._circuits.setdefault(provider, _Circuit())
            circuit.failures += 1
            circuit.half_open_probe_active = False
            if circuit.state is CircuitState.HALF_OPEN or circuit.failures >= self.circuit_failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.monotonic()

    def _record_neutral(self, provider: str) -> None:
        """Release an admitted probe without treating request-specific 4xx as provider health evidence."""
        with self._condition:
            circuit = self._circuits.setdefault(provider, _Circuit())
            circuit.half_open_probe_active = False
            if circuit.state is CircuitState.HALF_OPEN:
                # Preserve the prior OPEN evidence and high-water timestamp. A
                # later valid request may probe again without client input
                # manufacturing either provider recovery or provider failure.
                circuit.state = CircuitState.OPEN

    def _record_pressure(self, provider: str) -> None:
        """Release a half-open probe on 429 without treating keys as capacity."""
        with self._condition:
            circuit = self._circuits.setdefault(provider, _Circuit())
            circuit.half_open_probe_active = False
            if circuit.state is CircuitState.HALF_OPEN:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.monotonic()

    def _receipt(
        self,
        *,
        status: SidecarStatus,
        attempt_id: str,
        execution_digest: str,
        route_ref: str,
        route: ProviderRoute | None,
        attempts: int,
        retry_after_ms: int | None = None,
    ) -> ProviderReceipt:
        in_flight, queued = self._pressure_snapshot()
        return ProviderReceipt(
            status=status,
            dispatch_attempt_id=attempt_id,
            execution_digest=execution_digest,
            route_ref=route_ref,
            provider=route.provider if route else None,
            model=route.model if route else None,
            fallback_index=route.fallback_index if route else None,
            circuit_state=self._circuit_state(route.provider if route else None),
            in_flight=in_flight,
            queue_depth=queued,
            retry_after_ms=retry_after_ms,
            attempts=attempts,
        )

    @staticmethod
    def _retry_after_ms(exc: urllib.error.HTTPError) -> int | None:
        headers = getattr(exc, "headers", None)
        value = headers.get("Retry-After") if headers is not None and hasattr(headers, "get") else None
        if value is None:
            return None
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(seconds) or seconds < 0:
            return None
        milliseconds = seconds * 1000
        if not math.isfinite(milliseconds):
            return None
        return int(milliseconds)

    def _health_payload(
        self,
        *,
        route_ref: str,
        status: SidecarStatus,
        providers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        in_flight, queued = self._pressure_snapshot()
        return {
            "status": status.value,
            "route_ref": route_ref,
            "concurrency_limit": self.concurrency_limit,
            "queue_limit": self.queue_limit,
            "in_flight": in_flight,
            "queue_depth": queued,
            "providers": providers,
        }

    def health_report(self, route_ref: str) -> dict[str, Any]:
        """Return zero-secret routing/pressure state for Lane C or health UI."""
        ref = self.validate_route_ref(route_ref)
        providers: list[dict[str, Any]] = []
        try:
            routes = self._routes(ref)
            for route in routes:
                credentials = self._credentials_for_route(route)
                key_count = len(credentials)
                providers.append(
                    {
                        "provider": route.provider,
                        "model": route.model,
                        "configured": key_count > 0,
                        "key_count": key_count,
                        "fallback_index": route.fallback_index,
                        "circuit_state": self._circuit_state(route.provider).value,
                    }
                )
        except LocalResolutionFailure:
            return self._health_payload(
                route_ref=ref,
                status=SidecarStatus.LOCAL_RESOLUTION_ERROR,
                providers=[],
            )
        return self._health_payload(
            route_ref=ref,
            status=SidecarStatus.OK,
            providers=providers,
        )

    def dispatch(
        self,
        *,
        route_ref: str,
        binding: DispatchBinding,
        messages: Sequence[Mapping[str, str]],
        max_tokens: int = 900,
        temperature: float = 0.0,
        total_deadline_sec: float = 60.0,
        retry_budget: int = 1,
    ) -> DispatchResult:
        """Dispatch one bounded request and return response + redacted receipt."""
        execution_digest = self.execution_digest(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        normalized_ref = str(route_ref or "").strip().lower()
        attempt_id = binding.attempt_id(normalized_ref, execution_digest)
        try:
            ref = self.validate_route_ref(route_ref)
        except ValueError:
            return DispatchResult(
                None,
                self._receipt(
                    status=SidecarStatus.INVALID_ROUTE,
                    attempt_id=attempt_id,
                    execution_digest=execution_digest,
                    route_ref=str(route_ref or ""),
                    route=None,
                    attempts=0,
                ),
            )
        if total_deadline_sec <= 0 or retry_budget < 0:
            raise ValueError("deadline must be positive and retry_budget non-negative")
        deadline = time.monotonic() + total_deadline_sec

        try:
            _, provider_order = self._provider_order(ref)
        except LocalResolutionFailure:
            return DispatchResult(
                None,
                self._receipt(
                    status=SidecarStatus.LOCAL_RESOLUTION_ERROR,
                    attempt_id=attempt_id,
                    execution_digest=execution_digest,
                    route_ref=ref,
                    route=None,
                    attempts=0,
                ),
            )

        attempts = 0
        saw_credential = False
        saw_open_circuit = False
        last_effective_route: ProviderRoute | None = None
        last_status = SidecarStatus.PROVIDER_UNAVAILABLE
        last_retry_after_ms: int | None = None
        admission_held = False

        try:
            for index, provider in enumerate(provider_order):
                try:
                    route = self._resolve_route(ref, provider, index)
                    if route is None:
                        continue
                    credentials = self._credentials_for_route(route)
                except LocalResolutionFailure:
                    # A local failure must never leak a cause, create/mutate the
                    # unresolved candidate's circuit, or erase truthful prior
                    # transport accounting. If dispatch admission was already
                    # acquired for an earlier runnable fallback, release it
                    # before taking the pressure snapshot for the error receipt.
                    if admission_held:
                        self._release()
                        admission_held = False
                    return DispatchResult(
                        None,
                        self._receipt(
                            status=SidecarStatus.LOCAL_RESOLUTION_ERROR,
                            attempt_id=attempt_id,
                            execution_digest=execution_digest,
                            route_ref=ref,
                            route=last_effective_route,
                            attempts=attempts,
                        ),
                    )

                if not credentials:
                    continue
                saw_credential = True
                # Only a credentialed route may become the terminal route binding.
                # Later uncredentialed fallback enumeration must never overwrite it.
                last_effective_route = route

                # Global admission is dispatch-scoped and acquired only once the
                # first runnable candidate is actually reached. It remains held
                # across lawful fallback attempts, then is released exactly once.
                if not admission_held:
                    admission_failure = self._admit(deadline)
                    if admission_failure is not None:
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=admission_failure,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    admission_held = True

                # Candidate-local resolution is complete before circuit mutation.
                if not self._circuit_allows(route.provider):
                    saw_open_circuit = True
                    continue

                # Provider/account concurrency is not multiplied by key count.
                credential = credentials[0]
                payload = {
                    "model": route.model,
                    "messages": [dict(item) for item in messages],
                    "max_tokens": int(max_tokens),
                    "temperature": float(temperature),
                }
                for retry_index in range(retry_budget + 1):
                    attempts += 1
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._record_failure(route.provider)
                        last_status = SidecarStatus.TIMEOUT
                        break
                    try:
                        response = self.transport.post(
                            route.endpoint,
                            payload,
                            bearer=credential,
                            timeout=remaining,
                        )
                    except StrictTLSFailure:
                        self._record_failure(route.provider)
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=SidecarStatus.TLS_FAILURE,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    except RedirectBlocked:
                        self._record_failure(route.provider)
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=SidecarStatus.REDIRECT_BLOCKED,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    except ResponseTooLarge:
                        self._record_failure(route.provider)
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=SidecarStatus.RESPONSE_TOO_LARGE,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    except InvalidContentType:
                        self._record_failure(route.provider)
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=SidecarStatus.INVALID_CONTENT_TYPE,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    except urllib.error.HTTPError as exc:
                        if exc.code == 429:
                            self._record_pressure(route.provider)
                            last_retry_after_ms = self._retry_after_ms(exc)
                            return DispatchResult(
                                None,
                                self._receipt(
                                    status=SidecarStatus.RETRYABLE_PROVIDER_PRESSURE,
                                    attempt_id=attempt_id,
                                    execution_digest=execution_digest,
                                    route_ref=ref,
                                    route=route,
                                    attempts=attempts,
                                    retry_after_ms=last_retry_after_ms,
                                ),
                            )
                        if 400 <= int(exc.code) < 500:
                            # Request-specific client errors are not evidence that
                            # the shared provider is unhealthy. Release a possible
                            # HALF_OPEN probe without incrementing its breaker.
                            self._record_neutral(route.provider)
                            return DispatchResult(
                                None,
                                self._receipt(
                                    status=(
                                        SidecarStatus.TIMEOUT
                                        if int(exc.code) == 408
                                        else SidecarStatus.PROVIDER_UNAVAILABLE
                                    ),
                                    attempt_id=attempt_id,
                                    execution_digest=execution_digest,
                                    route_ref=ref,
                                    route=route,
                                    attempts=attempts,
                                ),
                            )
                        self._record_failure(route.provider)
                        last_status = SidecarStatus.PROVIDER_UNAVAILABLE
                        if exc.code not in (500, 502, 503, 504):
                            break
                    except (TimeoutError, socket.timeout):
                        self._record_failure(route.provider)
                        last_status = SidecarStatus.TIMEOUT
                    except http.client.HTTPException:
                        # Protocol failures may occur after HALF_OPEN admission
                        # (e.g. IncompleteRead/BadStatusLine). Always release/reopen
                        # the probe via _record_failure before returning/retrying.
                        self._record_failure(route.provider)
                        last_status = SidecarStatus.PROVIDER_UNAVAILABLE
                    except (urllib.error.URLError, OSError):
                        self._record_failure(route.provider)
                        last_status = SidecarStatus.PROVIDER_UNAVAILABLE
                    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                        self._record_failure(route.provider)
                        return DispatchResult(
                            None,
                            self._receipt(
                                status=SidecarStatus.MALFORMED_RESPONSE,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )
                    else:
                        self._record_success(route.provider)
                        return DispatchResult(
                            response,
                            self._receipt(
                                status=SidecarStatus.OK,
                                attempt_id=attempt_id,
                                execution_digest=execution_digest,
                                route_ref=ref,
                                route=route,
                                attempts=attempts,
                            ),
                        )

                    if self._circuit_state(route.provider) is CircuitState.OPEN:
                        saw_open_circuit = True
                        break
                    if retry_index >= retry_budget:
                        break

            if not saw_credential:
                status = SidecarStatus.NO_CREDENTIAL
            elif saw_open_circuit and last_status is SidecarStatus.PROVIDER_UNAVAILABLE:
                status = SidecarStatus.CIRCUIT_OPEN
            else:
                status = last_status
            return DispatchResult(
                None,
                self._receipt(
                    status=status,
                    attempt_id=attempt_id,
                    execution_digest=execution_digest,
                    route_ref=ref,
                    route=last_effective_route,
                    attempts=attempts,
                    retry_after_ms=last_retry_after_ms,
                ),
            )
        finally:
            if admission_held:
                self._release()
