from __future__ import annotations
import json, os, sys, time
from pathlib import Path

def ident(pid):
    text=Path(f"/proc/{pid}/stat").read_text(); r=text.rfind(") "); tail=text[r+2:].split()
    return {"pid": pid, "starttime": int(tail[19])}

def forever():
    while True: time.sleep(60)

def escaped_endpoint(write_fd, fanout=0):
    os.setsid()
    if fanout:
        children=[]
        for _ in range(fanout):
            p=os.fork()
            if p==0:
                os.close(write_fd)
                forever()
            children.append(p)
        msg={"root":ident(os.getpid()), "leaves":[ident(p) for p in children]}
        os.write(write_fd,(json.dumps(msg)+"\n").encode()); os.close(write_fd)
        forever()
    os.write(write_fd,(json.dumps({"root":ident(os.getpid()),"leaves":[]})+"\n").encode()); os.close(write_fd)
    forever()

def doublefork_endpoint(write_fd):
    os.setsid()
    p=os.fork()
    if p==0:
        # Grandchild remains in escaped session; intermediate exits after publishing endpoint.
        os.write(write_fd,(json.dumps({"root":ident(os.getpid()),"leaves":[]})+"\n").encode())
        os.close(write_fd); forever()
    os.close(write_fd)
    os._exit(0)

def main():
    mode=sys.argv[1]
    r,w=os.pipe()
    p=os.fork()
    if p==0:
        os.close(r)
        if mode=="escaped": escaped_endpoint(w)
        elif mode=="doublefork": doublefork_endpoint(w)
        elif mode=="fanout8": escaped_endpoint(w,8)
        else: os._exit(64)
    os.close(w)
    with os.fdopen(r,"r") as f:
        msg=json.loads(f.readline())
    # Reap intermediate if it deliberately exited; harmless WNOHANG otherwise.
    try: os.waitpid(p, os.WNOHANG)
    except ChildProcessError: pass
    identities=[msg["root"], *msg.get("leaves",[])]
    print(json.dumps({"state":"READY","mode":mode,"identities":identities},sort_keys=True),flush=True)
    forever()
if __name__=="__main__": main()
