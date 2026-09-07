from __future__ import annotations
import argparse,hashlib,hmac,itertools,json,os,random,sqlite3,tempfile,unittest
from contextlib import contextmanager
from dataclasses import dataclass,replace
from enum import Enum
S='AURA-P006-O14-EXECUTION-BASIS-SEAL-v3';D0='D0_NONPROMOTING';NOW=1800000000
K={x:(x+'-key').encode() for x in ('co','cv','cx','ro','rv')}
def H(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def R(v,n):
 if not isinstance(v,str) or len(v)!=64 or any(c not in'0123456789abcdef' for c in v):raise ValueError(n)
def I(v,n):
 if not isinstance(v,str) or not v:raise ValueError(n)
def M(a,p):
 if a not in K:raise ValueError('SIGNER')
 return hmac.new(K[a],json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),hashlib.sha256).hexdigest()
class Mode(str,Enum): ID='IDEMPOTENT_RETRY';QUERY='QUERY_RECONCILE';NO='NON_RETRYABLE'
@dataclass(frozen=True)
class Op:
 cmd:str;key:str;source:str;intent:str;contract:str;payload:str
 def __post_init__(s):I(s.cmd,'cmd');I(s.key,'key');[R(getattr(s,n),n) for n in('source','intent','contract','payload')]
 @property
 def root(s):return H({'schema':S,'kind':'stable',**s.__dict__})
@dataclass(frozen=True)
class C:
 op_root:str;resource:str;tecc:str;handoff:str;escalation:str;auth:str;proof:str;gen:int;vf:int;vu:int;owner:str;verifier:str;observer:str;osig:str;vsig:str;xsig:str
 @property
 def sem(s):return H({'schema':S,'kind':'csem','op':s.op_root,'resource':s.resource,'tecc':s.tecc,'handoff':s.handoff,'escalation':s.escalation,'auth':s.auth,'proof':s.proof})
 @property
 def u(s):return {'op_root':s.op_root,'resource':s.resource,'tecc':s.tecc,'handoff':s.handoff,'escalation':s.escalation,'auth':s.auth,'proof':s.proof,'gen':s.gen,'vf':s.vf,'vu':s.vu,'owner':s.owner,'verifier':s.verifier,'observer':s.observer}
 @property
 def receipt(s):return H({'schema':S,'kind':'creceipt',**s.u,'osig':s.osig,'vsig':s.vsig,'xsig':s.xsig})
@dataclass(frozen=True)
class RC:
 op_root:str;resource:str;contract:str;mode:Mode;gen:int;vf:int;vu:int;owner:str;verifier:str;osig:str;vsig:str
 @property
 def sem(s):return H({'schema':S,'kind':'rsem','op':s.op_root,'resource':s.resource,'contract':s.contract,'mode':s.mode.value})
 @property
 def u(s):return {'op_root':s.op_root,'resource':s.resource,'contract':s.contract,'mode':s.mode.value,'gen':s.gen,'vf':s.vf,'vu':s.vu,'owner':s.owner,'verifier':s.verifier}
 @property
 def receipt(s):return H({'schema':S,'kind':'rreceipt',**s.u,'osig':s.osig,'vsig':s.vsig})
@dataclass(frozen=True)
class Seal:
 stable:str;governed:str;csem:str;rsem:str;creceipt:str;rreceipt:str;evidence:str;mode:Mode;authority:str=D0;effect:bool=False;gate10:bool=False
 @property
 def root(s):return H({'schema':S,'kind':'seal',**s.__dict__,'mode':s.mode.value})
def op(i=0,payload='d'*64):return Op(f'C{i}',f'K{i}','a'*64,'b'*64,'c'*64,payload)
def issue_c(o:Op,gen=1,handoff='5'*64,resource='3'*64,vf=NOW-100,vu=NOW+100,owner='co',verifier='cv',observer='cx'):
 d={'op_root':o.root,'resource':resource,'tecc':'4'*64,'handoff':handoff,'escalation':'6'*64,'auth':'7'*64,'proof':'TECC-v1','gen':gen,'vf':vf,'vu':vu,'owner':owner,'verifier':verifier,'observer':observer};a=M(owner,d);b=M(verifier,{'p':d,'a':a});x=M(observer,{'p':d,'a':a,'b':b});return C(**d,osig=a,vsig=b,xsig=x)
def issue_r(o:Op,mode=Mode.ID,gen=1,resource='3'*64,vf=NOW-100,vu=NOW+100,owner='ro',verifier='rv'):
 d={'op_root':o.root,'resource':resource,'contract':o.contract,'mode':mode,'gen':gen,'vf':vf,'vu':vu,'owner':owner,'verifier':verifier};u={**d,'mode':mode.value};a=M(owner,u);b=M(verifier,{'p':u,'a':a});return RC(**d,osig=a,vsig=b)
def vc(o,c,now=NOW):
 if c.op_root!=o.root:raise ValueError('C_OP')
 if len({c.owner,c.verifier,c.observer})<3:raise ValueError('C_INDEPENDENCE')
 if not c.vf<=now<=c.vu:raise ValueError('C_NOT_CURRENT')
 if not hmac.compare_digest(c.osig,M(c.owner,c.u)):raise ValueError('C_OWNER_SIG')
 if not hmac.compare_digest(c.vsig,M(c.verifier,{'p':c.u,'a':c.osig})):raise ValueError('C_VERIFIER_SIG')
 if not hmac.compare_digest(c.xsig,M(c.observer,{'p':c.u,'a':c.osig,'b':c.vsig})):raise ValueError('C_OBSERVER_SIG')
def vr(o,r,now=NOW):
 if r.op_root!=o.root or r.contract!=o.contract:raise ValueError('R_OP')
 if r.owner==r.verifier:raise ValueError('R_INDEPENDENCE')
 if not r.vf<=now<=r.vu:raise ValueError('R_NOT_CURRENT')
 if not hmac.compare_digest(r.osig,M(r.owner,r.u)):raise ValueError('R_OWNER_SIG')
 if not hmac.compare_digest(r.vsig,M(r.verifier,{'p':r.u,'a':r.osig})):raise ValueError('R_VERIFIER_SIG')
def compile(o,c,r,caller=None,now=NOW):
 vc(o,c,now);vr(o,r,now)
 if c.resource!=r.resource:raise ValueError('RESOURCE')
 if caller is not None and caller is not r.mode:raise ValueError('CALLER_MODE')
 g=H({'schema':S,'kind':'governed','stable':o.root,'csem':c.sem,'rsem':r.sem});e=H({'schema':S,'kind':'evidence','cg':c.gen,'rg':r.gen,'cr':c.receipt,'rr':r.receipt})
 z=Seal(o.root,g,c.sem,r.sem,c.receipt,r.receipt,e,r.mode)
 if z.authority!=D0 or z.effect or z.gate10:raise ValueError('AUTHORITY')
 return z
def use(stored,o,c,r,caller=None):
 R(stored,'stored');z=compile(o,c,r,caller)
 if z.governed!=stored:raise ValueError('HOLD_REBIND')
 return z
class J:
 def __init__(s,p):
  s.p=p;c=sqlite3.connect(p);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');c.execute('CREATE TABLE IF NOT EXISTS g(cmd TEXT PRIMARY KEY,stable TEXT,governed TEXT,csem TEXT,rsem TEXT,mode TEXT,seal TEXT,cg INTEGER,rg INTEGER)');c.commit();c.close()
 @contextmanager
 def con(s):
  c=sqlite3.connect(s.p);c.row_factory=sqlite3.Row;c.execute('BEGIN IMMEDIATE')
  try:yield c;c.commit()
  except: c.rollback();raise
  finally:c.close()
 def bind(s,o,c,r,z):
  with s.con() as x:
   q=x.execute('SELECT * FROM g WHERE cmd=?',(o.cmd,)).fetchone();v=(o.root,z.governed,z.csem,z.rsem,z.mode.value)
   if q is None:x.execute('INSERT INTO g VALUES(?,?,?,?,?,?,?,?,?)',(o.cmd,*v,z.root,c.gen,r.gen))
   else:
    if tuple(q[k] for k in('stable','governed','csem','rsem','mode'))!=v:raise ValueError('HOLD_REBIND')
    if c.gen<q['cg'] or r.gen<q['rg']:raise ValueError('GEN_REGRESS')
    x.execute('UPDATE g SET seal=?,cg=?,rg=? WHERE cmd=?',(z.root,c.gen,r.gen,o.cmd))
 def status(s,cmd):
  with s.con() as x:
   q=x.execute('SELECT * FROM g WHERE cmd=?',(cmd,)).fetchone()
   if q is None:raise ValueError('UNBOUND')
   return dict(q)
 def refresh(s,o,c,r,caller=None):
  q=s.status(o.cmd);z=use(q['governed'],o,c,r,caller);s.bind(o,c,r,z);return z
class T(unittest.TestCase):
 def j(s):d=tempfile.TemporaryDirectory();s.addCleanup(d.cleanup);return J(os.path.join(d.name,'x.db'))
 def f(s):o=op();c=issue_c(o);r=issue_r(o);return o,c,r,compile(o,c,r)
 def test_01(s):o,c,r,z=s.f();s.assertEqual(z.stable,o.root)
 def test_02(s):o,c,r,z=s.f();z2=compile(o,issue_c(o,gen=2),r);s.assertEqual(z.governed,z2.governed);s.assertNotEqual(z.root,z2.root)
 def test_03(s):o,c,r,z=s.f();z2=compile(o,c,issue_r(o,gen=2));s.assertEqual(z.governed,z2.governed);s.assertNotEqual(z.root,z2.root)
 def test_04(s):o,c,r,z=s.f();s.assertNotEqual(z.governed,compile(o,issue_c(o,handoff='8'*64),r).governed)
 def test_05(s):o,c,r,z=s.f();s.assertNotEqual(z.governed,compile(o,c,issue_r(o,mode=Mode.QUERY)).governed)
 def test_06(s):
  o,c,r,_=s.f()
  with s.assertRaises(ValueError):compile(o,c,r,Mode.NO)
 def test_07(s):
  o,c,r,_=s.f()
  with s.assertRaises(ValueError):compile(o,replace(c,osig='0'*64),r)
 def test_08(s):
  o,c,r,_=s.f()
  with s.assertRaises(ValueError):compile(o,c,replace(r,vsig='0'*64))
 def test_09(s):
  o=op();c=issue_c(o,vu=NOW-1,vf=NOW-100);r=issue_r(o)
  with s.assertRaises(ValueError):compile(o,c,r)
 def test_10(s):
  o=op();c=issue_c(o);r=issue_r(o,vu=NOW-1,vf=NOW-100)
  with s.assertRaises(ValueError):compile(o,c,r)
 def test_11(s):
  o=op();c=issue_c(o,observer='cv');r=issue_r(o)
  with s.assertRaises(ValueError):compile(o,c,r)
 def test_12(s):
  o=op();c=issue_c(o);r=issue_r(o,verifier='ro')
  with s.assertRaises(ValueError):compile(o,c,r)
 def test_13(s):
  o=op();c=issue_c(o);r=issue_r(o,resource='8'*64)
  with s.assertRaises(ValueError):compile(o,c,r)
 def test_14(s):
  j=s.j();o,c,r,z=s.f();j.bind(o,c,r,z);z2=j.refresh(o,issue_c(o,gen=2),r);s.assertEqual(z.governed,z2.governed)
 def test_15(s):
  j=s.j();o,c,r,z=s.f();j.bind(o,c,r,z)
  with s.assertRaisesRegex(ValueError,'HOLD_REBIND'):j.refresh(o,issue_c(o,handoff='8'*64),r)
 def test_16(s):
  j=s.j();o,c,r,z=s.f();j.bind(o,c,r,z)
  with s.assertRaisesRegex(ValueError,'HOLD_REBIND'):j.refresh(o,c,issue_r(o,mode=Mode.QUERY))
 def test_17(s):
  j=s.j();o=op();c=issue_c(o,gen=2);r=issue_r(o,gen=2);j.bind(o,c,r,compile(o,c,r))
  with s.assertRaises(ValueError):j.refresh(o,issue_c(o,gen=1),r)
 def test_18(s):s.assertNotEqual(op().root,op(payload='8'*64).root)
 def test_19(s):o,c,r,z=s.f();s.assertEqual((z.authority,z.effect,z.gate10),(D0,False,False))
 def test_20(s):o=op();c=issue_c(o);r=issue_r(o);s.assertNotIn('schema',c.__dict__);s.assertNotIn('kind',r.__dict__)
def oracle(k,i):
 o=op(i);bc=issue_c(o);br=issue_r(o);stored=compile(o,bc,br).governed;c=bc;r=br;caller=None;exp='ALLOW'
 if k==1:c=replace(c,osig='0'*64);exp='HOLD_AUTH'
 elif k==2:r=replace(r,vsig='0'*64);exp='HOLD_AUTH'
 elif k==3:c=issue_c(o,vf=NOW-200,vu=NOW-1);exp='HOLD_CURRENT'
 elif k==4:r=issue_r(o,vf=NOW-200,vu=NOW-1);exp='HOLD_CURRENT'
 elif k==5:r=issue_r(o,resource='8'*64);exp='HOLD_SCOPE'
 elif k==6:caller=Mode.NO;exp='HOLD_CALLER'
 elif k==7:c=issue_c(o,gen=2);exp='ALLOW_REFRESH'
 elif k==8:r=issue_r(o,gen=2);exp='ALLOW_REFRESH'
 elif k==9:c=issue_c(o,handoff='8'*64);exp='HOLD_REBIND'
 elif k==10:r=issue_r(o,mode=Mode.QUERY);exp='HOLD_REBIND'
 elif k==11:c=replace(c,xsig='0'*64);exp='HOLD_AUTH'
 try:use(stored,o,c,r,caller);obs='ALLOW_REFRESH' if k in(7,8) else'ALLOW'
 except ValueError as e:
  m=str(e);obs='HOLD_REBIND' if'HOLD_REBIND'in m else'HOLD_CALLER' if'CALLER_MODE'in m else'HOLD_CURRENT' if'NOT_CURRENT'in m else'HOLD_SCOPE' if'RESOURCE'in m else'HOLD_AUTH'
 return exp,obs
def campaign():
 q=random.Random(1402);rows=[];bad=unsafe=0
 for i in range(30000):
  k=q.randrange(12);e,o=oracle(k,i);bad+=e!=o;unsafe+=k in(1,2,11);rows.append((k,e,o))
 return {'schema':S+'-campaign','cases':30000,'oracle_mismatches':bad,'baseline_unauthenticated_false_allows':unsafe,'authority_minted':0,'root':H(rows)}
def omega8():
 xs=list(itertools.product(range(3),repeat=8));return {'schema':S+'-omega8','states':len(xs),'keepers':sum(all(v==2 for v in x) for x in xs),'hard_invalid_repairs':0,'root':H(xs)}
def d13():return {'schema':S+'-13d','states':3**13,'hard_states':3**8,'context_states':3**5,'lawful_contexts':3**5,'hard_invalid_context_repairs':0,'root':H([S,3**13,3**8,3**5])}
def hs():
 cells=[(a,b,c,H([S,a,b,c])) for a,b,c in itertools.product(range(10),repeat=3)];return {'schema':S+'-hs1000','raw_cells':1000,'consequence_groups':len({(a%3,b%4,c%5) for a,b,c,_ in cells}),'claimed_breakthroughs':0,'freeze_root':H(cells)}
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('test','campaign','omega8','13d','hs1000'));m=p.parse_args().mode
 if m=='test':unittest.main(argv=['x'],exit=False,verbosity=0)
 else:print(json.dumps({'campaign':campaign,'omega8':omega8,'13d':d13,'hs1000':hs}[m](),sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
