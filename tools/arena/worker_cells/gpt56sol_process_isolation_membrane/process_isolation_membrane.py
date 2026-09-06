from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
import importlib
import importlib.util
import json
import multiprocessing
import os
import pickle
from pathlib import Path
import re
import secrets
import sys
from types import ModuleType
from typing import Any, Iterable

HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WORKER_CONTEXT: ContextVar[tuple[int, str] | None] = ContextVar("aura_isolated_worker", default=None)


class IsolationContractError(RuntimeError):
    pass


class ProcessIsolationRequiredError(IsolationContractError):
    pass


class WorkerProtocolError(IsolationContractError):
    pass


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return sha256(raw.encode()).hexdigest()


def _strict_text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise IsolationContractError(f"INVALID_TEXT:{name}")
    return value


def _sha256_file(path: str) -> str:
    try:
        resolved = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise WorkerProtocolError("FACTORY_ORIGIN") from exc
    if not resolved.is_file():
        raise WorkerProtocolError("FACTORY_ORIGIN")
    h = sha256()
    try:
        with resolved.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise WorkerProtocolError("FACTORY_SOURCE_READ") from exc
    return h.hexdigest()


def _split_factory_spec(spec: str) -> tuple[str, str]:
    spec = _strict_text(spec, "factory_spec")
    if ":" not in spec:
        raise WorkerProtocolError("SPEC_FORMAT")
    module_name, qualname = spec.split(":", 1)
    if not module_name or not qualname:
        raise WorkerProtocolError("SPEC_FORMAT")
    for part in qualname.split("."):
        if not part or part.startswith("_") or not part.isidentifier():
            raise WorkerProtocolError("PRIVATE_SPEC")
    return module_name, qualname


@dataclass(frozen=True)
class FactoryIdentity:
    factory_spec: str
    module_name: str
    qualname: str
    module_bytes_root: str
    identity_root: str

    @classmethod
    def mint(cls, *, factory_spec: str, module_bytes_root: str) -> "FactoryIdentity":
        module_name, qualname = _split_factory_spec(factory_spec)
        if type(module_bytes_root) is not str or HEX64.fullmatch(module_bytes_root) is None:
            raise WorkerProtocolError("FACTORY_BYTES_ROOT")
        body = {
            "factory_spec": factory_spec,
            "module_name": module_name,
            "qualname": qualname,
            "module_bytes_root": module_bytes_root,
        }
        return cls(factory_spec, module_name, qualname, module_bytes_root, _digest(body))

    def verify(self) -> bool:
        try:
            expected = FactoryIdentity.mint(
                factory_spec=self.factory_spec,
                module_bytes_root=self.module_bytes_root,
            )
        except IsolationContractError:
            return False
        return (
            self.module_name == expected.module_name
            and self.qualname == expected.qualname
            and self.identity_root == expected.identity_root
        )


def factory_identity_currentness(expected: FactoryIdentity, current: FactoryIdentity) -> str:
    if not isinstance(expected, FactoryIdentity) or not isinstance(current, FactoryIdentity):
        return "HOLD"
    if not expected.verify() or not current.verify():
        return "HOLD"
    if expected.factory_spec != current.factory_spec:
        return "HOLD"
    return "EXACT" if expected.identity_root == current.identity_root else "HOLD"


def factory_identity_for_spec(factory_spec: str, *, loaded: bool = False) -> FactoryIdentity:
    """Derive exact module-file identity for a factory without granting source truth.

    Parent preflight uses import metadata; the worker independently recomputes the
    identity from the module it actually imported. Equality proves byte parity for
    this module file only, not package/transitive provenance or provider truth.
    """
    module_name, _ = _split_factory_spec(factory_spec)
    if loaded:
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
    else:
        spec = importlib.util.find_spec(module_name)
        origin = None if spec is None else spec.origin
    if type(origin) is not str or not origin or origin in {"built-in", "frozen"}:
        raise WorkerProtocolError("FACTORY_ORIGIN")
    return FactoryIdentity.mint(
        factory_spec=factory_spec,
        module_bytes_root=_sha256_file(origin),
    )


def registered_module_aliases(module: object) -> tuple[str, ...]:
    return tuple(sorted(name for name, value in sys.modules.items() if value is module))


def patch_isolation_state(module: object) -> str:
    """Return PRIVATE_MODULE, DEDICATED_PROCESS, or HOLD.

    A module object that is not registered in sys.modules is private to the caller's
    object graph and may be patched for synthetic tests without touching global imports.
    Registered modules are process-global and may be patched only inside a worker
    context created by DedicatedProcessService.
    """
    aliases = registered_module_aliases(module)
    if not aliases:
        return "PRIVATE_MODULE"
    marker = _WORKER_CONTEXT.get()
    if marker is None:
        return "HOLD"
    worker_pid, token = marker
    if worker_pid != os.getpid() or not token:
        return "HOLD"
    return "DEDICATED_PROCESS"


def require_patch_isolation(module: object) -> str:
    state = patch_isolation_state(module)
    if state == "HOLD":
        aliases = registered_module_aliases(module)
        raise ProcessIsolationRequiredError(
            "registered process-global module patching requires a DedicatedProcessService "
            f"worker; aliases={aliases!r}"
        )
    return state


@dataclass(frozen=True)
class WorkerReceipt:
    parent_pid: int
    worker_pid: int
    worker_nonce_root: str
    factory_spec: str
    factory_identity_root: str
    factory_module_bytes_root: str
    state: str
    authority_ceiling: str
    receipt_root: str

    @classmethod
    def mint(
        cls,
        *,
        parent_pid: int,
        worker_pid: int,
        worker_nonce_root: str,
        factory_spec: str,
        factory_identity_root: str,
        factory_module_bytes_root: str,
        state: str,
    ) -> "WorkerReceipt":
        if type(parent_pid) is not int or type(worker_pid) is not int:
            raise WorkerProtocolError("PID_TYPE")
        if parent_pid <= 0 or worker_pid <= 0 or parent_pid == worker_pid:
            raise WorkerProtocolError("PID_ISOLATION")
        if type(worker_nonce_root) is not str or HEX64.fullmatch(worker_nonce_root) is None:
            raise WorkerProtocolError("NONCE_ROOT")
        factory_spec = _strict_text(factory_spec, "factory_spec")
        if type(factory_identity_root) is not str or HEX64.fullmatch(factory_identity_root) is None:
            raise WorkerProtocolError("FACTORY_IDENTITY_ROOT")
        if type(factory_module_bytes_root) is not str or HEX64.fullmatch(factory_module_bytes_root) is None:
            raise WorkerProtocolError("FACTORY_BYTES_ROOT")
        state = _strict_text(state, "state")
        body = {
            "parent_pid": parent_pid,
            "worker_pid": worker_pid,
            "worker_nonce_root": worker_nonce_root,
            "factory_spec": factory_spec,
            "factory_identity_root": factory_identity_root,
            "factory_module_bytes_root": factory_module_bytes_root,
            "state": state,
            "authority_ceiling": "D0_PROCESS_ISOLATION_ONLY",
        }
        return cls(
            parent_pid,
            worker_pid,
            worker_nonce_root,
            factory_spec,
            factory_identity_root,
            factory_module_bytes_root,
            state,
            body["authority_ceiling"],
            _digest(body),
        )

    def verify(self) -> bool:
        body = {
            "parent_pid": self.parent_pid,
            "worker_pid": self.worker_pid,
            "worker_nonce_root": self.worker_nonce_root,
            "factory_spec": self.factory_spec,
            "factory_identity_root": self.factory_identity_root,
            "factory_module_bytes_root": self.factory_module_bytes_root,
            "state": self.state,
            "authority_ceiling": self.authority_ceiling,
        }
        return (
            self.authority_ceiling == "D0_PROCESS_ISOLATION_ONLY"
            and type(self.receipt_root) is str
            and HEX64.fullmatch(self.receipt_root) is not None
            and self.receipt_root == _digest(body)
        )


def _resolve_spec(spec: str) -> Any:
    module_name, qualname = _split_factory_spec(spec)
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


@contextmanager
def _dedicated_worker_scope(token: str):
    if type(token) is not str or not token:
        raise WorkerProtocolError("WORKER_TOKEN")
    reset = _WORKER_CONTEXT.set((os.getpid(), token))
    try:
        yield
    finally:
        _WORKER_CONTEXT.reset(reset)


def _worker_main(conn, parent_pid: int, factory_spec: str, expected_factory_identity: FactoryIdentity, init_args: tuple[Any, ...], init_kwargs: dict[str, Any]) -> None:
    token = secrets.token_hex(32)
    nonce_root = sha256(token.encode()).hexdigest()
    try:
        with _dedicated_worker_scope(token):
            factory = _resolve_spec(factory_spec)
            worker_identity = factory_identity_for_spec(factory_spec, loaded=True)
            if factory_identity_currentness(expected_factory_identity, worker_identity) != "EXACT":
                raise WorkerProtocolError("FACTORY_IDENTITY_DRIFT")
            resident = factory(*init_args, **init_kwargs)
            receipt = WorkerReceipt.mint(
                parent_pid=parent_pid,
                worker_pid=os.getpid(),
                worker_nonce_root=nonce_root,
                factory_spec=factory_spec,
                factory_identity_root=worker_identity.identity_root,
                factory_module_bytes_root=worker_identity.module_bytes_root,
                state="READY",
            )
            conn.send(("READY", receipt))
            while True:
                request = conn.recv()
                if not isinstance(request, tuple) or not request:
                    raise WorkerProtocolError("REQUEST_SHAPE")
                op = request[0]
                if op == "CLOSE":
                    conn.send(("CLOSED", None))
                    return
                if op != "CALL" or len(request) != 4:
                    raise WorkerProtocolError("REQUEST_OP")
                _, method_name, args, kwargs = request
                method_name = _strict_text(method_name, "method_name")
                if method_name.startswith("_") or not method_name.isidentifier():
                    raise WorkerProtocolError("PRIVATE_METHOD")
                method = getattr(resident, method_name, None)
                if not callable(method):
                    raise WorkerProtocolError(f"UNKNOWN_METHOD:{method_name}")
                result = method(*args, **kwargs)
                try:
                    pickle.dumps(result)
                except Exception as exc:
                    raise WorkerProtocolError("UNSERIALIZABLE_RESULT") from exc
                conn.send(("OK", result))
    except EOFError:
        return
    except BaseException as exc:
        try:
            conn.send(("ERROR", (type(exc).__name__, str(exc))))
        except BaseException:
            pass
    finally:
        conn.close()


class DedicatedProcessService:
    """Keep state resident in a dedicated spawned process and expose bounded method RPC."""

    def __init__(self, process: multiprocessing.Process, conn: Any, receipt: WorkerReceipt):
        self._process = process
        self._conn = conn
        self.receipt = receipt
        self._closed = False

    @classmethod
    def start(
        cls,
        factory_spec: str,
        *init_args: Any,
        start_method: str = "spawn",
        **init_kwargs: Any,
    ) -> "DedicatedProcessService":
        factory_spec = _strict_text(factory_spec, "factory_spec")
        parent_identity = factory_identity_for_spec(factory_spec, loaded=False)
        try:
            pickle.dumps((factory_spec, init_args, init_kwargs))
        except Exception as exc:
            raise WorkerProtocolError("UNSERIALIZABLE_INIT") from exc
        ctx = multiprocessing.get_context(start_method)
        parent_conn, child_conn = ctx.Pipe(duplex=True)
        proc = ctx.Process(
            target=_worker_main,
            args=(child_conn, os.getpid(), factory_spec, parent_identity, init_args, init_kwargs),
            daemon=True,
        )
        proc.start()
        child_conn.close()
        try:
            if not parent_conn.poll(10):
                proc.terminate()
                proc.join(timeout=2)
                raise WorkerProtocolError("WORKER_START_TIMEOUT")
            status, payload = parent_conn.recv()
        except BaseException:
            parent_conn.close()
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=2)
            raise
        if status != "READY" or not isinstance(payload, WorkerReceipt):
            parent_conn.close()
            if proc.is_alive():
                proc.terminate()
            proc.join(timeout=2)
            raise WorkerProtocolError(f"WORKER_START_FAILED:{payload!r}")
        if payload.worker_pid != proc.pid or payload.parent_pid != os.getpid():
            parent_conn.close()
            proc.terminate()
            proc.join(timeout=2)
            raise WorkerProtocolError("WORKER_RECEIPT_PID_MISMATCH")
        if (
            not payload.verify()
            or payload.factory_spec != factory_spec
            or payload.factory_identity_root != parent_identity.identity_root
            or payload.factory_module_bytes_root != parent_identity.module_bytes_root
        ):
            parent_conn.close()
            proc.terminate()
            proc.join(timeout=2)
            raise WorkerProtocolError("WORKER_RECEIPT_FACTORY_MISMATCH")
        return cls(proc, parent_conn, payload)

    @property
    def worker_pid(self) -> int:
        return int(self.receipt.worker_pid)

    def call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        if self._closed:
            raise WorkerProtocolError("SERVICE_CLOSED")
        method_name = _strict_text(method_name, "method_name")
        if method_name.startswith("_") or not method_name.isidentifier():
            raise WorkerProtocolError("PRIVATE_METHOD")
        try:
            pickle.dumps((method_name, args, kwargs))
        except Exception as exc:
            raise WorkerProtocolError("UNSERIALIZABLE_CALL") from exc
        if not self._process.is_alive():
            raise WorkerProtocolError("WORKER_NOT_ALIVE")
        self._conn.send(("CALL", method_name, args, kwargs))
        if not self._conn.poll(30):
            raise WorkerProtocolError("WORKER_CALL_TIMEOUT")
        status, payload = self._conn.recv()
        if status == "OK":
            return payload
        if status == "ERROR":
            name, message = payload
            raise WorkerProtocolError(f"WORKER_ERROR:{name}:{message}")
        raise WorkerProtocolError(f"WORKER_RESPONSE:{status}")

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._process.is_alive():
                try:
                    self._conn.send(("CLOSE",))
                    if self._conn.poll(5):
                        self._conn.recv()
                except (BrokenPipeError, EOFError, OSError):
                    pass
        finally:
            self._closed = True
            try:
                self._conn.close()
            except OSError:
                pass
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=5)

    def __enter__(self) -> "DedicatedProcessService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class IsolationProbe:
    """Stdlib-only resident used to prove registered-module patch ownership."""

    def __init__(self):
        name = f"_aura_isolation_probe_{os.getpid()}"
        self.module = ModuleType(name)
        sys.modules[name] = self.module
        self.name = name
        self.counter = 0

    def isolation_state(self) -> tuple[str, int, tuple[str, ...]]:
        return require_patch_isolation(self.module), os.getpid(), registered_module_aliases(self.module)

    def increment(self, amount: int = 1) -> tuple[int, int]:
        if type(amount) is not int:
            raise WorkerProtocolError("AMOUNT_TYPE")
        self.counter += amount
        return self.counter, os.getpid()

    def parent_independent_marker(self) -> tuple[int, str]:
        setattr(self.module, "worker_only_marker", os.getpid())
        return os.getpid(), _digest((self.name, os.getpid(), self.counter))


def omega8_admit(state: tuple[int, ...]) -> bool:
    return len(state) == 8 and tuple(state) == (2, 2, 2, 2, 2, 2, 2, 1)


def admit13(state: tuple[int, ...]) -> bool:
    return len(state) == 13 and tuple(state) == (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2)
