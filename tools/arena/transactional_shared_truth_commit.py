from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json, sqlite3

SCHEMA = "AURA-O19-TRANSACTIONAL-SHARED-TRUTH-COMMIT-v1"

def digest(x):
    return sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class CommitMode(str, Enum):
    EXACT_PRESTATE = "EXACT_PRESTATE"
    KEY_PRECONDITION = "KEY_PRECONDITION"

class Disposition(str, Enum):
    COMMIT_D0 = "COMMIT_SHARED_TRUTH_D0"
    DEDUP_D0 = "DEDUP_COMMIT_D0"
    PUBLISH_D0 = "PUBLISH_COMMIT_D0"
    HOLD = "HOLD"

@dataclass(frozen=True)
class AttemptAdmission:
    domain: str
    operation_root: str
    attempt_root: str
    source_incarnation_root: str
    workcell_root: str
    lease_root: str
    current: bool = True
    proof_bound: bool = True

@dataclass(frozen=True)
class CommitProposal:
    mode: CommitMode
    operation_root: str
    attempt_root: str
    pre_state_root: str
    writes: tuple[tuple[str, str], ...]
    preconditions: tuple[tuple[str, str], ...] = ()
    resume_root: str | None = None
    def patch_root(self):
        return digest({"mode": self.mode.value, "operation_root": self.operation_root, "pre_state_root": self.pre_state_root,
                       "writes": sorted(self.writes), "preconditions": sorted(self.preconditions), "resume_root": self.resume_root})

@dataclass(frozen=True)
class Decision:
    disposition: Disposition
    reason: str
    commit_root: str | None = None
    commit_receipt_root: str | None = None
    post_state_root: str | None = None
    publication_root: str | None = None
    effect_authority: bool = False
    checkpoint_authority: bool = False
    project_write_authority: bool = False
    gate10: bool = False

def state_root(rows):
    return digest(sorted((str(k), str(v)) for k, v in rows))

def evaluate_admission_lineage(admission: AttemptAdmission, proposal: CommitProposal):
    if type(admission.current) is not bool or type(admission.proof_bound) is not bool:
        return False, "ATTEMPT_ADMISSION_BOOL_INVALID"
    if not admission.current: return False, "ATTEMPT_ADMISSION_STALE"
    if not admission.proof_bound: return False, "ATTEMPT_ADMISSION_NOT_PROOF_BOUND"
    if admission.operation_root != proposal.operation_root or admission.attempt_root != proposal.attempt_root:
        return False, "ATTEMPT_LINEAGE_MISMATCH"
    return True, "OK_D0"

def evaluate_snapshot(admission: AttemptAdmission, proposal: CommitProposal, current: dict[str, str]):
    admitted, admission_reason = evaluate_admission_lineage(admission, proposal)
    if not admitted: return False, admission_reason
    if not proposal.writes or len({k for k, _ in proposal.writes}) != len(proposal.writes):
        return False, "MALFORMED_WRITES"
    current_root = state_root(current.items())
    if proposal.mode == CommitMode.EXACT_PRESTATE:
        if proposal.pre_state_root != current_root: return False, "EXACT_PRESTATE_MOVED"
        if proposal.resume_root != proposal.pre_state_root: return False, "EXACT_RESUME_ROOT_REQUIRED"
    elif proposal.mode == CommitMode.KEY_PRECONDITION:
        expected = dict(proposal.preconditions)
        if set(expected) != {k for k, _ in proposal.writes}: return False, "PRECONDITION_COVERAGE_REQUIRED"
        for key, _ in proposal.writes:
            if current.get(key) != expected[key]: return False, "KEY_PRECONDITION_CONFLICT"
    else:
        return False, "UNKNOWN_MODE"
    return True, "OK_D0"

class SharedTruthStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS truth_state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS commits(
          commit_root TEXT PRIMARY KEY,operation_root TEXT NOT NULL,attempt_root TEXT NOT NULL,mode TEXT NOT NULL,
          pre_state_root TEXT NOT NULL,patch_root TEXT NOT NULL,post_state_root TEXT NOT NULL,commit_receipt_root TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS publications(
          commit_receipt_root TEXT NOT NULL,projection_root TEXT NOT NULL,publication_root TEXT PRIMARY KEY,
          UNIQUE(commit_receipt_root,projection_root));
        """)
        self.db.commit()
    def seed(self, state):
        with self.db:
            self.db.execute("DELETE FROM truth_state")
            self.db.executemany("INSERT INTO truth_state(key,value) VALUES(?,?)", sorted(state.items()))
    def state(self): return dict(self.db.execute("SELECT key,value FROM truth_state ORDER BY key"))
    def state_root(self): return state_root(self.state().items())
    def commit(self, admission: AttemptAdmission, proposal: CommitProposal):
        admitted, admission_reason = evaluate_admission_lineage(admission, proposal)
        if not admitted: return Decision(Disposition.HOLD, admission_reason)
        patch_root = proposal.patch_root()
        commit_root = digest({"schema": SCHEMA, "operation_root": proposal.operation_root, "patch_root": patch_root})
        prior = self.db.execute("SELECT commit_receipt_root,post_state_root FROM commits WHERE commit_root=?", (commit_root,)).fetchone()
        if prior:
            return Decision(Disposition.DEDUP_D0, "IDENTICAL_COMMIT_ALREADY_DURABLE", commit_root, prior[0], prior[1])
        current = self.state(); ok, reason = evaluate_snapshot(admission, proposal, current)
        if not ok: return Decision(Disposition.HOLD, reason)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            prior_locked = self.db.execute("SELECT commit_receipt_root,post_state_root FROM commits WHERE commit_root=?", (commit_root,)).fetchone()
            if prior_locked:
                return Decision(Disposition.DEDUP_D0, "IDENTICAL_COMMIT_ALREADY_DURABLE", commit_root, prior_locked[0], prior_locked[1])
            live = self.state(); ok2, reason2 = evaluate_snapshot(admission, proposal, live)
            if not ok2: return Decision(Disposition.HOLD, reason2)
            post = dict(live)
            for key, value in proposal.writes: post[key] = value
            post_root = state_root(post.items())
            receipt = digest({"schema": SCHEMA, "commit_root": commit_root, "operation_root": proposal.operation_root,
                              "attempt_root": proposal.attempt_root, "patch_root": patch_root, "post_state_root": post_root,
                              "admission": {"domain": admission.domain, "source_incarnation_root": admission.source_incarnation_root,
                                            "workcell_root": admission.workcell_root, "lease_root": admission.lease_root}})
            for key, value in proposal.writes:
                self.db.execute("INSERT INTO truth_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            self.db.execute("INSERT INTO commits VALUES(?,?,?,?,?,?,?,?)",
                            (commit_root, proposal.operation_root, proposal.attempt_root, proposal.mode.value,
                             proposal.pre_state_root, patch_root, post_root, receipt))
        return Decision(Disposition.COMMIT_D0, "COMMITTED_D0", commit_root, receipt, post_root)
    def publish(self, commit_receipt_root: str, projection_root: str):
        exists = self.db.execute("SELECT 1 FROM commits WHERE commit_receipt_root=?", (commit_receipt_root,)).fetchone()
        if not exists: return Decision(Disposition.HOLD, "COMMIT_RECEIPT_REQUIRED")
        publication_root = digest({"schema": SCHEMA, "commit_receipt_root": commit_receipt_root, "projection_root": projection_root})
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO publications VALUES(?,?,?)", (commit_receipt_root, projection_root, publication_root))
        return Decision(Disposition.PUBLISH_D0, "PUBLISHED_D0", commit_receipt_root=commit_receipt_root, publication_root=publication_root)
