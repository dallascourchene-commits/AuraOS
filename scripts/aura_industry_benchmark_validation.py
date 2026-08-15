#!/usr/bin/env python3
"""AuraOS bounded industry-readiness validation orchestrator.

Composes repository-defined implementation microbenchmarks with correctness,
lease, fail-closed, and exact-once fleet checks. No third-party certification
or hardware-independent guarantee is claimed.
"""
from __future__ import annotations
import argparse, hashlib, json, py_compile, sqlite3, subprocess, sys, time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CORE=ROOT/'core'; SCRIPTS=ROOT/'scripts'; OUTBOX=ROOT/'aura_workspace'/'outbox'; DB_PATH=ROOT/'aura_workspace'/'industry_validation_dispatcher.db'
sys.path.insert(0,str(CORE)); from aura_task_dispatcher import TaskDispatcher

def clean_db(p):
    for s in ('','-wal','-shm'):
        try: Path(str(p)+s).unlink()
        except FileNotFoundError: pass

def run_json(cmd,timeout=180):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    return p,json.loads(p.stdout)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source-commit',default='UNKNOWN'); a=ap.parse_args(); OUTBOX.mkdir(parents=True,exist_ok=True); gates=[]
    def gate(n,name,ok,evidence):
        gates.append({'number':n,'gate':name,'status':'PASS' if ok else 'FAIL','evidence':evidence})
        if not ok: raise AssertionError(f'gate {n}: {name}: {evidence}')
    fp,formal=run_json([sys.executable,str(SCRIPTS/'aura_benchmark_suite.py'),'--json']); gate(1,'Formal benchmark process',fp.returncode==0,'formal suite exited 0')
    gate(2,'FST 100k verification',formal.get('status')=='W_VALIDATED' and formal['fst']['iterations']==100000 and formal['fst']['accepted']+formal['fst']['rejected']==100000,'100k deterministic corpus completed')
    m=formal['merkle']; gate(3,'3^n Merkle 2k verification',m['rollups']==2000 and len(m['aggregate_witness_sha256'])==64,f"depth={m['depth']} witness={m['aggregate_witness_sha256']}")
    w=formal['sqlite_wal']; gate(4,'SQLite WAL 1-25 verification',w['worker_range']==[1,25] and len(w['rows'])==25 and all(x['writes']==w['total_writes_per_trial'] for x in w['rows']),'25 worker-count trials passed embedded row/WAL/integrity gates')
    gate(5,'Peak RSS captured',formal['memory']['peak_rss_bytes']>0,f"peak={formal['memory']['peak_rss_mib']:.2f} MiB")
    ap2,advanced=run_json([sys.executable,str(SCRIPTS/'aura_advanced_benchmark_runner.py')]); gate(6,'Advanced benchmark process',ap2.returncode==0,'advanced suite exited 0')
    u=advanced['udp_loopback']; gate(7,'UDP loopback delivery',u['packets_received']==u['packets_sent']==200,'200/200 datagrams')
    aw=advanced['sqlite_wal']; gate(8,'WAL clean reopen integrity',aw['rows_recovered']==aw['rows_expected']==500 and aw['integrity_check']=='ok' and str(aw['journal_mode']).lower()=='wal','500/500; integrity=ok; WAL')
    for p in [CORE/'aura_task_dispatcher.py',CORE/'aura_worker_daemon.py',SCRIPTS/'aura_benchmark_suite.py',SCRIPTS/'aura_advanced_benchmark_runner.py']: py_compile.compile(str(p),doraise=True)
    gate(9,'Python compile',True,'dispatcher, daemon, formal and advanced runners compiled')
    clean_db(DB_PATH); d=TaskDispatcher(DB_PATH); tids=[d.enqueue('noop',{'fleet_index':i}) for i in range(25)]; outs=[]
    for start in range(0,25,5):
        ps=[subprocess.Popen([sys.executable,str(CORE/'aura_worker_daemon.py'),'--db',str(DB_PATH.relative_to(ROOT)),'--worker-id',f'J{i+1:02d}','--once'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for i in range(start,min(start+5,25))]
        for p in ps:
            o,e=p.communicate(timeout=60); outs.append(p.returncode)
    rows=d.status(); done=[r for r in rows if r['task_id'] in set(tids) and r['status']=='DONE']; idx=[]
    for r in done: idx.append(json.loads(r['result_json']).get('echo',{}).get('fleet_index'))
    gate(10,'25-worker exact-once fleet',len(done)==25 and set(idx)==set(range(25)) and all(x==0 for x in outs),'25 unique DONE payloads')
    t=d.enqueue('noop',{'case':'owner'}); lease=d.claim('J_OWNER',60); rejected=False
    try: d.finish(t,'J_WRONG',ok=True,result={'ok':True})
    except RuntimeError: rejected=True
    d.finish(t,'J_OWNER',ok=True,result={'ok':True}); gate(11,'Lease ownership fail-closed',rejected,'wrong worker rejected')
    t=d.enqueue('noop',{'case':'expiry'}); first=d.claim('J_EXP_OLD',.01); time.sleep(.03); second=d.claim('J_EXP_NEW',60); ok=first and second and first['task_id']==t==second['task_id']; d.finish(t,'J_EXP_NEW',ok=True,result={'ok':True}); gate(12,'Expired lease recovery',bool(ok),'expired lease reclaimed')
    marker=ROOT/'aura_workspace'/'UNSUPPORTED_SHELL_MARKER'; marker.unlink(missing_ok=True); t=d.enqueue('shell',{'command':f'touch {marker}'}); subprocess.run([sys.executable,str(CORE/'aura_worker_daemon.py'),'--db',str(DB_PATH.relative_to(ROOT)),'--worker-id','J_SHELL','--once'],cwd=ROOT,timeout=60); rr=next(r for r in d.status() if r['task_id']==t); gate(13,'Unsupported shell task rejected',rr['status']=='FAILED' and not marker.exists(),'failed closed; marker absent')
    t=d.enqueue('advanced_benchmark',{}); p=subprocess.run([sys.executable,str(CORE/'aura_worker_daemon.py'),'--db',str(DB_PATH.relative_to(ROOT)),'--worker-id','J_ADV','--once'],cwd=ROOT,timeout=180); rr=next(r for r in d.status() if r['task_id']==t); ar=json.loads(rr['result_json']); gate(14,'Benchmark dispatch via daemon',p.returncode==0 and rr['status']=='DONE' and ar.get('ok') is True,'allowlisted advanced benchmark completed')
    c=sqlite3.connect(DB_PATH); mode=c.execute('pragma journal_mode').fetchone()[0]; integ=c.execute('pragma integrity_check').fetchone()[0]; c.close(); gate(15,'Dispatcher WAL integrity',str(mode).lower()=='wal' and integ=='ok',f'mode={mode}; integrity={integ}')
    counts=Counter(r['status'] for r in d.status()); result={'schema':'AURA_INDUSTRY_VALIDATION_V1','work_order':'WO-FLEET-AUTONOMOUS-EXECUTE','source_commit_bound_at_run_start':a.source_commit,'generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'PASS','gates_passed':15,'gates_total':15,'gates':gates,'formal':formal,'advanced':advanced,'fleet':{'processes':25,'unique_done_payloads':len(set(idx)),'task_counts':dict(sorted(counts.items())),'dispatcher_journal_mode':mode,'dispatcher_integrity_check':integ},'qualification':'Repository-defined industry-readiness validation; not third-party certification or hardware-independent guarantee.'}
    (OUTBOX/'WO-FLEET-AUTONOMOUS-EXECUTE.industry-validation.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps(result,sort_keys=True,separators=(',',':'))); clean_db(DB_PATH); return 0
if __name__=='__main__': raise SystemExit(main())
