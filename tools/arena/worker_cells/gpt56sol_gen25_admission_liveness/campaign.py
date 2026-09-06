from hashlib import sha256
import itertools,json,random
from liveness_witness import *
NOW=2_000_000; HEAD=Head('GEN25','d91e0a39358901c5')
def rec(cid,t,event,detail='OK',attempt='A1',seq=0): return TypedReceipt(cid,attempt,seq,t,event,detail)
def expected(c,mode):
 q='INACTIVE' if c.queue_state in INACTIVE_QUEUE_STATES else 'UNKNOWN' if c.queue_state not in ACTIVE_QUEUE_STATES else 'ACTIVE'
 if q=='INACTIVE': return CommandState.INACTIVE_QUEUE
 if q=='UNKNOWN': return CommandState.UNKNOWN
 if c.generation!=HEAD.generation or c.head_digest!=HEAD.digest: return CommandState.STALE_HEAD
 return {0:CommandState.ADMISSION_STARVED,1:CommandState.ADMITTED_NOT_TERMINAL,2:CommandState.TERMINAL,3:CommandState.TYPED_REJECTED,4:CommandState.ADMISSION_STARVED,5:CommandState.ADMISSION_STARVED,6:CommandState.RECEIPT_INTEGRITY_HOLD,7:'FUTURE'}[mode]
def run():
 rng=random.Random(59025); mismatches=0; future=0; roots=[]
 for i in range(100_000):
  cid=f'C{i}'; created=1_000_000+rng.randrange(900_000); gen='GEN25' if rng.randrange(7) else 'GEN24'; q=('READY','CANCELLED','MYSTERY')[rng.randrange(3)] if rng.randrange(10)==0 else 'AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND'; dig='d91e0a39358901c5' if rng.randrange(11) else 'wrong'; c=Command(cid,created,gen,dig,q,False); mode=rng.randrange(8); rs=[]
  t=created+rng.randrange(max(1,NOW-created))
  if mode==1: rs=[rec(cid,t,EventClass.ACK_ACCEPTED)]
  elif mode==2: rs=[rec(cid,t,EventClass.TERMINAL_RESULT)]
  elif mode==3: rs=[rec(cid,t,EventClass.REJECTED,'CURRENTNESS_REJECTED')]
  elif mode==4: rs=[rec('OTHER',NOW-1,EventClass.TERMINAL_RESULT)]
  elif mode==5: rs=[rec(cid,max(0,created-1),EventClass.ACK_ACCEPTED)]
  elif mode==6: rs=[rec(cid,t,EventClass.ACK_ACCEPTED,'X',seq=0),rec(cid,t+1,EventClass.ACK_ACCEPTED,'Y',seq=0)]
  elif mode==7: rs=[rec(cid,NOW+1,EventClass.ACK_ACCEPTED)]
  exp=expected(c,mode)
  try: got=classify_command(NOW,HEAD,c,rs).state
  except E as e: got='FUTURE' if str(e)=='FUTURE_RECEIPT' else f'E:{e}'
  if got=='FUTURE': future+=1
  mismatches+=got!=exp; roots.append(str(got))
 hs_bad=0
 for i in range(1000):
  cid=f'HS{i}'; c=Command(cid,NOW-7200,'GEN25','d91e0a39358901c5','READY',False); a=i%8
  if a==0: rs=[rec(cid,NOW-10,EventClass.ACK_ACCEPTED)]; exp=CommandState.ADMITTED_NOT_TERMINAL
  elif a==1: rs=[rec(cid,NOW-10,EventClass.REJECTED)]; exp=CommandState.TYPED_REJECTED
  elif a==2: rs=[rec(cid,NOW-10,EventClass.TERMINAL_RESULT)]; exp=CommandState.TERMINAL
  elif a==3: rs=[rec(cid,NOW-10,EventClass.ACK_ACCEPTED,'X'),rec(cid,NOW-9,EventClass.ACK_ACCEPTED,'Y')]; exp=CommandState.RECEIPT_INTEGRITY_HOLD
  elif a==4: rs=[rec(cid,NOW-10,EventClass.ACK_ACCEPTED,attempt='A1'),rec(cid,NOW-9,EventClass.ACK_ACCEPTED,attempt='A2',seq=1)]; exp=CommandState.RECEIPT_INTEGRITY_HOLD
  elif a==5: rs=[rec(cid,NOW-10,EventClass.TERMINAL_RESULT),rec(cid,NOW-9,EventClass.ACK_ACCEPTED,seq=1)]; exp=CommandState.RECEIPT_INTEGRITY_HOLD
  elif a==6: rs=[rec('OTHER',NOW-10,EventClass.TERMINAL_RESULT)]; exp=CommandState.ADMISSION_STARVED
  else: rs=[rec(cid,NOW+1,EventClass.ACK_ACCEPTED)]; exp='FUTURE'
  try: got=classify_command(NOW,HEAD,c,rs).state
  except E as e: got='FUTURE' if str(e)=='FUTURE_RECEIPT' else f'E:{e}'
  hs_bad+=got!=exp
 consumer_rejected=0
 for i in range(1000):
  bad=ConsumerObservation(True,service_active=(None if i%3==0 else (i if i%2 else True)))
  try: compile_recovery(now_s=NOW,head=HEAD,commands=[Command(f'X{i}',NOW-7200,'GEN25','d91e0a39358901c5','READY',False)],receipts=[],consumer=bad,starvation_after_s=3600,reducer_stall_after_s=3600)
  except E: consumer_rejected+=1
 omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8)); repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
 out={'oracle_decisions':100000,'oracle_mismatches':mismatches,'future_receipts_rejected':future,'hs1000_wrong':hs_bad,'consumer_fuzz_rejected':consumer_rejected,'omega8_keepers':omega,'13d_repairs':repairs,'oracle_root':sha256(''.join(roots).encode()).hexdigest()}; out['campaign_root']=sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(); print(json.dumps(out,sort_keys=True))
 if mismatches or hs_bad or consumer_rejected!=667 or omega!=1 or repairs!=0: raise SystemExit(1)
if __name__=='__main__': run()
