import importlib.util,tempfile,unittest,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("c",HERE/"candidate_index_collector.py");c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def root(d):
 d=Path(d);(d/".provoware_recovery_search_root").write_text(c.SEARCH_MARKER);return d
class T(unittest.TestCase):
 def test_collect_zip(self):
  with tempfile.TemporaryDirectory() as d:
   r=root(d);(r/"a.zip").write_bytes(b"x");self.assertEqual(c.collect([r])["candidate_count"],1)
 def test_marker_required(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,"SCAN_ROOT_MARKER_INVALID"):c.collect([Path(d)])
 def test_plain_ignored(self):
  with tempfile.TemporaryDirectory() as d:
   r=root(d);(r/"a.txt").write_text("x");self.assertEqual(c.collect([r])["candidate_count"],0)
 def test_symlink_skipped(self):
  with tempfile.TemporaryDirectory() as d:
   r=root(d);(r/"a.zip").write_bytes(b"x");(r/"b.zip").symlink_to(r/"a.zip");self.assertEqual(c.collect([r])["candidate_count"],1)
 def test_no_capabilities(self):
  with tempfile.TemporaryDirectory() as d:
   o=c.collect([root(d)]);self.assertFalse(o["intake_allowed"]);self.assertFalse(o["release_allowed"]);self.assertFalse(o["builder_v10_allowed"])
if __name__=="__main__":unittest.main()
