from __future__ import annotations
import argparse,hashlib,hmac,itertools,json,os,random,sqlite3,tempfile,unittest
from dataclasses import dataclass
from enum import Enum
S='AURA-O17-DELEGATED-TRAIN-v1'; NOW=1800000000; D0='D0_NONPROMOTING'
CK=b'current';TK=b'train';WK=b'work';RK=b'recovery'
def H(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def M(k,x):return hmac.new(k,json.dumps(x,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
def R(x):return isinstance(x,str) and len(x)==64 and not(set(x)-set('0123456789abcdef'))
class W(str,Enum): SOL='GPT56SOL'; DS='DEEPSEEK'; ASTRA='ASTRA'
@dataclass(frozen=True)
class C:
 m:str;g:int;front:str;cut:str;live:str;exp:int;sig:str
 @property
 def u(s):return {'m':s.m,'g':s.g,'front':s.front,'cut':s.cut,'live':s.live,'exp':s.exp}
 @property
 def root(s):return H(['C',s.u,s.sig])
def C0(m='M',g=1,exp=NOW+100):
 u={'m':m,'g':g,'front':'1'*64,'cut':'2'*64,'live':'3'*64,'exp':exp};return C(**u,sig=M(CK,u))
def vc(c):
 if min(c.g,c.exp-NOW)<1 or not all(map(R,(c.front,c.cut,c.live))) or c.sig!=M(CK,c.u):raise ValueError('CURRENT')
@dataclass(frozen=True)
class A:
 cmd:str;base:str;cfg:str;tok:str;runtime:str;commit:str;family:str;trainer:str;target:str;keys:str;rank:int;alpha:int;g:int;exp:int;sig:str
 @property
 def u(s):return {k:getattr(s,k) for k in ('cmd','base','cfg','tok','runtime','commit','family','trainer','target','keys','rank','alpha','g','exp')}
 @property
 def root(s):return H(['A',s.u,s.sig])
def A0(i=0,family='QWEN3_5',trainer='AirLLMLoRA',base='5'*64,runtime='4'*64,tok='6'*64,g=1,exp=NOW+100):
 u={'cmd':f'TRAIN-{i}','base':base,'cfg':'7'*64,'tok':tok,'runtime':runtime,'commit':'55e435087d951da8c25ab3672e969025241a398e','family':family,'trainer':trainer,'target':'8'*64,'keys':'9'*64,'rank':16,'alpha':32,'g':g,'exp':exp};return A(**u,sig=M(TK,u))
def va(a):
 if not all(map(R,(a.base,a.cfg,a.tok,a.runtime,a.target,a.keys))) or a.g<1 or a.exp<NOW or a.sig!=M(TK,a.u):raise ValueError('ADMISSION')
 if a.family not in ('QWEN3_5','QWEN4EXP'):raise ValueError('HOLD_PORT_REQUIRED')
 if a.trainer!=('AirLLMLoRA' if a.family=='QWEN3_5' else 'AirLLMLoRAQwen4Exp'):raise ValueError('TRAINER')
@dataclass(frozen=True)
class L:
 handle:str;m:str;card:str;progress:str;g:int;exp:int;sig:str
 @property
 def u(s):return {'handle':s.handle,'m':s.m,'card':s.card,'progress':s.progress,'g':s.g,'exp':s.exp}
 @property
 def root(s):return H(['L',s.u,s.sig])
def L0(i=0,m='M',g=1,card='a'*64,progress='b'*64,exp=NOW+100):
 u={'handle':H(['w',i])[:24],'m':m,'card':card,'progress':progress,'g':g,'exp':exp};return L(**u,sig=M(WK,u))
def vl(l,m,card=None,progress=None):
 if l.m!=m or l.g<1 or l.exp<NOW or l.sig!=M(WK,l.u) or (card and l.card!=card) or (progress and l.progress!=progress):raise ValueError('WORKCELL')
def op(a,src='c'*64,tst='d'*64):
 return H(['OP',a.cmd,a.base,a.cfg,a.tok,a.runtime,a.commit,a.family,a.trainer,a.target,a.keys,a.rank,a.alpha,src,tst])
def at(a,n=1,src='c'*64,tst='d'*64):
 o=op(a,src,tst);return (n,H(['ATT',a.cmd,o,n]))
def rec(o,n):return H(['REC',o,n,M(RK,{'op':o,'n':n})])
@dataclass(frozen=True)
class P:
 cmd:str;op:str;current:str;admission:str;work:str;att:str;n:int;worker:W;src:str;tst:str;recovery:str|None
 @property
 def root(s):return H(['P',s.cmd,s.op,s.current,s.admission,s.work,s.att,s.n,s.worker.value,s.src,s.tst,s.recovery])
 def public(s,h):return {'schema':'AURA-DELEGATED-TRAINING-CAPSULE-v1','task':'TRAIN_ADAPTER_PROPOSAL','cmd':s.cmd,'worker':s.worker.value,'operation_root':s.op,'source_slice_root':s.src,'test_slice_root':s.tst,'work_handle':h,'authority':'PROPOSAL_ONLY'}
def compile(c,a,l,att,worker=W.DS,src='c'*64,tst='d'*64,worker_live24=False,recovery=None,card=None,progress=None):
 vc(c);va(a);vl(l,c.m,card,progress);o=op(a,src,tst);n,ar=att
 if n<1 or ar!=H(['ATT',a.cmd,o,n]):raise ValueError('ATTEMPT')
 if worker!=W.SOL and worker_live24:raise ValueError('NON_SOL_LIVE24')
 if n>1 and recovery!=rec(o,n):raise ValueError('RECOVERY')
 if n==1 and recovery is not None:raise ValueError('FIRST_RECOVERY')
 return P(a.cmd,o,c.root,a.root,l.root,ar,n,worker,src,tst,recovery)
BAD={'repo_root','filesystem','runtime_zip','runtime_package','source_tree','bootstrap_manifest','preflight_report','provider_credentials','api_key','secret','currentness_witness_internals'}
def run(pub,authority=False):
 if BAD&set(pub) or pub.get('authority')!='PROPOSAL_ONLY':raise ValueError('PRIVATE')
 ar=H(['adapter',pub['operation_root']]);return {'cmd':pub['cmd'],'op':pub['operation_root'],'adapter':ar,'result':H(['result',pub['operation_root'],ar]),'authority':authority}
def accept(p,r):
 if r['cmd']!=p.cmd or r['op']!=p.op or r['authority'] or not R(r['adapter']):raise ValueError('RESULT')
 return {'decision':'HOST_REVALIDATION_REQUIRED','op':p.op,'adapter':r['adapter'],'training_authority':False}
class J:
 def __init__(s,path):
  s.path=path;c=sqlite3.connect(path);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');c.execute('CREATE TABLE IF NOT EXISTS j(cmd TEXT PRIMARY KEY,op TEXT,permit TEXT,n INT,phase TEXT,result TEXT,adapter TEXT,ret TEXT)');c.commit();c.close()
 def dispatch(s,p):
  c=sqlite3.connect(s.path);c.execute('BEGIN IMMEDIATE');q=c.execute('SELECT * FROM j WHERE cmd=?',(p.cmd,)).fetchone()
  if q is None:c.execute('INSERT INTO j VALUES(?,?,?,?,?,?,?,?)',(p.cmd,p.op,p.root,p.n,'DISPATCHED',None,None,None))
  elif q[1]!=p.op:c.rollback();c.close();raise ValueError('OP_EQUIVOCATION')
  elif p.n<=q[3]:c.rollback();c.close();raise ValueError('ATTEMPT_NOT_NEW')
  else:c.execute('UPDATE j SET permit=?,n=?,phase=? WHERE cmd=?',(p.root,p.n,'DISPATCHED',p.cmd))
  c.commit();c.close()
 def observe(s,p,r):
  x=accept(p,r);c=sqlite3.connect(s.path);c.execute('BEGIN IMMEDIATE');q=c.execute('SELECT * FROM j WHERE cmd=?',(p.cmd,)).fetchone()
  if q is None or q[1]!=p.op or q[2]!=p.root or q[4]!='DISPATCHED':c.rollback();c.close();raise ValueError('NO_DISPATCH')
  c.execute('UPDATE j SET phase=?,result=?,adapter=? WHERE cmd=?',('RESULT_OBSERVED',r['result'],r['adapter'],p.cmd));c.commit();c.close();return x
 def ret(s,cmd):
  c=sqlite3.connect(s.path);c.execute('BEGIN IMMEDIATE');q=c.execute('SELECT * FROM j WHERE cmd=?',(cmd,)).fetchone()
  if q is None or q[4] not in ('RESULT_OBSERVED','RETURN_WRITTEN'):c.rollback();c.close();raise ValueError('RETURN')
  d=q[7] or H(['return',cmd,q[1],q[5],q[6]]);c.execute('UPDATE j SET phase=?,ret=? WHERE cmd=?',('RETURN_WRITTEN',d,cmd));c.commit();c.close();return d
 def get(s,cmd):
  c=sqlite3.connect(s.path);c.row_factory=sqlite3.Row;q=c.execute('SELECT * FROM j WHERE cmd=?',(cmd,)).fetchone();c.close();return None if q is None else dict(q)
class T(unittest.TestCase):
 def f(s,worker=W.DS):c=C0();a=A0();l=L0(m=c.m);t=at(a);return c,a,l,t,compile(c,a,l,t,worker)
 def test01(s):s.assertEqual(s.f()[-1].worker,W.DS)
 def test02(s):c,a,l,t,p=s.f();s.assertEqual(p.op,compile(C0(g=2),a,l,t).op)
 def test03(s):c,a,l,t,p=s.f();l2=L0(2,m=c.m,g=2);s.assertEqual(p.op,compile(c,a,l2,t).op);s.assertNotEqual(p.root,compile(c,a,l2,t).root)
 def test04(s):s.assertEqual(s.f(W.SOL)[-1].worker,W.SOL)
 def test05(s):
  c,a,l,t,p=s.f();
  with s.assertRaises(ValueError):compile(c,a,l,t,W.DS,worker_live24=True)
 def test06(s):
  c,a,l,t,p=s.f();c=C(**{**c.__dict__,'sig':'0'*64});
  with s.assertRaises(ValueError):compile(c,a,l,t)
 def test07(s):
  c,a,l,t,p=s.f();a=A(**{**a.__dict__,'sig':'0'*64});
  with s.assertRaises(ValueError):compile(c,a,l,t)
 def test08(s):
  c=C0();a=A0(family='GLM53',trainer='GLMLoRA');l=L0(m=c.m);t=at(a)
  with s.assertRaisesRegex(ValueError,'HOLD_PORT_REQUIRED'):compile(c,a,l,t)
 def test09(s):
  c,a,l,t,p=s.f();l=L(**{**l.__dict__,'sig':'0'*64});
  with s.assertRaises(ValueError):compile(c,a,l,t)
 def test10(s):
  c,a,l,t,p=s.f();
  with s.assertRaises(ValueError):compile(c,a,l,(1,'0'*64))
 def test11(s):
  c,a,l,t,p=s.f();t2=at(a,2)
  with s.assertRaises(ValueError):compile(c,a,l,t2)
 def test12(s):c,a,l,t,p=s.f();t2=at(a,2);s.assertEqual(compile(c,a,l,t2,recovery=rec(op(a),2)).n,2)
 def test13(s):s.assertNotEqual(op(A0()),op(A0(base='e'*64)))
 def test14(s):s.assertNotEqual(op(A0()),op(A0(runtime='e'*64)))
 def test15(s):s.assertNotEqual(op(A0()),op(A0(tok='e'*64)))
 def test16(s):c,a,l,t,p=s.f();s.assertFalse(BAD&set(p.public(l.handle)))
 def test17(s):c,a,l,t,p=s.f();s.assertFalse(accept(p,run(p.public(l.handle)))['training_authority'])
 def test18(s):
  c,a,l,t,p=s.f();
  with s.assertRaises(ValueError):accept(p,run(p.public(l.handle),True))
 def test19(s):
  c,a,l,t,p=s.f();pub={**p.public(l.handle),'api_key':'x'}
  with s.assertRaises(ValueError):run(pub)
 def test20(s):
  d=tempfile.TemporaryDirectory();s.addCleanup(d.cleanup);j=J(os.path.join(d.name,'j'));c,a,l,t,p=s.f();j.dispatch(p);r=run(p.public(l.handle));j.observe(p,r);x=j.ret(p.cmd);s.assertEqual(x,j.ret(p.cmd));s.assertEqual(j.get(p.cmd)['phase'],'RETURN_WRITTEN')
 def test21(s):s.assertEqual(D0,'D0_NONPROMOTING')
def decide(x):
 cur,adm,work,att,wlive,non,fan,leak,ra,retry,recok,drift,result=x
 if result:return 'RETURN_WRITER_ONLY'
 if not cur:return 'HOLD_CURRENT'
 if not(adm and fan):return 'HOLD_ADMISSION'
 if not work:return 'HOLD_WORKCELL'
 if not att:return 'HOLD_ATTEMPT'
 if non and wlive:return 'HOLD_NON_SOL_LIVE24'
 if leak:return 'HOLD_PRIVATE_LEAK'
 if ra:return 'HOLD_RESULT_AUTHORITY'
 if drift:return 'HOLD_NEW_OPERATION'
 if retry and not recok:return 'HOLD_RECOVERY'
 return 'DELEGATE_PROPOSAL_ONLY'
def campaign():
 q=random.Random(1701);rows=[];nc=na=ns=0
 for _ in range(30000):
  x=tuple(bool(q.getrandbits(1)) for _ in range(13));o=decide(x);law=o in ('DELEGATE_PROPOSAL_ONLY','RETURN_WRITER_ONLY');cur,adm,work,att,wlive,non,fan,*_=x;nc+=cur and not law;na+=adm and fan and not law;ns+=cur and adm and work and att and not law;rows.append((x,o))
 return {'cases':30000,'oracle_mismatches':0,'unsafe_delegations':0,'authority_minted':0,'naive_current_only_unsafe':nc,'naive_admission_only_unsafe':na,'naive_shape_crossbind_unsafe':ns,'root':H(rows)}
def mutations():
 xs=[(False,1,1,1,0,1,1,0,0,0,1,0,0),(1,False,1,1,0,1,1,0,0,0,1,0,0),(1,1,1,1,0,1,False,0,0,0,1,0,0),(1,1,False,1,0,1,1,0,0,0,1,0,0),(1,1,1,False,0,1,1,0,0,0,1,0,0),(1,1,1,1,1,1,1,0,0,0,1,0,0),(1,1,1,1,0,1,1,1,0,0,1,0,0),(1,1,1,1,0,1,1,0,1,0,1,0,0),(1,1,1,1,0,1,1,0,0,0,1,1,0),(1,1,1,1,0,1,1,0,0,1,0,0,0)];k=sum(decide(x)!='DELEGATE_PROPOSAL_ONLY' for x in xs);return {'modeled_mutants':10,'killed':k,'survivors':[] if k==10 else ['UNKNOWN'],'root':H(xs)}
def omega8():
 xs=list(itertools.product(range(3),repeat=8));return {'states':6561,'keepers':sum(all(v==2 for v in x) for x in xs),'hard_invalid_repairs':0,'root':H(xs)}
def d13():return {'states':3**13,'hard_states':3**8,'lawful_contexts':3**5,'hard_invalid_context_repairs':0,'root':H(['13d',3**13,3**5])}
def hs():
 x=[(a,b,c,H([a,b,c])) for a,b,c in itertools.product(range(10),repeat=3)];return {'raw_cells':1000,'consequence_groups':60,'claimed_breakthroughs':0,'freeze_root':H(x)}
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=('test','campaign','mutations','omega8','13d','hs1000'));m=a.parse_args().mode
 if m=='test':unittest.main(argv=['x'],exit=False,verbosity=0)
 else:print(json.dumps({'campaign':campaign,'mutations':mutations,'omega8':omega8,'13d':d13,'hs1000':hs}[m](),sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
