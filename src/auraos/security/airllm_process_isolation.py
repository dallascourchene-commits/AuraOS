"""Process boundary for loaders that must temporarily mutate process-global state.

This module proves *concurrency noninterference*, not privilege separation. The
child process owns any temporary monkey-patches; unrelated callers in the parent
process cannot observe those mutations. IPC still uses Python multiprocessing
serialization and therefore must be used only between trusted AuraOS code.

The worker receipt binds a fresh child nonce and importable factory identity so a
historical READY tuple cannot be replayed as a current worker instantiation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
import multiprocessing as mp
import os
import pickle
import re
import secrets
from multiprocessing.connection import Connection
from typing import Any

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IsolationBoundaryError(RuntimeError):
    """Base class for process-isolation failures."""


class RemoteInvocationError(IsolationBoundaryError):
    """A child-side operation failed; only sanitized metadata crosses the boundary."""

    def __init__(self, error_type: str, message: str):
        super().__init__(f"isolated child {error_type}: {message}")
        self.error_type = error_type
        self.remote_message = message


@dataclass(frozen=True)
class IsolationReceipt:
    parent_pid: int
    child_pid: int
    start_method: str
    generation: int
    worker_nonce_root: str
    factory_identity_root: str
    receipt_root: str
    authority_ceiling: str = "D0_PROCESS_ISOLATION_ONLY"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _factory_identity_root(module_name: str, qualname: str) -> str:
    return _digest({"module_name": module_name, "qualname": qualname})


def _validate_receipt_fields(
    *,
    parent_pid: int,
    child_pid: int,
    start_method: str,
    generation: int,
    worker_nonce_root: str,
    factory_identity_root: str,
) -> str:
    if type(parent_pid) is not int or type(child_pid) is not int:
        raise IsolationBoundaryError("receipt PIDs must be exact integers")
    if parent_pid <= 0 or child_pid <= 0 or parent_pid == child_pid:
        raise IsolationBoundaryError("receipt PIDs must be positive and distinct")
    if start_method != "spawn":
        raise IsolationBoundaryError("only multiprocessing spawn is admitted")
    if type(generation) is not int or generation <= 0:
        raise IsolationBoundaryError("receipt generation must be a positive integer")
    if not isinstance(worker_nonce_root, str) or _HEX64.fullmatch(worker_nonce_root) is None:
        raise IsolationBoundaryError("worker nonce root must be exact lowercase 64-hex")
    if not isinstance(factory_identity_root, str) or _HEX64.fullmatch(factory_identity_root) is None:
        raise IsolationBoundaryError("factory identity root must be exact lowercase 64-hex")
    body = {
        "parent_pid": parent_pid,
        "child_pid": child_pid,
        "start_method": start_method,
        "generation": generation,
        "worker_nonce_root": worker_nonce_root,
        "factory_identity_root": factory_identity_root,
        "authority_ceiling": "D0_PROCESS_ISOLATION_ONLY",
    }
    return _digest(body)


def _resolve_symbol(module_name: str, qualname: str) -> Any:
    if not isinstance(module_name, str) or not module_name:
        raise IsolationBoundaryError("module_name must be a non-empty string")
    if not isinstance(qualname, str) or not qualname or "<locals>" in qualname:
        raise IsolationBoundaryError("qualname must identify an importable top-level symbol")
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        if not part or part.startswith("_"):
            raise IsolationBoundaryError("private or malformed symbol paths are not admitted")
        obj = getattr(obj, part)
    return obj


def _sanitized_error(exc: BaseException) -> tuple[str, str]:
    return type(exc).__name__, str(exc)[:1024]


def _assert_picklable(value: Any, *, label: str) -> None:
    try:
        pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    except BaseException as exc:
        raise IsolationBoundaryError(f"{label} is not admitted across multiprocessing IPC") from exc


def _worker_main(
    conn: Connection,
    parent_pid: int,
    module_name: str,
    qualname: str,
    init_args: tuple[Any, ...],
    init_kwargs: dict[str, Any],
) -> None:
    target: Any = None
    try:
        factory = _resolve_symbol(module_name, qualname)
        target = factory(*init_args, **init_kwargs)
        worker_nonce_root = sha256(secrets.token_bytes(32)).hexdigest()
        factory_root = _factory_identity_root(module_name, qualname)
        conn.send(("READY", os.getpid(), worker_nonce_root, factory_root))
        while True:
            request = conn.recv()
            if not isinstance(request, tuple) or not request:
                raise IsolationBoundaryError("malformed IPC request")
            opcode = request[0]
            if opcode == "CLOSE":
                closer = getattr(target, "close", None)
                if callable(closer):
                    closer()
                conn.send(("CLOSED", os.getpid()))
                target = None
                return
            if opcode != "CALL" or len(request) != 4:
                conn.send(("ERROR", "IsolationBoundaryError", "unknown IPC opcode"))
                continue
            _, method_name, args, kwargs = request
            if (
                not isinstance(method_name, str)
                or not method_name
                or method_name.startswith("_")
                or not method_name.isidentifier()
            ):
                conn.send((
                    "ERROR",
                    "IsolationBoundaryError",
                    "private or malformed method names are not admitted",
                ))
                continue
            method = getattr(target, method_name, None)
            if not callable(method):
                conn.send((
                    "ERROR",
                    "IsolationBoundaryError",
                    f"target method is unavailable: {method_name}",
                ))
                continue
            try:
                result = method(*args, **kwargs)
                _assert_picklable(result, label="child result")
            except BaseException as exc:
                conn.send(("ERROR",) + _sanitized_error(exc))
            else:
                conn.send(("RESULT", result))
    except EOFError:
        return
    except BaseException as exc:
        try:
            conn.send(("FATAL",) + _sanitized_error(exc))
        except BaseException:
            pass
    finally:
        try:
            if target is not None:
                closer = getattr(target, "close", None)
                if callable(closer):
                    closer()
        finally:
            conn.close()


class IsolatedObjectProxy:
    """Own an object in a spawned child process and expose explicit method calls.

    The ``spawn`` context is deliberate: no patched/imported parent state is inherited
    into the child. This class is a concurrency-isolation primitive only; it is not a
    hostile-code sandbox and does not claim OS privilege separation.
    """

    def __init__(
        self,
        module_name: str,
        qualname: str,
        *init_args: Any,
        timeout_seconds: float = 10.0,
        **init_kwargs: Any,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not isinstance(module_name, str) or not module_name:
            raise IsolationBoundaryError("module_name must be a non-empty string")
        if not isinstance(qualname, str) or not qualname or "<locals>" in qualname:
            raise IsolationBoundaryError("qualname must identify an importable top-level symbol")
        _assert_picklable(
            (module_name, qualname, tuple(init_args), dict(init_kwargs)),
            label="child construction payload",
        )
        self._timeout = float(timeout_seconds)
        self._ctx = mp.get_context("spawn")
        parent, child = self._ctx.Pipe(duplex=True)
        self._conn = parent
        self._process = self._ctx.Process(
            target=_worker_main,
            args=(
                child,
                os.getpid(),
                module_name,
                qualname,
                tuple(init_args),
                dict(init_kwargs),
            ),
            daemon=True,
        )
        self._closed = False
        self._generation = 1
        self._process.start()
        child.close()
        message = self._recv("child startup")
        if message[0] != "READY" or len(message) != 4:
            self._abort()
            self._raise_message(message, expected="READY")
        child_pid = int(message[1])
        worker_nonce_root = str(message[2])
        factory_root = str(message[3])
        expected_factory_root = _factory_identity_root(module_name, qualname)
        if factory_root != expected_factory_root:
            self._abort()
            raise IsolationBoundaryError("child factory identity did not match requested symbol")
        receipt_root = _validate_receipt_fields(
            parent_pid=os.getpid(),
            child_pid=child_pid,
            start_method=self._ctx.get_start_method(),
            generation=self._generation,
            worker_nonce_root=worker_nonce_root,
            factory_identity_root=factory_root,
        )
        self._receipt = IsolationReceipt(
            parent_pid=os.getpid(),
            child_pid=child_pid,
            start_method=self._ctx.get_start_method(),
            generation=self._generation,
            worker_nonce_root=worker_nonce_root,
            factory_identity_root=factory_root,
            receipt_root=receipt_root,
        )

    @property
    def receipt(self) -> IsolationReceipt:
        return self._receipt

    def _recv(self, phase: str) -> tuple[Any, ...]:
        if not self._conn.poll(self._timeout):
            self._abort()
            raise IsolationBoundaryError(f"timeout waiting for {phase}")
        try:
            message = self._conn.recv()
        except (EOFError, OSError) as exc:
            self._abort()
            raise IsolationBoundaryError(f"isolated child exited during {phase}") from exc
        if not isinstance(message, tuple) or not message:
            self._abort()
            raise IsolationBoundaryError(f"malformed response during {phase}")
        return message

    def _raise_message(self, message: tuple[Any, ...], *, expected: str) -> None:
        if message[0] in {"ERROR", "FATAL"} and len(message) == 3:
            raise RemoteInvocationError(str(message[1]), str(message[2]))
        raise IsolationBoundaryError(
            f"unexpected isolated response {message[0]!r}; expected {expected}"
        )

    def call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        if self._closed:
            raise IsolationBoundaryError("isolated object is closed")
        if (
            not isinstance(method_name, str)
            or not method_name
            or method_name.startswith("_")
            or not method_name.isidentifier()
        ):
            raise IsolationBoundaryError("private or malformed method names are not admitted")
        _assert_picklable((method_name, tuple(args), dict(kwargs)), label="child call payload")
        if not self._process.is_alive():
            self._abort()
            raise IsolationBoundaryError("isolated child is not alive")
        try:
            self._conn.send(("CALL", method_name, tuple(args), dict(kwargs)))
        except (EOFError, OSError, BrokenPipeError) as exc:
            self._abort()
            raise IsolationBoundaryError("failed to send request to isolated child") from exc
        message = self._recv(f"call {method_name}")
        if message[0] == "RESULT" and len(message) == 2:
            return message[1]
        self._raise_message(message, expected="RESULT")

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        return self.call("generate", *args, **kwargs)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._process.is_alive():
                try:
                    self._conn.send(("CLOSE",))
                except (EOFError, OSError, BrokenPipeError):
                    self._abort()
                    return
                if self._conn.poll(self._timeout):
                    try:
                        message = self._conn.recv()
                    except (EOFError, OSError):
                        self._abort()
                        return
                    if not (isinstance(message, tuple) and message and message[0] == "CLOSED"):
                        self._abort()
                        return
                else:
                    self._abort()
                    return
                self._process.join(self._timeout)
                if self._process.is_alive():
                    self._abort()
        finally:
            try:
                self._conn.close()
            except OSError:
                pass

    def _abort(self) -> None:
        try:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=1.0)
        finally:
            try:
                self._conn.close()
            except OSError:
                pass
            self._closed = True

    def __enter__(self) -> "IsolatedObjectProxy":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


__all__ = [
    "IsolatedObjectProxy",
    "IsolationBoundaryError",
    "IsolationReceipt",
    "RemoteInvocationError",
]
