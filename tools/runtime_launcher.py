#!/usr/bin/env python3
"""Small project-bound runtime host around the existing PROVOWARE GUI core."""
from __future__ import annotations
import argparse,json,os,threading,urllib.parse,urllib.request,webbrowser,sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/"tools"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import app as gui
import runtime_instance_receipt as receipt

ORIGINAL_STATUS=gui._status

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=True
    daemon_threads=True

def project_status():
    try: data=json.loads((ROOT/"PROJEKTSTATUS.json").read_text(encoding="utf-8"))
    except Exception: data={}
    base=ORIGINAL_STATUS()
    base["version"]=data.get("version",base.get("version"))
    base["status"]=data.get("status",base.get("status"))
    base["project_id"]=receipt.project_id(ROOT)
    return base

gui._status=project_status

def probe(port:int,timeout:float=.35):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/api/status",timeout=timeout) as r:
            obj=json.loads(r.read(256*1024).decode())
    except Exception: return None
    if not isinstance(obj,dict): return None
    expected=project_status()
    for key in ("product","mode","version","project_id"):
        if obj.get(key)!=expected.get(key): return None
    return obj

def receipt_instance():
    try: obj=receipt.load_receipt(ROOT)
    except receipt.RuntimeReceiptError: return None
    if not obj: return None
    ok,_=receipt.validate_receipt(ROOT,project_status()["version"],obj)
    if not ok or probe(int(obj["port"])) is None: return None
    return obj["url"]

def acquire(preferred:int=8765,tries:int=32):
    existing=receipt_instance()
    if existing: return None,existing,"REUSE_RECEIPT"
    preferred=int(preferred)
    if preferred<0 or preferred>65535: raise ValueError("PORT_OUT_OF_RANGE")
    if preferred==0:
        s=LocalServer(("127.0.0.1",0),gui.Handler)
        return s,f"http://127.0.0.1:{s.server_address[1]}/","NEW_EPHEMERAL"
    for port in range(preferred,min(65535,preferred+max(0,int(tries)))+1):
        try:
            s=LocalServer(("127.0.0.1",port),gui.Handler)
            return s,f"http://127.0.0.1:{port}/","NEW_PREFERRED" if port==preferred else "NEW_FALLBACK"
        except OSError as exc:
            if exc.errno not in (98,48,10048): raise
            if port==preferred and probe(port) is not None:
                return None,f"http://127.0.0.1:{port}/","REUSE_EXISTING"
    s=LocalServer(("127.0.0.1",0),gui.Handler)
    return s,f"http://127.0.0.1:{s.server_address[1]}/","NEW_EPHEMERAL_AFTER_CONFLICT"

def selfcheck():
    base=gui.selfcheck()
    errors=list(base.get("errors",[]))
    if not (ROOT/"tools"/"runtime_instance_receipt.py").is_file(): errors.append("RUNTIME_RECEIPT_MODULE_MISSING")
    return {"status":"PASS" if not errors else "FAIL","errors":errors,"version":project_status()["version"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--port",type=int,default=8765)
    ap.add_argument("--no-browser",action="store_true")
    ap.add_argument("--selfcheck",action="store_true")
    a=ap.parse_args()
    if a.selfcheck:
        result=selfcheck();print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0 if result["status"]=="PASS" else 12
    server,url,state=acquire(a.port)
    if state in ("REUSE_RECEIPT","REUSE_EXISTING"):
        print(f"PROVOWARE GUI bereits aktiv: {url}",flush=True)
        if state=="REUSE_RECEIPT": print("Single-Instance Runtime Receipt: PASS",flush=True)
        if not a.no_browser: threading.Timer(.1,lambda:webbrowser.open(url)).start()
        return 0
    port=int(urllib.parse.urlparse(url).port or 0)
    if a.port and port!=a.port: print(f"Hinweis: Port {a.port} belegt; freier Port {port}.",flush=True)
    obj=receipt.build_receipt(ROOT,project_status()["version"],os.getpid(),port,url)
    path=receipt.write_receipt(ROOT,obj)
    print(f"PROVOWARE GUI: {url}",flush=True);print(f"Runtime Receipt: {path}",flush=True)
    if not a.no_browser: threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:
        assert server is not None
        server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        receipt.remove_receipt_if_owner(ROOT,os.getpid(),port)
        if server is not None: server.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())
