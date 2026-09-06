from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
import multiprocessing as mp
import os
import threading
from typing import Any, Iterable

_SCHEMA = "AURA-AIRLLM-PROCESS-ISOLATION-v1"
_MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class IsolationError(RuntimeError):
    pass


class IsolationProtocolError(IsolationError):
    pass


class IsolationWorkerError(IsolationError):
    pass


class IsolationTimeoutError(IsolationError):
    pass


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise IsolationProtocolError("process-isolation messages must be canonical JSON values") from exc


def _decode_json(raw: bytes) -> Any:
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > _MAX_MESSAGE_BYTES:
        raise IsolationProtocolError("invalid or oversized process-isolation message")
    try:
        return json.loads(bytes(raw).decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IsolationProtocolError("process-isolation message is not valid canonical JSON") from exc


def _send_json(conn: Any, value: Any) -> None:
    raw = _canonical_json(value)
    if len(raw) > _MAX_MESSAGE_BYTES:
        raise IsolationProtocolError("process-isolation message exceeds size ceiling")
    conn.send_bytes(raw)


def _recv_json(conn: Any) -> Any:
    return _decode_json(conn.recv_bytes(_MAX_MESSAGE_BYTES))


def _resolve_qualname(module_name: str, qualname: str) -> Any:
    if not isinstance(module_name, str) or not module_name or module_name.strip() != module_name:
        raise IsolationProtocolError("factory module must be an exact non-empty string")
    if not isinstance(qualname, str) or not qualname or qualname.strip() != qualname:
        raise IsolationProtocolError("factory qualname must be an exact non-empty string")
    if any(part.startswith("_") or not part for part in qualname.split(".")):
        raise IsolationProtocolError("private or malformed factory qualnames are not admitted")
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    if not callable(obj):
        raise IsolationProtocolError("resolved factory is not callable")
    return obj


def _normalize_methods(methods: Iterable[str]) -> tuple[str, ...]:
    if isinstance(methods, (str, bytes)):
        raise IsolationProtocolError("allowed_methods must be an iterable of public method names")
    out = tuple(sorted(set(methods)))
    if not out:
        raise IsolationProtocolError("allowed_methods must not be empty")
    for method in out:
        if (
            not isinstance(method, str)
            or not method
            or method.strip() != method
            or method.startswith("_")
            or not method.replace("_", "a").isalnum()
        ):
            raise IsolationProtocolError("allowed method names must be exact public identifiers")
    return out


def _worker_main(
    conn: Any,
    factory_module: str,
    factory_qualname: str,
    init_args: list[Any],
    init_kwargs: dict[str, Any],
    allowed_methods: tuple[str, ...],
) -> None:
    session: Any = None
    try:
        factory = _resolve_qualname(factory_module, factory_qualname)
        session = factory(*init_args, **init_kwargs)
        _send_json(conn, {"kind": "ready", "schema": _SCHEMA, "child_pid": os.getpid()})
        while True:
            request = _recv_json(conn)
            if not isinstance(request, dict) or set(request) != {"kind", "method", "args", "kwargs"}:
                raise IsolationProtocolError("malformed isolation request")
            kind = request["kind"]
            method = request["method"]
            args = request["args"]
            kwargs = request["kwargs"]
            if kind == "close":
                close = getattr(session, "close", None)
                if callable(close):
                    close()
                _send_json(conn, {"kind": "closed", "schema": _SCHEMA})
                return
            if kind != "call" or method not in allowed_methods:
                raise IsolationProtocolError("requested method is not admitted")
            if not isinstance(args, list) or not isinstance(kwargs, dict):
                raise IsolationProtocolError("call args/kwargs must be JSON list/object")
            target = getattr(session, method, None)
            if not callable(target):
                raise IsolationProtocolError("admitted method is not callable on worker session")
            result = target(*args, **kwargs)
            _send_json(conn, {"kind": "result", "schema": _SCHEMA, "method": method, "result": result})
    except BaseException as exc:
        try:
            _send_json(
                conn,
                {
                    "kind": "error",
                    "schema": _SCHEMA,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
            )
        except BaseException:
            pass
    finally:
        try:
            conn.close()
        except BaseException:
            pass


@dataclass(frozen=True)
class IsolationReceipt:
    schema: str
    factory_module: str
    factory_qualname: str
    allowed_methods: tuple[str, ...]
    start_method: str
    authority: str = "D0"
    effect_authority: bool = False
    gate10: bool = False

    @property
    def root(self) -> str:
        payload = {
            "schema": self.schema,
            "factory_module": self.factory_module,
            "factory_qualname": self.factory_qualname,
            "allowed_methods": list(self.allowed_methods),
            "start_method": self.start_method,
            "authority": self.authority,
            "effect_authority": self.effect_authority,
            "gate10": self.gate10,
        }
        return sha256(_canonical_json(payload)).hexdigest()


class IsolatedSessionProxy:
    """Keep patching/mutable runtime state in a dedicated spawned interpreter process.

    The parent exchanges canonical JSON only. No loaded model object, monkey-patched class,
    module global, or arbitrary pickle crosses back into the host interpreter.
    """

    def __init__(
        self,
        *,
        factory_module: str,
        factory_qualname: str,
        allowed_methods: Iterable[str],
        init_args: list[Any] | None = None,
        init_kwargs: dict[str, Any] | None = None,
        startup_timeout: float = 10.0,
        call_timeout: float = 30.0,
    ) -> None:
        self._factory_module = factory_module
        self._factory_qualname = factory_qualname
        self._allowed_methods = _normalize_methods(allowed_methods)
        self._init_args = [] if init_args is None else list(init_args)
        self._init_kwargs = {} if init_kwargs is None else dict(init_kwargs)
        _canonical_json(self._init_args)
        _canonical_json(self._init_kwargs)
        if not isinstance(startup_timeout, (int, float)) or startup_timeout <= 0:
            raise IsolationProtocolError("startup_timeout must be positive")
        if not isinstance(call_timeout, (int, float)) or call_timeout <= 0:
            raise IsolationProtocolError("call_timeout must be positive")
        self._startup_timeout = float(startup_timeout)
        self._call_timeout = float(call_timeout)
        self._ctx = mp.get_context("spawn")
        self._parent_conn: Any = None
        self._process: Any = None
        self._child_pid: int | None = None
        self._poisoned = False
        self._lock = threading.RLock()

    @property
    def receipt(self) -> IsolationReceipt:
        return IsolationReceipt(
            schema=_SCHEMA,
            factory_module=self._factory_module,
            factory_qualname=self._factory_qualname,
            allowed_methods=self._allowed_methods,
            start_method="spawn",
        )

    @property
    def child_pid(self) -> int | None:
        return self._child_pid

    def start(self) -> "IsolatedSessionProxy":
        with self._lock:
            if self._poisoned:
                raise IsolationWorkerError("isolated worker proxy is poisoned and must be recreated")
            if self._process is not None:
                if self._process.is_alive():
                    return self
                raise IsolationWorkerError("isolated worker exited and must not be silently reused")
            parent_conn, child_conn = self._ctx.Pipe(duplex=True)
            process = self._ctx.Process(
                target=_worker_main,
                args=(
                    child_conn,
                    self._factory_module,
                    self._factory_qualname,
                    self._init_args,
                    self._init_kwargs,
                    self._allowed_methods,
                ),
                daemon=True,
            )
            process.start()
            child_conn.close()
            self._parent_conn = parent_conn
            self._process = process
            if not parent_conn.poll(self._startup_timeout):
                self._poisoned = True
                self._terminate()
                raise IsolationTimeoutError("isolated worker did not become ready")
            response = _recv_json(parent_conn)
            if response.get("kind") == "error":
                self._poisoned = True
                self._terminate()
                raise IsolationWorkerError(
                    f"worker startup failed: {response.get('error_type')}: {response.get('message')}"
                )
            if (
                response.get("kind") != "ready"
                or response.get("schema") != _SCHEMA
                or not isinstance(response.get("child_pid"), int)
                or response["child_pid"] == os.getpid()
            ):
                self._poisoned = True
                self._terminate()
                raise IsolationProtocolError("worker readiness receipt is invalid")
            self._child_pid = response["child_pid"]
            return self

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if method not in self._allowed_methods:
                raise IsolationProtocolError("requested method is not admitted")
            self.start()
            request = {"kind": "call", "method": method, "args": list(args), "kwargs": kwargs}
            _send_json(self._parent_conn, request)
            if not self._parent_conn.poll(self._call_timeout):
                self._poisoned = True
                self._terminate()
                raise IsolationTimeoutError("isolated worker call exceeded timeout")
            response = _recv_json(self._parent_conn)
            if response.get("kind") == "error":
                self._poisoned = True
                self._terminate()
                raise IsolationWorkerError(
                    f"worker call failed: {response.get('error_type')}: {response.get('message')}"
                )
            if (
                response.get("kind") != "result"
                or response.get("schema") != _SCHEMA
                or response.get("method") != method
            ):
                self._poisoned = True
                self._terminate()
                raise IsolationProtocolError("worker result receipt is invalid")
            return response.get("result")

    def close(self) -> None:
        with self._lock:
            if self._process is None:
                return
            if self._process.is_alive() and self._parent_conn is not None:
                try:
                    _send_json(
                        self._parent_conn,
                        {"kind": "close", "method": "close", "args": [], "kwargs": {}},
                    )
                    if self._parent_conn.poll(min(self._call_timeout, 5.0)):
                        response = _recv_json(self._parent_conn)
                        if response.get("kind") != "closed":
                            raise IsolationProtocolError("worker close receipt is invalid")
                finally:
                    self._terminate()
            else:
                self._terminate()

    def _terminate(self) -> None:
        process = self._process
        conn = self._parent_conn
        self._process = None
        self._parent_conn = None
        self._child_pid = None
        if conn is not None:
            try:
                conn.close()
            except BaseException:
                pass
        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=2.0)

    def __enter__(self) -> "IsolatedSessionProxy":
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


__all__ = [
    "IsolatedSessionProxy",
    "IsolationError",
    "IsolationProtocolError",
    "IsolationReceipt",
    "IsolationTimeoutError",
    "IsolationWorkerError",
]
