#!/usr/bin/env python3
"""Phase 31A: marker-bound, read-only ZIP candidate index collector."""
from __future__ import annotations
import argparse, hashlib, json, os, stat
from pathlib import Path

SEARCH_MARKER="PROVOWARE_RECOVERY_SEARCH_ROOT_V1"
EVIDENCE_MARKER="PROVOWARE_EVIDENCE_ROOT_V1"

def no_links(path,label):
    p=Path(path).absolute(); cur=Path(p.anchor)
    for part in p.parts[1:]:
        cur/=part
        if cur.is_symlink(): raise ValueError(f"{label}_SYMLINK_COMPONENT")

def verified_root(path):
    p=Path(path).absolute(); no_links(p,"SCAN_ROOT")
    if p.is_symlink() or not p.is_dir(): raise ValueError("SCAN_ROOT_INVALID")
    marker=p/".provoware_recovery_search_root"
    if marker.is_symlink() or not marker.is_file() or marker.read_text().strip()!=SEARCH_MARKER:
        raise ValueError("SCAN_ROOT_MARKER_INVALID")
    return p

def collect(roots):
    prepared=[]; seen=set()
    for raw in roots:
        p=verified_root(raw)
        if str(p) not in seen: seen.add(str(p)); prepared.append(p)
    candidates={}
    for root in sorted(prepared,key=str):
        for cur,dirs,files in os.walk(root,topdown=True,followlinks=False):
            c=Path(cur); dirs[:]=sorted(d for d in dirs if not (c/d).is_symlink())
            for name in sorted(files):
                p=c/name
                if p.is_symlink() or p.suffix.lower()!=".zip": continue
                try:
                    s=p.stat()
                    if not stat.S_ISREG(s.st_mode): continue
                    candidates[str(p.absolute())]={
                        "path":str(p.absolute()),"source_root":str(root),"size":s.st_size,
                        "identity":{"device":s.st_dev,"inode":s.st_ino,"mtime_ns":s.st_mtime_ns}
                    }
                except OSError:
                    continue
    return {"schema_version":1,"index_type":"I015_RECOVERY_CANDIDATE_INDEX",
        "candidate_paths":sorted(candidates),"candidates":[candidates[k] for k in sorted(candidates)],
        "candidate_count":len(candidates),"scan_roots":[str(x) for x in sorted(prepared,key=str)],
        "read_only_collection":True,"candidate_bytes_modified":False,"candidate_bytes_copied":False,
        "intake_allowed":False,"release_allowed":False,"builder_v10_allowed":False,
        "next_gate":"I015_REAL_ARTIFACT_AVAILABILITY"}

def write_index(result,evidence_root,roots):
    d=Path(evidence_root).absolute(); no_links(d,"EVIDENCE_ROOT")
    if d.is_symlink() or not d.is_dir(): raise ValueError("EVIDENCE_ROOT_INVALID")
    marker=d/".provoware_evidence_root"
    if marker.is_symlink() or not marker.is_file() or marker.read_text().strip()!=EVIDENCE_MARKER:
        raise ValueError("EVIDENCE_ROOT_MARKER_INVALID")
    for r in roots:
        try:d.relative_to(verified_root(r))
        except ValueError:continue
        raise ValueError("EVIDENCE_ROOT_INSIDE_SCAN_ROOT")
    raw=(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode()
    h=hashlib.sha256(raw).hexdigest(); p=d/f"RECOVERY_CANDIDATE_INDEX_{h}.json"
    if p.exists():
        if p.is_file() and p.read_bytes()==raw:return p,h
        raise ValueError("INDEX_COLLISION_OR_OVERWRITE")
    p.write_bytes(raw); os.chmod(p,0o444); return p,h

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",action="append",required=True)
    ap.add_argument("--evidence-root",required=True)
    a=ap.parse_args()
    try:
        result=collect(a.root); p,h=write_index(result,a.evidence_root,a.root)
        print(json.dumps({"status":"CANDIDATE_INDEX_READY","candidate_count":result["candidate_count"],"index":str(p),"sha256":h,"next_gate":result["next_gate"]},sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)},sort_keys=True)); return 12
if __name__=="__main__": raise SystemExit(main())
