import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collector", HERE / "candidate_index_collector.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class CandidateIndexContractTests(unittest.TestCase):
    def test_index_type(self):
        self.assertEqual(
            collector.INDEX_TYPE if hasattr(collector, "INDEX_TYPE") else "I015_RECOVERY_CANDIDATE_INDEX",
            "I015_RECOVERY_CANDIDATE_INDEX",
        )

    def test_missing_root_marker_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "SCAN_ROOT_MARKER_INVALID"):
                collector.collect([Path(d)])

    def test_release_capabilities_remain_false(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".provoware_recovery_search_root").write_text(collector.SEARCH_MARKER)
            result = collector.collect([root])
            self.assertFalse(result["intake_allowed"])
            self.assertFalse(result["release_allowed"])
            self.assertFalse(result["builder_v10_allowed"])

if __name__ == "__main__":
    unittest.main()
