from __future__ import annotations
import ctypes, errno, hashlib, json, os, signal, subprocess, sys, time
from dataclasses import dataclass, asdict
from pathlib import Path

PR_SET_CHILD_SUBREAPER = 36

class ContainmentError(RuntimeError):
    pass

@dataclass(frozen=True)
class ProcIdentity:
    pid: int
    starttime: int

@dataclass(frozen=True)
class ContainmentReceipt:
    mode: str
    disposition: str
    subreaper: bool
    pidfd_supported: bool
    pidfd_signals: int
    group_kill_sent: bool
    adopted_seen: int
    identities_seen: int
    killed: int
    reaped: int
    survivors: int
    budget: int
    max_rounds: int
    stable_empty_scans: int
    authority: str = "D0_NONOWNER_CANARY"
    cgroup_direct: str = "UNAVAILABLE_NOT_WRITABLE"

    def semantic_dict(self):
        d = asdict(self)
        # Counts and dispositions are semantic; no PIDs, wall time, or observations timestamps.
        return d

    def root(self) -> str:
        b = json.dumps(self.semantic_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b).hexdigest()


def enable_subreaper() -> None:
    if sys.platform != "linux":
        raise ContainmentError("subreaper requires Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    rc = libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)
    if rc != 0:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))


def proc_identity(pid: int) -> ProcIdentity | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    # comm can contain spaces/parentheses. Split after final ') '. Field 22 is starttime;
    # tail begins at field 3, therefore zero-based tail index 19.
    r = text.rfind(") ")
    if r < 0:
        raise ContainmentError("unparseable /proc stat")
    tail = text[r + 2 :].split()
    return ProcIdentity(pid=pid, starttime=int(tail[19]))


def direct_children() -> list[int]:
    # /proc/<pid>/task/<tid>/children is task-thread scoped and can miss an adopted
    # child even when /proc/<child>/status reports this thread-group PID as PPid.
    # Census /proc by PPid instead. The dedicated canary supervisor owns no unrelated
    # children, so this is both complete for the experiment and bounded by the caller's budget.
    out=[]
    me=os.getpid()
    for ent in Path("/proc").iterdir():
        if not ent.name.isdigit():
            continue
        try:
            status=(ent/"status").read_text()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        ppid=None
        for line in status.splitlines():
            if line.startswith("PPid:"):
                ppid=int(line.split()[1]); break
        if ppid==me:
            out.append(int(ent.name))
    return sorted(out)


def reap_nonblocking() -> int:
    n = 0
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return n
        if pid == 0:
            return n
        n += 1


def pidfd_kill(identity: ProcIdentity) -> tuple[bool, bool]:
    """Return (signalled, used_pidfd). Never signal if identity changed."""
    now = proc_identity(identity.pid)
    if now is None:
        return False, False
    if now.starttime != identity.starttime:
        raise ContainmentError("PID identity changed before signal")
    if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
        try:
            fd = os.pidfd_open(identity.pid, 0)
        except ProcessLookupError:
            return False, False
        try:
            after = proc_identity(identity.pid)
            if after is None:
                return False, True
            if after.starttime != identity.starttime:
                raise ContainmentError("PID identity changed after pidfd_open")
            signal.pidfd_send_signal(fd, signal.SIGKILL, None, 0)
            return True, True
        finally:
            os.close(fd)
    os.kill(identity.pid, signal.SIGKILL)
    return True, False


def read_ready(proc: subprocess.Popen[str], timeout: float = 3.0) -> dict:
    import selectors
    if proc.stdout is None:
        raise ContainmentError("missing worker stdout")
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    events = sel.select(timeout)
    sel.close()
    if not events:
        raise TimeoutError("worker READY timeout")
    line = proc.stdout.readline()
    if not line:
        raise ContainmentError("worker EOF before READY")
    msg = json.loads(line)
    if msg.get("state") != "READY":
        raise ContainmentError("unexpected worker message")
    return msg


def launch_worker(worker: str, mode: str) -> tuple[subprocess.Popen[str], dict]:
    proc = subprocess.Popen(
        [sys.executable, worker, mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
        close_fds=True,
    )
    try:
        ready = read_ready(proc)
        if proc.stdout is not None:
            proc.stdout.close()
    except BaseException:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=2)
        raise
    return proc, ready


def fixed_point_contain(*, worker: str, mode: str, max_descendants: int = 64,
                        deadline: float = 3.0, stable_empty_needed: int = 2) -> ContainmentReceipt:
    if max_descendants <= 0:
        raise ValueError("max_descendants must be positive")
    enable_subreaper()
    proc, ready = launch_worker(worker, mode)
    expected = [ProcIdentity(int(x["pid"]), int(x["starttime"])) for x in ready.get("identities", [])]
    seen: dict[tuple[int,int], ProcIdentity] = {}
    killed = reaped = pidfd_signals = adopted_seen = 0
    group_kill_sent = False
    disposition = "CONTAINED"
    stable = 0
    rounds = 0
    end = time.monotonic() + deadline
    try:
        # Kill original session/process-group first. Escaped sessions survive this by design.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            group_kill_sent = True
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=1.0)
            reaped += 1
        except subprocess.TimeoutExpired:
            pass

        while time.monotonic() < end:
            rounds += 1
            reaped += reap_nonblocking()
            pids = direct_children()
            current: list[ProcIdentity] = []
            for pid in pids:
                ident = proc_identity(pid)
                if ident is not None:
                    current.append(ident)
                    seen[(ident.pid, ident.starttime)] = ident
            adopted_seen = max(adopted_seen, len(current))
            if len(seen) > max_descendants:
                disposition = "HOLD_DESCENDANT_BUDGET"
                break
            if not current:
                stable += 1
                if stable >= stable_empty_needed:
                    break
                time.sleep(0.01)
                continue
            stable = 0
            for ident in current:
                try:
                    sent, used = pidfd_kill(ident)
                    killed += int(sent)
                    pidfd_signals += int(sent and used)
                except PermissionError:
                    disposition = "HOLD_PERMISSION"
                    break
            if disposition != "CONTAINED":
                break
            time.sleep(0.01)
        else:
            disposition = "HOLD_DEADLINE"

        # Identity-specific survivor check for ready-reported escape endpoints.
        survivors = 0
        for ident in expected:
            now = proc_identity(ident.pid)
            if now is not None and now.starttime == ident.starttime:
                survivors += 1
        if disposition == "CONTAINED" and (survivors or direct_children()):
            disposition = "HOLD_DESCENDANTS_REMAIN"

        return ContainmentReceipt(
            mode=mode,
            disposition=disposition,
            subreaper=True,
            pidfd_supported=hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"),
            pidfd_signals=pidfd_signals,
            group_kill_sent=group_kill_sent,
            adopted_seen=adopted_seen,
            identities_seen=len(seen),
            killed=killed,
            reaped=reaped,
            survivors=survivors,
            budget=max_descendants,
            max_rounds=rounds,
            stable_empty_scans=stable,
        )
    finally:
        # Safety cleanup even for HOLD paths. First kill every READY-pinned identity directly;
        # this closes the reparenting-delay window where an escaped endpoint is alive but not yet
        # visible in a PPid census. Then iterate adopted children to a fixed point.
        for ident in expected:
            try: pidfd_kill(ident)
            except (ProcessLookupError, PermissionError, ContainmentError): pass
        for _ in range(256):
            reap_nonblocking()
            ids=[]
            for pid in direct_children():
                ident=proc_identity(pid)
                if ident: ids.append(ident)
            if not ids:
                # Require two empty observations around a scheduler yield before returning.
                time.sleep(0.005)
                reap_nonblocking()
                if not direct_children():
                    break
                continue
            for ident in ids:
                try: pidfd_kill(ident)
                except (ProcessLookupError, PermissionError, ContainmentError): pass
            time.sleep(0.005)
        reap_nonblocking()
        if proc.poll() is None:
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            try: proc.wait(timeout=1)
            except subprocess.TimeoutExpired: pass


def group_only_falsifier(*, worker: str, mode: str = "escaped") -> dict:
    enable_subreaper()
    proc, ready = launch_worker(worker, mode)
    escaped = [ProcIdentity(int(x["pid"]), int(x["starttime"])) for x in ready["identities"]]
    try:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=1)
        # Give orphan reparenting a tiny bounded interval.
        for _ in range(50):
            reap_nonblocking()
            if direct_children(): break
            time.sleep(0.005)
        alive = sum(1 for i in escaped if (x:=proc_identity(i.pid)) is not None and x.starttime == i.starttime)
        adopted = len(direct_children())
        return {"group_only_survivors": alive, "adopted_children": adopted,
                "falsified": alive > 0, "mode": mode}
    finally:
        for ident in escaped:
            try: pidfd_kill(ident)
            except Exception: pass
        for _ in range(128):
            reap_nonblocking()
            ids=[proc_identity(p) for p in direct_children()]
            ids=[x for x in ids if x]
            if not ids:
                time.sleep(0.005); reap_nonblocking()
                if not direct_children(): break
                continue
            for ident in ids:
                try: pidfd_kill(ident)
                except Exception: pass
            time.sleep(0.005)
        reap_nonblocking()
