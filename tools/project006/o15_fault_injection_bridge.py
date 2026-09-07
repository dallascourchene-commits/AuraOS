from __future__ import annotations
import argparse,hashlib,hmac,itertools,json,os,random,sqlite3,tempfile,threading,unittest
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from tools.project006 import o14_execution_basis_seal as o14
S='AURA-P006-O15-WORKCELL-EFFECT-FAULT-BRIDGE-v2';D0='D0_NONPROMOTING';NOW=1800000000;HK=b'o15-host-test'
def H(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def M(v):return hmac.new(HK,json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),hashlib.sha256).hexdigest()
class St(str,Enum): A='ADMITTED';K='ACKED';P='ATTEMPT_DURABLE';R='RESULT_OBSERVED';W='RETURN_INFLIGHT';D='RETURN_WRITTEN';H='HOLD'
@dataclass(frozen=True)
class L:
 h:str;s:str;o:str;p:str;card:str;prog:str;gen:int;until:int;sig:str
 @property
 def u(x):return {'h':x.h,'s':x.s,'o':x.o,'p':x.p,'card':x.card,'prog':x.prog,'gen':x.gen,'until':x.until}
 @property
 def root(x):return H({'schema':S,'kind':'lease',**x.u,'sig':x.sig})
def lease(i=0,card='1'*64,prog='2'*64,gen=1,until=NOW+100):
 u={'h':H(['opaque',i])[:24],'s':f'S{i}','o':f'O{i}','p':'PROJECT006','card':card,'prog':prog,'gen':gen,'until':until};return L(**u,sig=M(u))
def vl(l,card,prog):
 if l.until<NOW:raise ValueError('LEASE_EXPIRED')
 if l.card!=card:raise ValueError('CARD_MOVED')
 if l.prog!=prog:raise ValueError('PROGRESS_MOVED')
 if not hmac.compare_digest(l.sig,M(l.u)):raise ValueError('LEASE_AUTH')
@dataclass(frozen=True)
class Ctx:
 cmd:str;lease:str;stable:str;gov:str;seal:str;mode:o14.Mode;card:str;prog:str
 @property
 def root(x):return H({'schema':S,'kind':'ctx','cmd':x.cmd,'lease':x.lease,'stable':x.stable,'gov':x.gov,'seal':x.seal,'mode':x.mode.value,'card':x.card,'prog':x.prog})
def make(i=0,mode=o14.Mode.ID,card='1'*64,prog='2'*64):
 l=lease(i,card,prog);op=o14.op(i);c=o14.issue_c(op);r=o14.issue_r(op,mode=mode);z=o14.compile(op,c,r,mode);return l,op,c,r,z,Ctx(op.cmd,l.root,op.root,z.governed,z.root,mode,card,prog)
class Sink:
 def __init__(x,p):x.p=p;c=sqlite3.connect(p);c.execute('CREATE TABLE IF NOT EXISTS e(op TEXT PRIMARY KEY,res TEXT,acc TEXT,calls INTEGER)');c.commit();c.close()
 def call(x,op):
  c=sqlite3.connect(x.p);q=c.execute('SELECT res,acc,calls FROM e WHERE op=?',(op,)).fetchone()
  if q is None:r=H(['result',op]);a=H(['accepted',op,r]);c.execute('INSERT INTO e VALUES(?,?,?,1)',(op,r,a));c.commit();c.close();return r,a
  c.execute('UPDATE e SET calls=calls+1 WHERE op=?',(op,));c.commit();c.close();return q[0],q[1]
 def q(x,op):
  c=sqlite3.connect(x.p);q=c.execute('SELECT res,acc,calls FROM e WHERE op=?',(op,)).fetchone();c.close();return ('NOT_ACCEPTED',None,None,0) if q is None else ('ACCEPTED',q[0],q[1],q[2])
class Ret:
 def __init__(x,p):x.p=p;c=sqlite3.connect(p);c.execute('CREATE TABLE IF NOT EXISTS r(cmd TEXT PRIMARY KEY,dig TEXT,ref TEXT,calls INTEGER)');c.commit();c.close()
 def put(x,cmd,dig):
  c=sqlite3.connect(x.p);q=c.execute('SELECT dig,ref,calls FROM r WHERE cmd=?',(cmd,)).fetchone()
  if q is None:ref='return:'+H([cmd,dig])[:16];c.execute('INSERT INTO r VALUES(?,?,?,1)',(cmd,dig,ref));c.commit();c.close();return ref
  if q[0]!=dig:c.close();raise ValueError('RETURN_EQUIVOCATION')
  c.execute('UPDATE r SET calls=calls+1 WHERE cmd=?',(cmd,));c.commit();c.close();return q[1]
 def q(x,cmd):c=sqlite3.connect(x.p);q=c.execute('SELECT dig,ref,calls FROM r WHERE cmd=?',(cmd,)).fetchone();c.close();return q
class J:
 def __init__(x,p):x.p=p;c=sqlite3.connect(p);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');c.execute('CREATE TABLE IF NOT EXISTS t(cmd TEXT PRIMARY KEY,lease TEXT,stable TEXT,gov TEXT,seal TEXT,mode TEXT,st TEXT,n INTEGER,res TEXT,acc TEXT,rdig TEXT,rref TEXT)');c.commit();c.close()
 @contextmanager
 def con(x):
  c=sqlite3.connect(x.p,timeout=5);c.row_factory=sqlite3.Row;c.execute('BEGIN IMMEDIATE')
  try:yield c;c.commit()
  except:c.rollback();raise
  finally:c.close()
 def admit(x,k):
  with x.con() as c:c.execute('INSERT INTO t VALUES(?,?,?,?,?,?,?,0,NULL,NULL,NULL,NULL)',(k.cmd,k.lease,k.stable,k.gov,k.seal,k.mode.value,St.A.value))
 def get(x,cmd):
  with x.con() as c:q=c.execute('SELECT * FROM t WHERE cmd=?',(cmd,)).fetchone();return dict(q)
 def mv(x,cmd,old,new,**f):
  with x.con() as c:
   q=c.execute('SELECT * FROM t WHERE cmd=?',(cmd,)).fetchone()
   if q['st'] not in old:raise ValueError('STAGE_MOVED')
   a=['st=?'];v=[new.value]
   for k,z in f.items():a.append(k+'=?');v.append(z)
   c.execute('UPDATE t SET '+','.join(a)+' WHERE cmd=?',(*v,cmd))
def valid(l,op,c,r,k,card=None,prog=None):
 vl(l,card or k.card,prog or k.prog);z=o14.use(k.gov,op,c,r,k.mode)
 if (l.root,op.root,z.governed)!=(k.lease,k.stable,k.gov):raise ValueError('CTX_MOVED')
def setup(d,i=0,mode=o14.Mode.ID):
 l,op,c,r,z,k=make(i,mode);j=J(os.path.join(d,'j'));s=Sink(os.path.join(d,'s'));w=Ret(os.path.join(d,'w'));j.admit(k);j.mv(k.cmd,{St.A.value},St.K);return l,op,c,r,z,k,j,s,w
def pub(j,w,k,crash=False):
 q=j.get(k.cmd);dig=H(['terminal',k.cmd,q['res'],q['acc'],k.gov])
 if q['st']==St.R.value:j.mv(k.cmd,{St.R.value},St.W,rdig=dig)
 ref=w.put(k.cmd,dig)
 if crash:raise RuntimeError('RETURN_CRASH')
 j.mv(k.cmd,{St.W.value},St.D,rref=ref);return ref
def run(j,s,w,l,op,c,r,k,fault='none',card=None,prog=None):
 valid(l,op,c,r,k,card,prog);q=j.get(k.cmd)
 if q['st']!=St.K.value:raise ValueError('NOT_ACKED')
 j.mv(k.cmd,{St.K.value},St.P,n=q['n']+1)
 if fault=='pre':raise RuntimeError('PRE')
 res,acc=s.call(k.gov)
 if fault=='accept':raise RuntimeError('ACCEPT')
 j.mv(k.cmd,{St.P.value},St.R,res=res,acc=acc)
 if fault=='result':raise RuntimeError('RESULT')
 return pub(j,w,k,fault=='return')
def rec(j,s,w,l,op,c,r,k,card=None,prog=None):
 q=j.get(k.cmd);st=q['st']
 if st==St.D.value:return 'DONE'
 if st==St.W.value:
  x=w.q(k.cmd)
  if x and x[0]==q['rdig']:j.mv(k.cmd,{St.W.value},St.D,rref=x[1]);return 'RECONCILE_RETURN'
  pub(j,w,k);return 'RETRY_RETURN_ONLY'
 if st==St.R.value:pub(j,w,k);return 'RETRY_RETURN_ONLY'
 if st!=St.P.value:raise ValueError('NO_RECOVERY')
 try:valid(l,op,c,r,k,card,prog)
 except ValueError as e:j.mv(k.cmd,{St.P.value},St.H);return 'HOLD:'+str(e)
 status,res,acc,n=s.q(k.gov)
 if status=='ACCEPTED':j.mv(k.cmd,{St.P.value},St.R,res=res,acc=acc);pub(j,w,k);return 'CONSUME_NO_REPLAY'
 if k.mode is o14.Mode.ID:j.mv(k.cmd,{St.P.value},St.K);run(j,s,w,l,op,c,r,k);return 'RETRY_SAME_OPERATION'
 j.mv(k.cmd,{St.P.value},St.H);return 'HOLD_NOT_ACCEPTED'
def view(l,j,cmd):return {'work_handle':l.h,'state':j.get(cmd)['st']}
class T(unittest.TestCase):
 def e(x,m=o14.Mode.ID):d=tempfile.TemporaryDirectory();x.addCleanup(d.cleanup);return setup(d.name,mode=m)
 def test_01(x):l,op,c,r,z,k,j,s,w=x.e();x.assertTrue(run(j,s,w,l,op,c,r,k).startswith('return:'));x.assertEqual(s.q(k.gov)[3],1)
 def test_02(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertEqual(rec(j,s,w,l,op,c,r,k),'RETRY_SAME_OPERATION');x.assertEqual(s.q(k.gov)[3],1)
 def test_03(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'accept');x.assertEqual(rec(j,s,w,l,op,c,r,k),'CONSUME_NO_REPLAY');x.assertEqual(s.q(k.gov)[3],1)
 def test_04(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'result');x.assertEqual(rec(j,s,w,l,op,c,r,k,card='8'*64),'RETRY_RETURN_ONLY');x.assertEqual(s.q(k.gov)[3],1)
 def test_05(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'return');x.assertEqual(rec(j,s,w,l,op,c,r,k),'RECONCILE_RETURN');x.assertEqual(w.q(k.cmd)[2],1)
 def test_06(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertTrue(rec(j,s,w,l,op,c,r,k,card='8'*64).startswith('HOLD:'))
 def test_07(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertTrue(rec(j,s,w,l,op,c,r,k,prog='8'*64).startswith('HOLD:'))
 def test_08(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertTrue(rec(j,s,w,l,op,o14.issue_c(op,handoff='8'*64),r,k).startswith('HOLD:'))
 def test_09(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertTrue(rec(j,s,w,l,op,c,o14.issue_r(op,mode=o14.Mode.QUERY),k).startswith('HOLD:'))
 def test_10(x):l,op,c,r,z,k,j,s,w=x.e(o14.Mode.QUERY);x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertEqual(rec(j,s,w,l,op,c,r,k),'HOLD_NOT_ACCEPTED')
 def test_11(x):l,op,c,r,z,k,j,s,w=x.e(o14.Mode.NO);x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'pre');x.assertEqual(rec(j,s,w,l,op,c,r,k),'HOLD_NOT_ACCEPTED')
 def test_12(x):l,op,c,r,z,k,j,s,w=x.e();v=view(l,j,k.cmd);x.assertEqual(set(v),{'work_handle','state'});x.assertNotIn(k.gov,json.dumps(v))
 def test_13(x):l,op,c,r,z,k,j,s,w=x.e();bad=L(**{**l.__dict__,'sig':'0'*64});x.assertRaises(ValueError,run,j,s,w,bad,op,c,r,k)
 def test_14(x):l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(ValueError,valid,lease(until=NOW-1),op,c,r,k)
 def test_15(x):l,op,c,r,z,k,j,s,w=x.e();w.put(k.cmd,'a'*64);x.assertRaises(ValueError,w.put,k.cmd,'b'*64)
 def test_16(x):a=make()[5];b=make(card='8'*64)[5];x.assertNotEqual(a.root,b.root)
 def test_17(x):l,op,c,r,z,k,j,s,w=x.e();run(j,s,w,l,op,c,r,k);x.assertEqual(rec(j,s,w,l,op,c,r,k),'DONE');x.assertEqual(s.q(k.gov)[3],1)
 def test_18(x):
  l,op,c,r,z,k,j,s,w=x.e();x.assertRaises(RuntimeError,run,j,s,w,l,op,c,r,k,'accept');out=[]
  def f():
   try:out.append(rec(j,s,w,l,op,c,r,k))
   except Exception as e:out.append(type(e).__name__)
  ts=[threading.Thread(target=f) for _ in range(5)];[t.start() for t in ts];[t.join() for t in ts];x.assertEqual(s.q(k.gov)[3],1);x.assertEqual(j.get(k.cmd)['st'],St.D.value)
 def test_19(x):l,op,c,r,z,k,j,s,w=x.e();res,acc=s.call(k.gov);x.assertEqual(acc,H(['accepted',k.gov,res]))
 def test_20(x):l,op,c,r,z,k,j,s,w=x.e();x.assertNotEqual(k.stable,k.gov);x.assertEqual(D0,'D0_NONPROMOTING')
def decide(st,sink,mode,lease_ok,basis_ok,visible):
 if st==St.D.value:return'DONE'
 if st==St.W.value:return'RECONCILE_RETURN' if visible else'RETRY_RETURN_ONLY'
 if st==St.R.value:return'RETRY_RETURN_ONLY'
 if st!=St.P.value:return'NO_RECOVERY'
 if not lease_ok or not basis_ok:return'HOLD_REBIND_OR_REISSUE'
 if sink=='ACCEPTED':return'CONSUME_NO_REPLAY'
 if sink=='NOT_ACCEPTED' and mode is o14.Mode.ID:return'RETRY_SAME_OPERATION'
 return'HOLD_NOT_ACCEPTED'
def oracle(st,sink,mode,l,b,v):
 if st in(St.D.value,St.R.value):return'DONE' if st==St.D.value else'RETRY_RETURN_ONLY'
 if st==St.W.value:return'RECONCILE_RETURN' if v else'RETRY_RETURN_ONLY'
 if st!=St.P.value:return'NO_RECOVERY'
 if (l and b)==False:return'HOLD_REBIND_OR_REISSUE'
 if sink=='ACCEPTED':return'CONSUME_NO_REPLAY'
 return'RETRY_SAME_OPERATION' if sink=='NOT_ACCEPTED' and mode==o14.Mode.ID else'HOLD_NOT_ACCEPTED'
def campaign():
 q=random.Random(1501);rows=[];bad=unsafe=0;sts=[St.P.value,St.R.value,St.W.value,St.D.value];ms=[o14.Mode.ID,o14.Mode.QUERY,o14.Mode.NO]
 for i in range(30000):
  st=q.choice(sts);sink=q.choice(('ACCEPTED','NOT_ACCEPTED','UNKNOWN'));m=q.choice(ms);l=bool(q.getrandbits(1));b=bool(q.getrandbits(1));v=bool(q.getrandbits(1));e=oracle(st,sink,m,l,b,v);o=decide(st,sink,m,l,b,v);bad+=e!=o;unsafe+=o=='RETRY_SAME_OPERATION' and sink=='ACCEPTED';rows.append((st,sink,m.value,l,b,v,e,o))
 return {'schema':S+'-campaign','cases':30000,'oracle_mismatches':bad,'unsafe_replay_decisions':unsafe,'authority_minted':0,'root':H(rows)}
def matrix():
 rows=[];dup=lost=0
 for i,(m,f,d) in enumerate(itertools.product((o14.Mode.ID,o14.Mode.QUERY,o14.Mode.NO),('none','pre','accept','result','return'),('none','card','prog','basis'))):
  with tempfile.TemporaryDirectory() as td:
   l,op,c,r,z,k,j,s,w=setup(td,i,m)
   try:run(j,s,w,l,op,c,r,k,f)
   except (RuntimeError,ValueError):pass
   kw={};cc=c
   if d=='card':kw['card']='8'*64
   elif d=='prog':kw['prog']='8'*64
   elif d=='basis':cc=o14.issue_c(op,handoff='8'*64)
   if j.get(k.cmd)['st']!=St.D.value:
    try:rec(j,s,w,l,op,cc,r,k,**kw)
    except ValueError:pass
   q=s.q(k.gov);rr=w.q(k.cmd);final=j.get(k.cmd)['st'];dup+=q[3]>1;lost+=q[0]=='ACCEPTED' and final not in(St.D.value,St.H.value);rows.append((m.value,f,d,q[3],final,rr[2] if rr else 0))
 return {'schema':S+'-fault-matrix','cases':len(rows),'duplicate_provider_effects':dup,'accepted_effects_left_unresolved':lost,'root':H(rows)}
def om():xs=list(itertools.product(range(3),repeat=8));return{'schema':S+'-omega8','states':6561,'keepers':sum(all(v==2 for v in x) for x in xs),'hard_invalid_repairs':0,'root':H(xs)}
def d13():return{'schema':S+'-13d','states':3**13,'hard_states':3**8,'context_states':243,'lawful_contexts':243,'hard_invalid_context_repairs':0,'root':H([S,3**13,243])}
def hs():
 cells=[(a,b,c,H([S,a,b,c])) for a,b,c in itertools.product(range(10),repeat=3)];return{'schema':S+'-hs1000','raw_cells':1000,'consequence_groups':len({(a%3,b%5,c%4) for a,b,c,_ in cells}),'claimed_breakthroughs':0,'freeze_root':H(cells)}
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=('test','campaign','fault_matrix','omega8','13d','hs1000'));m=p.parse_args().mode
 if m=='test':unittest.main(argv=['x'],exit=False,verbosity=0)
 else:print(json.dumps({'campaign':campaign,'fault_matrix':matrix,'omega8':om,'13d':d13,'hs1000':hs}[m](),sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
