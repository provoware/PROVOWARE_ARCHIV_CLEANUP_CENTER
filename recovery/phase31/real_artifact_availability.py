#!/usr/bin/env python3
"""I015 Phase 31: explicit-candidate real artifact availability gate."""
from __future__ import annotations
import argparse, hashlib, json, os, stat, zipfile
from pathlib import Path, PurePosixPath

TARGETS={
 "I014":{"filename":"PROVOWARE_ARCHIV_CLEANUP_CENTER_I014.zip","sha256":"72393a4ed445a765a7542d7a28c42171dbae66ed927dd0207c31f05a2a159899"},
 "BUILDER_V9":{"filename":"PROVOWARE_ARCHIV_CLEANUP_CENTER_I015_RC1_BUILDER_V9_MIGRATION_FIXED.zip","sha256":"29ad1a4a2ed8fcc8f1eff5c6bb36ba37425352caab8ecb99c3a992cdeac8780c"},
}
LOCKS={"production_write_enabled":False,"real_user_data_touched":False,"builder_v10_allowed":False,"rc1_release_allowed":False,"stable_release_allowed":False}

def sha256_file(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()

def no_links(p,label):
 p=Path(p).absolute(); cur=Path(p.anchor)
 for part in p.parts[1:]:
  cur/=part
  if cur.is_symlink(): raise ValueError(f"{label}_SYMLINK_COMPONENT")

def regular_identity(p,label):
 p=Path(p); no_links(p,label)
 if p.is_symlink(): raise ValueError(f"{label}_SYMLINK")
 s=p.stat()
 if not stat.S_ISREG(s.st_mode): raise ValueError(f"{label}_NOT_REGULAR")
 return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns

def load_json(p,label):
 a=regular_identity(p,label); raw=Path(p).read_bytes(); b=regular_identity(p,label)
 if a!=b: raise ValueError(f"{label}_DRIFT")
 try: return json.loads(raw.decode()),hashlib.sha256(raw).hexdigest()
 except Exception as e: raise ValueError(f"{label}_INVALID_JSON") from e

def validate_zip(p):
 try:
  with zipfile.ZipFile(p) as z:
   for i in z.infolist():
    q=PurePosixPath(i.filename)
    if q.is_absolute() or ".." in q.parts: raise ValueError("ZIP_PATH_TRAVERSAL")
    if ((i.external_attr>>16)&0o170000)==stat.S_IFLNK: raise ValueError("ZIP_SYMLINK")
   if z.testzip() is not None: raise ValueError("ZIP_CRC_ERROR")
 except zipfile.BadZipFile as e: raise ValueError("ZIP_INVALID") from e

def load_snapshot(p):
 o,h=load_json(p,"GITHUB_SNAPSHOT")
 if o.get("snapshot_type")!="I015_REAL_ARTIFACT_GITHUB_AVAILABILITY": raise ValueError("GITHUB_SNAPSHOT_TYPE_INVALID")
 if o.get("repository")!="provoware/PROVOWARE_ARCHIV_CLEANUP_CENTER": raise ValueError("GITHUB_SNAPSHOT_REPOSITORY_DRIFT")
 if o.get("canonical_targets")!={k:v["sha256"] for k,v in TARGETS.items()}: raise ValueError("GITHUB_SNAPSHOT_TARGET_DRIFT")
 return o,h

def load_index(p):
 o,h=load_json(p,"CANDIDATE_INDEX")
 if o.get("index_type")!="I015_RECOVERY_CANDIDATE_INDEX": raise ValueError("CANDIDATE_INDEX_TYPE_INVALID")
 paths=o.get("candidate_paths")
 if not isinstance(paths,list) or any(not isinstance(x,str) for x in paths): raise ValueError("CANDIDATE_INDEX_PATHS_INVALID")
 return o,h

def qualify(path):
 p=Path(path).absolute(); a=regular_identity(p,"CANDIDATE"); h=sha256_file(p); b=regular_identity(p,"CANDIDATE")
 if a!=b: raise ValueError("CANDIDATE_DRIFT_DURING_HASH")
 key=next((k for k,v in TARGETS.items() if h==v["sha256"]),None)
 if not key: return None
 validate_zip(p)
 return key,{"path":str(p),"sha256":h,"size":b[2],"identity":{"device":b[0],"inode":b[1],"mtime_ns":b[3]},"zip_integrity":"PASS"}

def evaluate(snapshot_path,index_path):
 snap,snap_h=load_snapshot(snapshot_path); idx,idx_h=load_index(index_path)
 matches={k:[] for k in TARGETS}; errors=[]
 for raw in sorted(set(idx["candidate_paths"])):
  try:
   rec=qualify(raw)
   if rec: matches[rec[0]].append(rec[1])
  except (OSError,ValueError) as e: errors.append({"path":raw,"reason":str(e)})
 counts={k:len(v) for k,v in matches.items()}
 if all(v==1 for v in counts.values()): status,nxt="VERIFIED_INTAKE_HANDOFF_READY","VERIFIED_ARTIFACT_INTAKE_REQUIRED"
 elif any(v>1 for v in counts.values()): status,nxt="RECOVERY_ARTIFACTS_MULTIPLE_MATCHES","MANUAL_MATCH_DISAMBIGUATION_REQUIRED"
 elif any(v==1 for v in counts.values()): status,nxt="RECOVERY_ARTIFACTS_PARTIAL","CANDIDATE_DISCOVERY_REQUIRED"
 else: status,nxt="RECOVERY_ARTIFACTS_STILL_MISSING","CANDIDATE_DISCOVERY_REQUIRED"
 return {"schema_version":1,"evidence_type":"I015_REAL_ARTIFACT_AVAILABILITY","status":status,"canonical_targets":TARGETS,
  "github_snapshot_sha256":snap_h,"github_snapshot_status":snap.get("status"),"candidate_index_sha256":idx_h,
  "candidate_count":len(set(idx["candidate_paths"])),"match_counts":counts,"matches":matches,
  "selected_for_handoff":{k:(v[0] if len(v)==1 else None) for k,v in matches.items()},"qualification_errors":errors,
  "candidate_bytes_modified":False,"candidate_bytes_copied":False,"next_gate":nxt,**LOCKS,"safety":dict(LOCKS)}

def write_evidence(result,out_dir):
 d=Path(out_dir).absolute(); no_links(d,"EVIDENCE_ROOT")
 if not d.is_dir(): raise ValueError("EVIDENCE_ROOT_INVALID")
 marker=d/".provoware_evidence_root"
 if marker.is_symlink() or not marker.is_file() or marker.read_text().strip()!="PROVOWARE_EVIDENCE_ROOT_V1": raise ValueError("EVIDENCE_ROOT_MARKER_INVALID")
 raw=(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode(); h=hashlib.sha256(raw).hexdigest()
 p=d/f"REAL_ARTIFACT_AVAILABILITY_{h}.json"; s=p.with_suffix(p.suffix+".sha256"); sr=f"{h}  {p.name}\n".encode()
 if p.exists() or s.exists():
  if p.is_file() and s.is_file() and p.read_bytes()==raw and s.read_bytes()==sr: return p,s,h
  raise ValueError("EVIDENCE_COLLISION_OR_OVERWRITE")
 p.write_bytes(raw); s.write_bytes(sr); os.chmod(p,0o444); os.chmod(s,0o444); return p,s,h

def main():
 a=argparse.ArgumentParser(); a.add_argument("--github-snapshot",required=True); a.add_argument("--candidate-index",required=True); a.add_argument("--evidence-root",required=True); x=a.parse_args()
 try:
  r=evaluate(Path(x.github_snapshot),Path(x.candidate_index)); p,_,h=write_evidence(r,Path(x.evidence_root))
  print(json.dumps({"status":r["status"],"next_gate":r["next_gate"],"evidence":str(p),"sha256":h},sort_keys=True))
  return 0 if r["status"]=="VERIFIED_INTAKE_HANDOFF_READY" else 10
 except Exception as e:
  print(json.dumps({"status":"BLOCKED","reason":str(e)},sort_keys=True)); return 12
if __name__=="__main__": raise SystemExit(main())
