import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rr", ROOT / "tools" / "runtime_instance_receipt.py")
rr = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(rr)

class RuntimeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name) / "runtime"
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        self.old = os.environ.get("XDG_RUNTIME_DIR")
        os.environ["XDG_RUNTIME_DIR"] = str(self.runtime)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("XDG_RUNTIME_DIR", None)
        else:
            os.environ["XDG_RUNTIME_DIR"] = self.old

    def test_project_id_is_path_bound(self):
        other = Path(self.tmp.name) / "other"; other.mkdir()
        self.assertNotEqual(rr.project_id(self.project), rr.project_id(other))

    def test_write_load_validate_roundtrip(self):
        receipt = rr.build_receipt(self.project, "1.2.3", os.getpid(), 8765, "http://127.0.0.1:8765/")
        path = rr.write_receipt(self.project, receipt)
        loaded = rr.load_receipt(self.project)
        ok, reason = rr.validate_receipt(self.project, "1.2.3", loaded)
        self.assertTrue(ok, reason)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_wrong_version_is_invalid(self):
        receipt = rr.build_receipt(self.project, "1.2.3", os.getpid(), 8765, "http://127.0.0.1:8765/")
        rr.write_receipt(self.project, receipt)
        ok, reason = rr.validate_receipt(self.project, "9.9.9", rr.load_receipt(self.project))
        self.assertFalse(ok)
        self.assertIn("version", reason)

    def test_remove_only_owner(self):
        receipt = rr.build_receipt(self.project, "1.2.3", os.getpid(), 8765, "http://127.0.0.1:8765/")
        path = rr.write_receipt(self.project, receipt)
        self.assertFalse(rr.remove_receipt_if_owner(self.project, os.getpid(), 9999))
        self.assertTrue(path.exists())
        self.assertTrue(rr.remove_receipt_if_owner(self.project, os.getpid(), 8765))
        self.assertFalse(path.exists())

    def test_runtime_symlink_component_blocked(self):
        target = Path(self.tmp.name) / "real"; target.mkdir()
        self.runtime.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(rr.RuntimeReceiptError, "RUNTIME_DIR_SYMLINK_COMPONENT"):
            rr.ensure_runtime_dir()

if __name__ == "__main__":
    unittest.main()
