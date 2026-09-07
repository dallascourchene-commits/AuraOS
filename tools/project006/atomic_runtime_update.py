from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json, os, shutil, sqlite3, tempfile
from pathlib import Path
from typing import Mapping, Optional

HEX=set('0123456789abcdef')
class UpdateError(ValueError): pass
class UpdateState(str,Enum):
    PREPARED='PREPARED'
    BACKUP_DURABLE='BACKUP_DURABLE'
    STAGED='STAGED'
    COMMITTED='COMMITTED'
    ROLLBACK_REQUIRED='ROLLBACK_REQUIRED'
    ACCEPTED='ACCEPTED'
    ROLLED_BACK='ROLLED_BACK'

def _hex64(x): return isinstance(x,str) and len(x)==64 and set(x)<=HEX
def _jroot(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha256_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def safe_relpath(p:str)->str:
    q=Path(p)
    if not p or q.is_absolute() or '..' in q.parts: raise UpdateError('UNSAFE_COMPONENT_PATH')
    s=q.as_posix()
    if s.startswith('/') or s.startswith('\\'): raise UpdateError('UNSAFE_COMPONENT_PATH')
    return s

@dataclass(frozen=True)
class ReleaseManifest:
    release_id:str
    repository:str
    expected_head:str
    canonical_operation_root:str
    components:Mapping[str,str]
    def validate(self):
        if not self.release_id or not self.repository or not self.expected_head: raise UpdateError('RELEASE_IDENTITY_INVALID')
        if not _hex64(self.canonical_operation_root): raise UpdateError('CANONICAL_OPERATION_ROOT_INVALID')
        if not self.components: raise UpdateError('EMPTY_COMPONENT_MANIFEST')
        seen=set()
        for p,h in self.components.items():
            p=safe_relpath(p)
            if p in seen or not _hex64(h): raise UpdateError('COMPONENT_MANIFEST_INVALID')
            seen.add(p)
    @property
    def release_root(self):
        self.validate(); return _jroot({'release_id':self.release_id,'repository':self.repository,'expected_head':self.expected_head,'canonical_operation_root':self.canonical_operation_root,'components':dict(sorted(self.components.items()))})

@dataclass(frozen=True)
class UpdateReceipt:
    tx_id:str
    state:UpdateState
    source_release_root:str
    target_release_root:str
    backup_root:Optional[str]
    staged_root:Optional[str]
    installed_root:Optional[str]
    receipt_root:str

class UpdateJournal:
    def __init__(self,path:str):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.path=path
        c=sqlite3.connect(path)
        try:
            c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
            c.execute('''CREATE TABLE IF NOT EXISTS tx(
              tx_id TEXT PRIMARY KEY, state TEXT NOT NULL, source_release_root TEXT NOT NULL,
              target_release_root TEXT NOT NULL, backup_root TEXT, staged_root TEXT, installed_root TEXT,
              commit_receipt_root TEXT, last_receipt_root TEXT NOT NULL)''')
            c.commit()
        finally: c.close()
    def _read(self,tx_id):
        c=sqlite3.connect(self.path)
        try: return c.execute('SELECT state,source_release_root,target_release_root,backup_root,staged_root,installed_root,commit_receipt_root,last_receipt_root FROM tx WHERE tx_id=?',(tx_id,)).fetchone()
        finally:c.close()
    def _receipt(self,tx_id,row):
        return UpdateReceipt(tx_id,UpdateState(row[0]),row[1],row[2],row[3],row[4],row[5],row[7])
    def prepare(self,tx_id:str,source_release_root:str,target_release_root:str)->UpdateReceipt:
        if not tx_id or not _hex64(source_release_root) or not _hex64(target_release_root): raise UpdateError('PREPARE_INVALID')
        prior=self._read(tx_id)
        if prior:
            if prior[1]!=source_release_root or prior[2]!=target_release_root: raise UpdateError('TX_IDENTITY_CONFLICT')
            return self._receipt(tx_id,prior)
        rr=_jroot({'tx_id':tx_id,'state':UpdateState.PREPARED.value,'source':source_release_root,'target':target_release_root})
        c=sqlite3.connect(self.path)
        try:
            c.execute('INSERT INTO tx VALUES(?,?,?,?,?,?,?,?,?)',(tx_id,UpdateState.PREPARED.value,source_release_root,target_release_root,None,None,None,None,rr)); c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))
    def record_backup(self,tx_id:str,backup_root:str)->UpdateReceipt:
        if not _hex64(backup_root): raise UpdateError('BACKUP_ROOT_INVALID')
        row=self._read(tx_id)
        if not row: raise UpdateError('TX_UNKNOWN')
        if row[0] not in (UpdateState.PREPARED.value,UpdateState.BACKUP_DURABLE.value): raise UpdateError('BACKUP_STATE_INVALID')
        if row[0]==UpdateState.BACKUP_DURABLE.value:
            if row[3]!=backup_root: raise UpdateError('BACKUP_EQUIVOCATION')
            return self._receipt(tx_id,row)
        rr=_jroot({'tx_id':tx_id,'state':UpdateState.BACKUP_DURABLE.value,'source':row[1],'target':row[2],'backup':backup_root})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE tx SET state=?,backup_root=?,last_receipt_root=? WHERE tx_id=?',(UpdateState.BACKUP_DURABLE.value,backup_root,rr,tx_id));c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))
    def record_staged(self,tx_id:str,staged_root:str)->UpdateReceipt:
        if not _hex64(staged_root): raise UpdateError('STAGED_ROOT_INVALID')
        row=self._read(tx_id)
        if not row: raise UpdateError('TX_UNKNOWN')
        if row[0] not in (UpdateState.BACKUP_DURABLE.value,UpdateState.STAGED.value): raise UpdateError('STAGE_STATE_INVALID')
        if staged_root!=row[2]: raise UpdateError('STAGED_BYTES_DO_NOT_MATCH_TARGET')
        if row[0]==UpdateState.STAGED.value: return self._receipt(tx_id,row)
        rr=_jroot({'tx_id':tx_id,'state':UpdateState.STAGED.value,'target':row[2],'staged':staged_root,'backup':row[3]})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE tx SET state=?,staged_root=?,last_receipt_root=? WHERE tx_id=?',(UpdateState.STAGED.value,staged_root,rr,tx_id));c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))
    def commit(self,tx_id:str,installed_root:str)->UpdateReceipt:
        if not _hex64(installed_root): raise UpdateError('INSTALLED_ROOT_INVALID')
        row=self._read(tx_id)
        if not row: raise UpdateError('TX_UNKNOWN')
        if row[0] in (UpdateState.COMMITTED.value,UpdateState.ACCEPTED.value,UpdateState.ROLLBACK_REQUIRED.value):
            if row[5]!=installed_root: raise UpdateError('COMMIT_EQUIVOCATION')
            return self._receipt(tx_id,row)
        if row[0]!=UpdateState.STAGED.value: raise UpdateError('COMMIT_STATE_INVALID')
        if installed_root!=row[2] or row[4]!=row[2]: raise UpdateError('COMMIT_BYTES_NOT_TARGET')
        cr=_jroot({'tx_id':tx_id,'commit':'CANONICAL_INSTALL_COMMIT','source':row[1],'target':row[2],'backup':row[3],'staged':row[4],'installed':installed_root})
        rr=_jroot({'tx_id':tx_id,'state':UpdateState.COMMITTED.value,'commit_receipt_root':cr})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE tx SET state=?,installed_root=?,commit_receipt_root=?,last_receipt_root=? WHERE tx_id=?',(UpdateState.COMMITTED.value,installed_root,cr,rr,tx_id));c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))
    def post_install_attest(self,tx_id:str,*,o20_current_exact:bool,o19_physical_wake_accepted:bool)->UpdateReceipt:
        row=self._read(tx_id)
        if not row: raise UpdateError('TX_UNKNOWN')
        if row[0]==UpdateState.ACCEPTED.value: return self._receipt(tx_id,row)
        if row[0] not in (UpdateState.COMMITTED.value,UpdateState.ROLLBACK_REQUIRED.value): raise UpdateError('ATTEST_STATE_INVALID')
        target_state=UpdateState.ACCEPTED if (o20_current_exact and o19_physical_wake_accepted) else UpdateState.ROLLBACK_REQUIRED
        rr=_jroot({'tx_id':tx_id,'state':target_state.value,'o20_current_exact':bool(o20_current_exact),'o19_physical_wake_accepted':bool(o19_physical_wake_accepted),'commit_receipt_root':row[6]})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE tx SET state=?,last_receipt_root=? WHERE tx_id=?',(target_state.value,rr,tx_id));c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))
    def rollback(self,tx_id:str,restored_root:str)->UpdateReceipt:
        row=self._read(tx_id)
        if not row: raise UpdateError('TX_UNKNOWN')
        if row[0]==UpdateState.ROLLED_BACK.value:
            if row[5]!=restored_root: raise UpdateError('ROLLBACK_EQUIVOCATION')
            return self._receipt(tx_id,row)
        if row[0]!=UpdateState.ROLLBACK_REQUIRED.value: raise UpdateError('ROLLBACK_STATE_INVALID')
        if restored_root!=row[1] or restored_root!=row[3]: raise UpdateError('ROLLBACK_BYTES_NOT_SOURCE_BACKUP')
        rr=_jroot({'tx_id':tx_id,'state':UpdateState.ROLLED_BACK.value,'restored_root':restored_root,'commit_receipt_root':row[6]})
        c=sqlite3.connect(self.path)
        try:c.execute('UPDATE tx SET state=?,installed_root=?,last_receipt_root=? WHERE tx_id=?',(UpdateState.ROLLED_BACK.value,restored_root,rr,tx_id));c.commit()
        finally:c.close()
        return self._receipt(tx_id,self._read(tx_id))

def tree_root(root:Path, expected_paths:Optional[set[str]]=None)->str:
    entries=[]
    if not root.exists(): raise UpdateError('TREE_MISSING')
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        rel=safe_relpath(p.relative_to(root).as_posix()); entries.append((rel,sha256_bytes(p.read_bytes())))
    if expected_paths is not None and {p for p,_ in entries}!=set(expected_paths): raise UpdateError('TREE_PATH_SET_MISMATCH')
    return _jroot(entries)

def materialize_release(stage_dir:Path, payloads:Mapping[str,bytes], manifest:ReleaseManifest)->str:
    manifest.validate(); stage_dir.mkdir(parents=True,exist_ok=True)
    if set(payloads)!=set(manifest.components): raise UpdateError('PAYLOAD_SET_MISMATCH')
    for rel,data in payloads.items():
        rel=safe_relpath(rel)
        if sha256_bytes(data)!=manifest.components[rel]: raise UpdateError('PAYLOAD_HASH_MISMATCH')
        dst=stage_dir/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(data)
    tree_root(stage_dir,set(manifest.components))
    return manifest.release_root
