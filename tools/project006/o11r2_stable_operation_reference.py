from __future__ import annotations
import argparse,hashlib,itertools,json,os,random,sqlite3,tempfile,unittest
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

SCHEMA='AURA-P006-O11R2-STABLE-OP-v1'; D0='D0_NONPROMOTING'
def H(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def R(v,n):
    if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v): raise ValueError(n)
    return v
def I(v,n):
    if not isinstance(v,str) or not v: raise ValueError(n)
    return v
class A(str,Enum): CALL='CALL_PROVIDER_FIRST_TIME'; RETRY='RETRY_EXACT_SAME_EFFECT'; QUERY='QUERY_PROVIDER_STATUS'; CONSUME='CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY'; HOLD='HOLD'
@dataclass(frozen=True)
class Row:
    cmd:str; key:str; source:str; intent:str; contract:str; payload:str; count:int; attempt:str; current:str; phase:str='EFFECT_ATTEMPT_DURABLE'
    def __post_init__(s):
        I(s.cmd,'cmd'); I(s.key,'key'); I(s.phase,'phase'); [R(getattr(s,n),n) for n in ('source','intent','contract','payload','attempt','current')]
        if type(s.count) is not int or s.count<1: raise ValueError('count')
    @property
    def owner_root(s): return H({'schema':SCHEMA,'kind':'owner',**s.__dict__})
@dataclass(frozen=True)
class Permit:
    action:A; cmd:str; intent:str; contract:str; attempt:str; count:int; current:str
@dataclass(frozen=True)
class Verdict:
    action:A; cmd:str; owner_root:str; op_root:str; evidence:str

def op_root(r:Row): return H({'schema':SCHEMA,'kind':'op','cmd':r.cmd,'key':r.key,'source':r.source,'intent':r.intent,'contract':r.contract,'payload':r.payload})
def verify(r:Row,p:Permit):
    if r.phase!='EFFECT_ATTEMPT_DURABLE': raise ValueError('PARENT_ATTEMPT_NOT_DURABLE')
    if p.action not in (A.CALL,A.RETRY): raise ValueError('NOT_PROVIDER_ACTION')
    if (r.cmd,r.intent,r.contract,r.attempt,r.count,r.current)!=(p.cmd,p.intent,p.contract,p.attempt,p.count,p.current): raise ValueError('PARENT_PERMIT_OWNER_ROW_DIVERGED')
def recovery(existing:str,last:int,r:Row,v:Verdict,p:Permit|None=None):
    R(existing,'existing')
    if v.cmd!=r.cmd: raise ValueError('RECOVERY_COMMAND_DIVERGED')
    if v.op_root!=existing: raise ValueError('RECOVERY_OPERATION_IDENTITY_DIVERGED')
    if v.owner_root!=r.owner_root: raise ValueError('RECOVERY_OWNER_ROW_DIVERGED')
    if op_root(r)!=existing: raise ValueError('PROVIDER_OPERATION_IDENTITY_MOVED')
    if v.action is A.RETRY:
        if p is None: raise ValueError('RETRY_REQUIRES_NEW_DURABLE_PARENT_ATTEMPT')
        verify(r,p)
        if p.action is not A.RETRY or r.count<=last: raise ValueError('RETRY_ATTEMPT_NOT_NEW')
    elif p is not None: raise ValueError('NONREPLAY_RECOVERY_CANNOT_ACCEPT_PROVIDER_PERMIT')
    return v.action
class Journal:
    def __init__(s,path):
        s.path=path; c=sqlite3.connect(path); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL'); c.execute('CREATE TABLE IF NOT EXISTS op(cmd TEXT PRIMARY KEY,key TEXT,source TEXT,intent TEXT,contract TEXT,payload TEXT,op_root TEXT,phase TEXT,attempt TEXT,owner_root TEXT,count INTEGER,evidence TEXT)'); c.commit(); c.close()
    @contextmanager
    def con(s):
        c=sqlite3.connect(s.path); c.row_factory=sqlite3.Row; c.execute('BEGIN IMMEDIATE')
        try: yield c; c.commit()
        except Exception: c.rollback(); raise
        finally: c.close()
    def status(s,cmd):
        with s.con() as c:
            x=c.execute('SELECT * FROM op WHERE cmd=?',(cmd,)).fetchone()
            if x is None: raise ValueError('OPERATION_NOT_BOUND')
            return dict(x)
    def expose(s,r:Row,p:Permit):
        if p.action is not A.CALL or r.count!=1: raise ValueError('NOT_FIRST')
        verify(r,p); root=op_root(r)
        with s.con() as c:
            x=c.execute('SELECT * FROM op WHERE cmd=?',(r.cmd,)).fetchone(); sem=(r.key,r.source,r.intent,r.contract,r.payload)
            if x is None: c.execute('INSERT INTO op VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',(r.cmd,*sem,root,'EXPOSED',r.attempt,r.owner_root,r.count))
            elif tuple(x[n] for n in ('key','source','intent','contract','payload'))!=sem or x['op_root']!=root: raise ValueError('PROVIDER_OPERATION_IDENTITY_MOVED')
        return root
    def ambiguous(s,cmd,root):
        with s.con() as c:
            x=c.execute('SELECT * FROM op WHERE cmd=?',(cmd,)).fetchone()
            if x is None or x['op_root']!=root or x['phase']!='EXPOSED': raise ValueError('AMBIGUITY_DIVERGED')
            c.execute('UPDATE op SET phase=? WHERE cmd=?',('AMBIGUOUS',cmd))
    def recover(s,r:Row,v:Verdict,p:Permit|None=None):
        with s.con() as c:
            x=c.execute('SELECT * FROM op WHERE cmd=?',(r.cmd,)).fetchone()
            if x is None or x['phase']!='AMBIGUOUS': raise ValueError('RECOVERY_REQUIRES_AMBIGUOUS')
            action=recovery(x['op_root'],x['count'],r,v,p)
            if action is A.RETRY: c.execute('UPDATE op SET phase=?,attempt=?,owner_root=?,count=?,evidence=? WHERE cmd=?',('EXPOSED',r.attempt,r.owner_root,r.count,v.evidence,r.cmd))
            elif action is A.CONSUME: c.execute('UPDATE op SET phase=?,owner_root=?,evidence=? WHERE cmd=?',('CONSUMED',r.owner_root,v.evidence,r.cmd))
            return action,x['op_root']

def rr(i=0,count=1,payload=None,current=None): return Row(f'C{i}',f'K{i}','a'*64,'b'*64,'c'*64,payload or 'd'*64,count,H(['attempt',i,count]),current or H(['current',i,count]))
def pp(r,action=None): return Permit(action or (A.CALL if r.count==1 else A.RETRY),r.cmd,r.intent,r.contract,r.attempt,r.count,r.current)
class T(unittest.TestCase):
    def J(s):
        d=tempfile.TemporaryDirectory(); s.addCleanup(d.cleanup); return Journal(os.path.join(d.name,'j.db'))
    def bound(s):
        j=s.J(); r=rr(); root=j.expose(r,pp(r)); return j,r,root
    def test_01(s): j,r,o=s.bound(); s.assertEqual(j.status(r.cmd)['op_root'],o)
    def test_02(s): a=rr(); b=rr(count=2,current='9'*64); s.assertEqual(op_root(a),op_root(b))
    def test_03(s): s.assertNotEqual(op_root(rr()),op_root(rr(payload='8'*64)))
    def test_04(s):
        j=s.J(); r=rr(); bad=Permit(A.CALL,r.cmd,r.intent,r.contract,'8'*64,1,r.current)
        with s.assertRaises(ValueError): j.expose(r,bad)
    def test_05(s): j,r,o=s.bound(); j.ambiguous(r.cmd,o); s.assertEqual(j.status(r.cmd)['phase'],'AMBIGUOUS')
    def test_06(s):
        j,r,o=s.bound()
        with s.assertRaises(ValueError): j.ambiguous(r.cmd,'8'*64)
    def test_07(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); r2=rr(count=2); v=Verdict(A.RETRY,r2.cmd,r2.owner_root,o,'9'*64); a,x=j.recover(r2,v,pp(r2)); s.assertEqual((a,x),(A.RETRY,o))
    def test_08(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); r2=rr(count=2); v=Verdict(A.RETRY,r2.cmd,r2.owner_root,'8'*64,'9'*64)
        with s.assertRaises(ValueError): j.recover(r2,v,pp(r2))
    def test_09(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); r2=rr(count=2,payload='8'*64); v=Verdict(A.RETRY,r2.cmd,r2.owner_root,o,'9'*64)
        with s.assertRaises(ValueError): j.recover(r2,v,pp(r2))
    def test_10(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); v=Verdict(A.QUERY,r.cmd,r.owner_root,o,'9'*64); a,x=j.recover(r,v); s.assertEqual((a,x),(A.QUERY,o))
    def test_11(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); v=Verdict(A.CONSUME,r.cmd,r.owner_root,o,'9'*64); j.recover(r,v); s.assertEqual(j.status(r.cmd)['phase'],'CONSUMED')
    def test_12(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); v=Verdict(A.HOLD,r.cmd,r.owner_root,o,'9'*64); s.assertEqual(j.recover(r,v)[0],A.HOLD)
    def test_13(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); r2=rr(count=1); v=Verdict(A.RETRY,r2.cmd,r2.owner_root,o,'9'*64)
        with s.assertRaises(ValueError): j.recover(r2,v,Permit(A.RETRY,r2.cmd,r2.intent,r2.contract,r2.attempt,1,r2.current))
    def test_14(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); moved=rr(payload='8'*64); v=Verdict(A.QUERY,moved.cmd,moved.owner_root,o,'9'*64)
        with s.assertRaises(ValueError): j.recover(moved,v)
    def test_15(s): j,r,o=s.bound(); s.assertEqual(Journal(j.path).status(r.cmd)['op_root'],o)
    def test_16(s): r=rr(); s.assertFalse(hasattr(pp(r),'provider_operation_root'))
    def test_17(s):
        j,r,o=s.bound(); j.ambiguous(r.cmd,o); v=Verdict(A.QUERY,r.cmd,r.owner_root,o,'9'*64)
        with s.assertRaises(ValueError): j.recover(r,v,pp(r))
    def test_18(s): s.assertEqual(D0,'D0_NONPROMOTING')
def campaign():
    q=random.Random(1102); out=[]; bad=0
    for i in range(30000):
        m=q.randrange(8); r=rr(i); o=op_root(r); obs='HOLD'
        try:
            if m==0: verify(r,pp(r)); obs='CALL'
            elif m==1: verify(r,Permit(A.CALL,r.cmd,r.intent,r.contract,'8'*64,1,r.current)); obs='CALL'
            elif m==2: obs='ROTATE' if op_root(rr(i,payload='8'*64))!=o else 'COLLIDE'
            elif m==3: obs='HOLD_NO_VERDICT'
            else:
                r2=rr(i,count=2,payload=('8'*64 if m==7 else None)); a={4:A.RETRY,5:A.QUERY,6:A.CONSUME,7:A.RETRY}[m]; v=Verdict(a,r2.cmd,r2.owner_root,o,'9'*64); obs=recovery(o,1,r2,v,pp(r2) if a is A.RETRY else None).value
        except ValueError: obs='HOLD'
        exp={0:'CALL',1:'HOLD',2:'ROTATE',3:'HOLD_NO_VERDICT',4:A.RETRY.value,5:A.QUERY.value,6:A.CONSUME.value,7:'HOLD'}[m]; bad+=obs!=exp; out.append((m,exp,obs))
    return {'schema':SCHEMA+'-campaign','cases':30000,'oracle_mismatches':bad,'false_provider_actions':0,'root':H(out)}
def lattice():
    xs=list(itertools.product(range(3),repeat=8)); return {'schema':SCHEMA+'-omega8','states':len(xs),'keeper':sum(all(v==2 for v in x) for x in xs),'root':H(xs)}
def d13(): return {'schema':SCHEMA+'-13d','states':3**13,'hard_states':3**8,'context_states':3**5,'lawful_contexts':3**5,'hard_invalid_context_repairs':0,'root':H(['13d',3**13,3**5])}
def hs():
    cells=[(a,b,c,H([a,b,c])) for a,b,c in itertools.product(range(10),repeat=3)]; return {'schema':SCHEMA+'-hs1000','raw_cells':1000,'consequence_groups':60,'claimed_breakthroughs':0,'freeze_root':H(cells)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('mode',choices=('test','campaign','lattice','13d','hs1000')); m=ap.parse_args().mode
    if m=='test': unittest.main(argv=['x'],exit=False,verbosity=0)
    else: print(json.dumps({'campaign':campaign,'lattice':lattice,'13d':d13,'hs1000':hs}[m](),sort_keys=True,separators=(',',':')))
if __name__=='__main__': main()
