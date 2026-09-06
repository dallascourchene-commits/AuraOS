"""Verify direct target source bytes before executing a resident isolated target.

The bootstrap is supplied through ``python -I -S -c`` and does not import the target
module to identify it. It opens the final target path once, hashes one stable read, and
compiles/executes those same bytes before constructing the target. Explicit import roots
are added only after the direct-target digest matches. This is a D0 ordering primitive,
not transitive package/runtime/OS/provider attestation.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import pickle
import queue
import re
import secrets
import subprocess
import sys
import threading
from typing import Any

try:
    from .airllm_process_isolation import IsolationBoundaryError, IsolationReceipt, RemoteInvocationError
except ImportError:
    from airllm_process_isolation import IsolationBoundaryError, IsolationReceipt, RemoteInvocationError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
MODE = "subprocess-source-attested-v1"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _pickled(value: Any, label: str) -> str:
    try:
        raw = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    except BaseException as exc:
        raise IsolationBoundaryError(f"{label} is not admitted across trusted IPC") from exc
    return base64.b64encode(raw).decode("ascii")


def _unpickle(value: Any, label: str) -> Any:
    if not isinstance(value, str):
        raise IsolationBoundaryError(f"{label} payload is malformed")
    try:
        return pickle.loads(base64.b64decode(value.encode("ascii"), validate=True))
    except BaseException as exc:
        raise IsolationBoundaryError(f"{label} payload could not be decoded") from exc


def _receipt_root(parent_pid: int, child_pid: int, generation: int, nonce: str, factory_root: str) -> str:
    return _digest({
        "parent_pid": parent_pid,
        "child_pid": child_pid,
        "start_method": MODE,
        "generation": generation,
        "worker_nonce_root": nonce,
        "factory_identity_root": factory_root,
        "authority_ceiling": "D0_PROCESS_ISOLATION_ONLY",
    })


_BOOTSTRAP = r'''
import base64
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import importlib.util
import io
import json
import os
import pickle
import stat
import sys
from types import ModuleType


def emit(value):
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")
    sys.stdout.flush()


def fail(reason, message="", *, observed=None, executed=False):
    out={"kind":"FATAL","reason":reason,"message":str(message)[:1024],"target_executed":bool(executed),"pid":os.getpid()}
    if observed is not None:
        out["observed_source_sha256"]=observed
    emit(out)
    raise SystemExit(0)


def decode(text):
    try:
        return pickle.loads(base64.b64decode(text.encode("ascii"), validate=True))
    except BaseException as exc:
        fail("PAYLOAD_DECODE", type(exc).__name__)


def encode(value):
    return base64.b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)).decode("ascii")


def main():
    try:
        meta=json.loads(sys.argv[1])
    except BaseException as exc:
        fail("META_DECODE", type(exc).__name__)
    required={"module_name","qualname","source_path","expected_source_sha256","import_roots","init_payload_b64"}
    if not isinstance(meta,dict) or set(meta)!=required:
        fail("META_SCHEMA")
    module_name,qualname,path,expected,roots=(meta[k] for k in ("module_name","qualname","source_path","expected_source_sha256","import_roots"))
    if not isinstance(module_name,str) or not module_name:
        fail("MODULE_NAME")
    if not isinstance(qualname,str) or not qualname or "<locals>" in qualname or any((not p) or p.startswith("_") or not p.isidentifier() for p in qualname.split(".")):
        fail("QUALNAME")
    if not isinstance(path,str) or not path or not os.path.isabs(path) or "\x00" in path:
        fail("SOURCE_PATH")
    if not isinstance(expected,str) or len(expected)!=64 or any(c not in "0123456789abcdef" for c in expected):
        fail("SOURCE_SHA")
    if not isinstance(roots,list) or any(not isinstance(x,str) or not os.path.isabs(x) for x in roots):
        fail("IMPORT_ROOTS")

    flags=os.O_RDONLY
    if hasattr(os,"O_CLOEXEC"): flags |= os.O_CLOEXEC
    if hasattr(os,"O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    try:
        fd=os.open(path,flags)
    except OSError as exc:
        fail("SOURCE_OPEN",type(exc).__name__)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): fail("SOURCE_NOT_REGULAR")
        chunks=[]; digest=sha256()
        while True:
            chunk=os.read(fd,1024*1024)
            if not chunk: break
            chunks.append(chunk); digest.update(chunk)
        after=os.fstat(fd)
    finally:
        os.close(fd)
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        fail("SOURCE_CHANGED_DURING_READ")
    observed=digest.hexdigest()
    if observed!=expected:
        fail("SOURCE_DIGEST_MISMATCH",observed=observed,executed=False)
    source_bytes=b"".join(chunks)
    try:
        code=compile(source_bytes,path,"exec",dont_inherit=True)
    except BaseException as exc:
        fail("TARGET_COMPILE",type(exc).__name__,observed=observed,executed=False)
    for root in reversed(roots):
        if root not in sys.path: sys.path.insert(0,root)
    package=module_name.rpartition(".")[0]
    module=ModuleType(module_name)
    module.__file__=path; module.__package__=package
    module.__spec__=importlib.util.spec_from_file_location(module_name,path)
    module.__loader__=None if module.__spec__ is None else module.__spec__.loader
    sys.modules[module_name]=module
    out=io.StringIO(); err=io.StringIO()
    try:
        with redirect_stdout(out),redirect_stderr(err): exec(code,module.__dict__,module.__dict__)
    except BaseException as exc:
        fail("TARGET_EXECUTION",type(exc).__name__,observed=observed,executed=True)
    obj=module
    try:
        for part in qualname.split("."): obj=getattr(obj,part)
    except BaseException as exc:
        fail("FACTORY_RESOLVE",type(exc).__name__,observed=observed,executed=True)
    if not callable(obj): fail("FACTORY_NOT_CALLABLE",observed=observed,executed=True)
    args,kwargs=decode(meta["init_payload_b64"])
    try:
        with redirect_stdout(out),redirect_stderr(err): target=obj(*args,**kwargs)
    except BaseException as exc:
        fail(type(exc).__name__,str(exc),observed=observed,executed=True)
    emit({"kind":"READY","pid":os.getpid(),"observed_source_sha256":observed,"target_executed":True,"worker_nonce_root":sha256(os.urandom(32)).hexdigest()})

    while True:
        line=sys.stdin.readline()
        if not line: return
        try: request=json.loads(line)
        except BaseException:
            emit({"kind":"ERROR","error_type":"IsolationBoundaryError","message":"malformed RPC JSON"}); continue
        if not isinstance(request,dict) or "op" not in request:
            emit({"kind":"ERROR","error_type":"IsolationBoundaryError","message":"malformed RPC envelope"}); continue
        if request["op"]=="CLOSE":
            try:
                closer=getattr(target,"close",None)
                if callable(closer):
                    with redirect_stdout(out),redirect_stderr(err): closer()
            finally:
                emit({"kind":"CLOSED","pid":os.getpid()})
            return
        if request["op"]!="CALL" or set(request)!={"op","method","payload_b64"}:
            emit({"kind":"ERROR","error_type":"IsolationBoundaryError","message":"unknown RPC opcode"}); continue
        method=request["method"]
        if not isinstance(method,str) or not method or method.startswith("_") or not method.isidentifier():
            emit({"kind":"ERROR","error_type":"IsolationBoundaryError","message":"private or malformed method"}); continue
        fn=getattr(target,method,None)
        if not callable(fn):
            emit({"kind":"ERROR","error_type":"IsolationBoundaryError","message":f"target method unavailable: {method}"}); continue
        try:
            args,kwargs=decode(request["payload_b64"])
            with redirect_stdout(out),redirect_stderr(err): result=fn(*args,**kwargs)
            payload=encode(result)
        except BaseException as exc:
            emit({"kind":"ERROR","error_type":type(exc).__name__,"message":str(exc)[:1024]})
        else:
            emit({"kind":"RESULT","payload_b64":payload})

main()
'''.strip()

BOOTSTRAP_SOURCE_SHA256 = sha256(_BOOTSTRAP.encode("utf-8")).hexdigest()


class PreimportSourceObjectProxy:
    def __init__(
        self,
        module_name: str,
        qualname: str,
        source_path: str,
        expected_source_sha256: str,
        *init_args: Any,
        import_roots: tuple[str, ...] | None = None,
        timeout_seconds: float = 10.0,
        **init_kwargs: Any,
    ) -> None:
        if not isinstance(module_name,str) or not module_name:
            raise IsolationBoundaryError("module_name must be non-empty")
        if not isinstance(qualname,str) or not qualname or "<locals>" in qualname or any((not p) or p.startswith("_") or not p.isidentifier() for p in qualname.split(".")):
            raise IsolationBoundaryError("qualname must contain public identifiers")
        if not isinstance(expected_source_sha256,str) or _HEX64.fullmatch(expected_source_sha256) is None:
            raise IsolationBoundaryError("expected source SHA-256 must be exact lowercase 64-hex")
        if not isinstance(timeout_seconds,(int,float)) or isinstance(timeout_seconds,bool) or timeout_seconds<=0:
            raise ValueError("timeout_seconds must be positive")
        path=str(Path(source_path).resolve(strict=True))
        if not Path(path).is_file():
            raise IsolationBoundaryError("source_path must resolve to a regular file")
        roots=[]
        for raw in (() if import_roots is None else import_roots):
            root=str(Path(raw).resolve(strict=True))
            if not Path(root).is_dir(): raise IsolationBoundaryError("import root must be a directory")
            if root not in roots: roots.append(root)
        source_dir=str(Path(path).parent)
        if source_dir not in roots: roots.insert(0,source_dir)
        meta={
            "module_name":module_name,
            "qualname":qualname,
            "source_path":path,
            "expected_source_sha256":expected_source_sha256,
            "import_roots":roots,
            "init_payload_b64":_pickled((tuple(init_args),dict(init_kwargs)),"child construction"),
        }
        self._timeout=float(timeout_seconds); self._closed=False; self._generation=1
        self._queue: queue.Queue=queue.Queue(); self._rpc_lock=threading.Lock(); self._stderr=[]
        self._process=subprocess.Popen(
            [sys.executable,"-I","-S","-u","-c",_BOOTSTRAP,_canonical_json(meta).decode("ascii")],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,
        )
        assert self._process.stdin and self._process.stdout and self._process.stderr
        threading.Thread(target=self._read_stdout,daemon=True).start()
        threading.Thread(target=self._read_stderr,daemon=True).start()
        ready=self._recv("child startup")
        if ready.get("kind")!="READY":
            self._abort(); raise RemoteInvocationError(str(ready.get("reason","IsolationBoundaryError")),str(ready.get("message","pre-import child failed")))
        child_pid=int(ready.get("pid",0)); nonce=ready.get("worker_nonce_root")
        if child_pid<=0 or child_pid==os.getpid(): self._abort(); raise IsolationBoundaryError("pre-import child PID is invalid")
        if ready.get("observed_source_sha256")!=expected_source_sha256 or ready.get("target_executed") is not True:
            self._abort(); raise IsolationBoundaryError("pre-import child did not execute exact requested source")
        if not isinstance(nonce,str) or _HEX64.fullmatch(nonce) is None:
            self._abort(); raise IsolationBoundaryError("pre-import child nonce is invalid")
        factory_root=_digest({"module_name":module_name,"qualname":qualname,"source_path":path,"source_sha256":expected_source_sha256,"bootstrap_source_sha256":BOOTSTRAP_SOURCE_SHA256})
        self._receipt=IsolationReceipt(
            parent_pid=os.getpid(),child_pid=child_pid,start_method=MODE,generation=1,
            worker_nonce_root=nonce,factory_identity_root=factory_root,
            receipt_root=_receipt_root(os.getpid(),child_pid,1,nonce,factory_root),
        )

    @property
    def receipt(self) -> IsolationReceipt:
        return self._receipt

    @property
    def bootstrap_source_sha256(self) -> str:
        return BOOTSTRAP_SOURCE_SHA256

    def _read_stdout(self) -> None:
        try:
            assert self._process.stdout
            for raw in iter(self._process.stdout.readline,b""):
                try:
                    msg=json.loads(raw.decode("ascii"))
                    if not isinstance(msg,dict): raise ValueError
                    self._queue.put(msg)
                except BaseException:
                    self._queue.put(IsolationBoundaryError("pre-import child emitted malformed protocol")); return
        except BaseException as exc:
            self._queue.put(exc)

    def _read_stderr(self) -> None:
        try:
            assert self._process.stderr
            while True:
                chunk=self._process.stderr.read(4096)
                if not chunk: return
                if sum(map(len,self._stderr))<8192: self._stderr.append(chunk[:8192])
        except BaseException:
            return

    def _recv(self,phase:str)->dict[str,Any]:
        try: item=self._queue.get(timeout=self._timeout)
        except queue.Empty as exc:
            self._abort(); raise IsolationBoundaryError(f"timeout waiting for {phase}; pre-import session poisoned") from exc
        if isinstance(item,BaseException):
            self._abort(); raise IsolationBoundaryError(f"pre-import protocol failed during {phase}") from item
        return item

    def _send(self,payload:dict[str,Any])->None:
        if self._closed or self._process.poll() is not None:
            self._abort(); raise IsolationBoundaryError("pre-import child is not alive")
        try:
            assert self._process.stdin
            self._process.stdin.write(_canonical_json(payload)+b"\n"); self._process.stdin.flush()
        except (BrokenPipeError,OSError) as exc:
            self._abort(); raise IsolationBoundaryError("failed to send pre-import request") from exc

    def call(self,method_name:str,*args:Any,**kwargs:Any)->Any:
        if self._closed: raise IsolationBoundaryError("isolated object is closed")
        if not isinstance(method_name,str) or not method_name or method_name.startswith("_") or not method_name.isidentifier():
            raise IsolationBoundaryError("private or malformed method names are not admitted")
        payload=_pickled((tuple(args),dict(kwargs)),"child call")
        with self._rpc_lock:
            self._send({"op":"CALL","method":method_name,"payload_b64":payload}); msg=self._recv(f"call {method_name}")
        if msg.get("kind")=="RESULT": return _unpickle(msg.get("payload_b64"),"child result")
        if msg.get("kind")=="ERROR": raise RemoteInvocationError(str(msg.get("error_type","IsolationBoundaryError")),str(msg.get("message","child call failed")))
        self._abort(); raise IsolationBoundaryError(f"unexpected pre-import response: {msg.get('kind')!r}")

    def generate(self,*args:Any,**kwargs:Any)->Any:
        return self.call("generate",*args,**kwargs)

    def close(self)->None:
        if self._closed: return
        try:
            if self._process.poll() is None:
                self._send({"op":"CLOSE"}); msg=self._recv("child close")
                if msg.get("kind")!="CLOSED": self._abort(); return
                try: self._process.wait(timeout=self._timeout)
                except subprocess.TimeoutExpired: self._abort(); return
        finally:
            self._closed=True
            for name in ("stdin","stdout","stderr"):
                stream=getattr(self._process,name,None)
                try:
                    if stream is not None: stream.close()
                except OSError: pass

    def _abort(self)->None:
        if getattr(self,"_closed",False): return
        self._closed=True
        try:
            if getattr(self,"_process",None) is not None and self._process.poll() is None: self._process.kill()
            if getattr(self,"_process",None) is not None:
                try: self._process.wait(timeout=1.0)
                except subprocess.TimeoutExpired: pass
        finally:
            for name in ("stdin","stdout","stderr"):
                stream=getattr(getattr(self,"_process",None),name,None)
                try:
                    if stream is not None: stream.close()
                except OSError: pass

    def __enter__(self)->"PreimportSourceObjectProxy": return self
    def __exit__(self,exc_type:Any,exc:Any,tb:Any)->None: self.close()


__all__=["BOOTSTRAP_SOURCE_SHA256","MODE","PreimportSourceObjectProxy"]
