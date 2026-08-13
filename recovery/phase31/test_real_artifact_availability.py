import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("g",HERE/"real_artifact_availability.py"); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def z(p,t):
 with zipfile.ZipFile(p,"w") as f:f.writestr("x.txt",t)
 return g.sha256_file(p)
def snap(p,targets):
 p.write_text(json.dumps({"snapshot_type":"I015_REAL_ARTIFACT_GITHUB_AVAILABILITY","repository":"provoware/PROVOWARE_ARCHIV_CLEANUP_CENTER","status":"NO_CANONICAL_BYTES_FOUND","canonical_targets":{k:v["sha256"] for k,v in targets.items()}}));return p
def idx(p,paths):
 p.write_text(json.dumps({"index_type":"I015_RECOVERY_CANDIDATE_INDEX","candidate_paths":[str(x) for x in paths]}));return p

class T(unittest.TestCase):
 def case(self,d):
  d=Path(d);a=d/"a.zip";b=d/"b.zip";z(a,"a");z(b,"b")
  targets={"I014":{"filename":"a","sha256":g.sha256_file(a)},"BUILDER_V9":{"filename":"b","sha256":g.sha256_file(b)}}
  return d,a,b,targets
 def test_handoff(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);old=g.TARGETS;g.TARGETS=t
   try:self.assertEqual(g.evaluate(snap(d/"s",t),idx(d/"i",[a,b]))["status"],"VERIFIED_INTAKE_HANDOFF_READY")
   finally:g.TARGETS=old
 def test_missing(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);old=g.TARGETS;g.TARGETS=t
   try:self.assertEqual(g.evaluate(snap(d/"s",t),idx(d/"i",[]))["status"],"RECOVERY_ARTIFACTS_STILL_MISSING")
   finally:g.TARGETS=old
 def test_partial(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);old=g.TARGETS;g.TARGETS=t
   try:self.assertEqual(g.evaluate(snap(d/"s",t),idx(d/"i",[a]))["status"],"RECOVERY_ARTIFACTS_PARTIAL")
   finally:g.TARGETS=old
 def test_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);c=d/"c.zip";c.write_bytes(a.read_bytes());old=g.TARGETS;g.TARGETS=t
   try:self.assertEqual(g.evaluate(snap(d/"s",t),idx(d/"i",[a,b,c]))["status"],"RECOVERY_ARTIFACTS_MULTIPLE_MATCHES")
   finally:g.TARGETS=old
 def test_symlink_candidate(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);l=d/"l.zip";l.symlink_to(a);old=g.TARGETS;g.TARGETS=t
   try:self.assertTrue(g.evaluate(snap(d/"s",t),idx(d/"i",[l]))["qualification_errors"])
   finally:g.TARGETS=old
 def test_inputs_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);old=g.TARGETS;g.TARGETS=t;s=snap(d/"s",t);i=idx(d/"i",[a,b]);before=(a.read_bytes(),b.read_bytes())
   try:g.evaluate(s,i);self.assertEqual(before,(a.read_bytes(),b.read_bytes()))
   finally:g.TARGETS=old
 def test_snapshot_drift(self):
  with tempfile.TemporaryDirectory() as d:
   d,a,b,t=self.case(d);s=snap(d/"s",t);o=json.loads(s.read_text());o["canonical_targets"]["I014"]="0"*64;s.write_text(json.dumps(o))
   with self.assertRaisesRegex(ValueError,"GITHUB_SNAPSHOT_TARGET_DRIFT"):g.load_snapshot(s)
 def test_evidence_marker(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);r=d/"ev";r.mkdir()
   with self.assertRaisesRegex(ValueError,"EVIDENCE_ROOT_MARKER_INVALID"):g.write_evidence({"x":1},r)
 def test_locks(self):
  self.assertTrue(all(v is False for v in g.LOCKS.values()))
if __name__=="__main__":unittest.main()
