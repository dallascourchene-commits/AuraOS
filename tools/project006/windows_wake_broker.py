from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, subprocess, time
from pathlib import Path
from typing import Any, Callable

VERSION="PROJECT006_WINDOWS_WAKE_BROKER_V1"

class WakeStore:
    def __init__(self,path:str):
        self.path=path; c=sqlite3.connect(path)
        try:
            c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=FULL")
            c.execute("CREATE TABLE IF NOT EXISTS wake(event_id TEXT PRIMARY KEY, observed_at REAL NOT NULL, state TEXT NOT NULL, exit_code INTEGER, detail TEXT)")
            c.commit()
        finally:c.close()
    def capture(self,event_id:str)->bool:
        if not event_id or len(event_id)>2048: raise ValueError("BAD_EVENT_ID")
        with sqlite3.connect(self.path) as c:
            try:c.execute("INSERT INTO wake(event_id,observed_at,state) VALUES(?,?,?)",(event_id,time.time(),"CAPTURED")); return True
            except sqlite3.IntegrityError:return False
    def finish(self,event_id:str,code:int,detail:str=""):
        with sqlite3.connect(self.path) as c:c.execute("UPDATE wake SET state=?,exit_code=?,detail=? WHERE event_id=?",("DONE" if code==0 else "FAILED",code,detail[:2048],event_id))

def event_identity(message:dict[str,Any])->str:
    for path in (("message","messageId"),("messageId",),("id",)):
        cur:Any=message
        for key in path:
            if not isinstance(cur,dict) or key not in cur:cur=None;break
            cur=cur[key]
        if isinstance(cur,str) and cur:return cur
    body=json.dumps(message,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def wake_wsl(*,distro:str|None=None,consumer:str="/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py",timeout_s:int=180)->tuple[int,str]:
    argv=["wsl.exe"]
    if distro: argv += ["-d",distro]
    argv += ["--","python3",consumer,"once"]
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout_s,check=False)
    return p.returncode,(p.stdout+"\n"+p.stderr)[-4000:]

def process_message(store:WakeStore,message:dict[str,Any],wake:Callable[[],tuple[int,str]])->str:
    eid=event_identity(message)
    if not store.capture(eid): return "DUPLICATE"
    try: code,detail=wake()
    except Exception as exc:
        store.finish(eid,111,type(exc).__name__); return "WAKE_FAILED"
    store.finish(eid,code,detail)
    return "WAKE_OK" if code==0 else "WAKE_FAILED"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--state",default=str(Path(os.environ.get("LOCALAPPDATA", "."))/"AuraOS"/"project006-wake.sqlite3"))
    ap.add_argument("--distro")
    ap.add_argument("--stdin-once",action="store_true",help="consume one normalized Pub/Sub/Workspace event JSON from stdin")
    ns=ap.parse_args(); Path(ns.state).parent.mkdir(parents=True,exist_ok=True); store=WakeStore(ns.state)
    if ns.stdin_once:
        msg=json.loads(input()); print(process_message(store,msg,lambda:wake_wsl(distro=ns.distro))); return
    raise SystemExit("A concrete Pub/Sub receiver must feed normalized messages to --stdin-once")
if __name__=="__main__":main()
