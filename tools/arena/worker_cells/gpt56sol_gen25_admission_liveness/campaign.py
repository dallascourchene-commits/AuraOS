import hashlib,json,random
from liveness_witness import *
NOW=2_000_000; HEAD=Head('GEN25','d91e0a39358901c5')
def rec(cid,attempt,seq,t,event,detail): return TypedReceipt(cid,attempt,seq,t,event,detail)
def run():
 rng=random.Random(852); counts={'cases':1000,'holds':0,'future_rejected':0,'wrong_admissions':0}; roots=[]
 for i in range(1000):
  cid=f'C{i}'; c=Command(cid,NOW-7200,'GEN25','d91e0a39358901c5','READY',False); axis=i%8
  rs=[]; expected=None
  if axis==0: rs=[rec(cid,'A1',0,NOW-10,EventClass.ACK_ACCEPTED,'OK')]; expected=CommandState.ADMITTED_NOT_TERMINAL
  elif axis==1: rs=[rec(cid,'A1',0,NOW-10,EventClass.REJECTED,'POLICY')]; expected=CommandState.TYPED_REJECTED
  elif axis==2: rs=[rec(cid,'A1',0,NOW-10,EventClass.TERMINAL_RESULT,'DONE')]; expected=CommandState.TERMINAL
  elif axis==3: rs=[rec(cid,'A1',0,NOW-10,EventClass.ACK_ACCEPTED,'X'),rec(cid,'A1',0,NOW-9,EventClass.ACK_ACCEPTED,'Y')]; expected=CommandState.RECEIPT_INTEGRITY_HOLD
  elif axis==4: rs=[rec(cid,'A1',0,NOW-10,EventClass.ACK_ACCEPTED,'X'),rec(cid,'A2',1,NOW-9,EventClass.ACK_ACCEPTED,'Y')]; expected=CommandState.RECEIPT_INTEGRITY_HOLD
  elif axis==5: rs=[rec(cid,'A1',0,NOW-10,EventClass.TERMINAL_RESULT,'DONE'),rec(cid,'A1',1,NOW-9,EventClass.ACK_ACCEPTED,'LATE')]; expected=CommandState.RECEIPT_INTEGRITY_HOLD
  elif axis==6: rs=[rec('OTHER','A1',0,NOW-10,EventClass.TERMINAL_RESULT,'DONE')]; expected=CommandState.ADMISSION_STARVED
  else: rs=[rec(cid,'A1',0,NOW+1,EventClass.ACK_ACCEPTED,'FUTURE')]; expected='FUTURE'
  try: got=classify_command(NOW,HEAD,c,rs).state
  except E as e:
   if expected=='FUTURE' and str(e)=='FUTURE_RECEIPT': counts['future_rejected']+=1; got='FUTURE'
   else: got=f'E:{e}'
  if got==CommandState.RECEIPT_INTEGRITY_HOLD: counts['holds']+=1
  if got!=expected: counts['wrong_admissions']+=1
  roots.append(str(got))
 counts['root']=hashlib.sha256(json.dumps(roots,separators=(',',':')).encode()).hexdigest()
 print(json.dumps(counts,sort_keys=True))
 if counts['wrong_admissions']: raise SystemExit(1)
if __name__=='__main__': run()
