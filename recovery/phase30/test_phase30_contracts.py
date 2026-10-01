import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE / "post_promotion_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class Phase30ContractTests(unittest.TestCase):
    def test_qualification_contract_passes(self):
        value = {
            "receipt_type": "I015_RC1_RELEASE_QUALIFICATION_RECEIPT",
            "status": "RC1_CANDIDATE_QUALIFIED",
            "next_gate": "RC1_RELEASE_PROMOTION_REQUIRED",
            "candidate_package_sha256": "a" * 64,
            "stable_release_allowed": False,
            "rc1_release_allowed": False,
            "builder_v10_allowed": False,
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "safety": dict(audit.LOCKS),
        }
        audit.validate_qualification(value)

    def test_qualification_lock_drift_is_blocked(self):
        value = {
            "receipt_type": "I015_RC1_RELEASE_QUALIFICATION_RECEIPT",
            "status": "RC1_CANDIDATE_QUALIFIED",
            "next_gate": "RC1_RELEASE_PROMOTION_REQUIRED",
            "candidate_package_sha256": "a" * 64,
            "stable_release_allowed": False,
            "rc1_release_allowed": False,
            "builder_v10_allowed": False,
            "production_write_enabled": False,
            "real_user_data_touched": True,
            "safety": dict(audit.LOCKS),
        }
        with self.assertRaisesRegex(ValueError, "QUALIFICATION_LOCK_DRIFT"):
            audit.validate_qualification(value)

    def test_sha256_shape_validation(self):
        self.assertTrue(audit.valid_sha256("0" * 64))
        self.assertFalse(audit.valid_sha256("0" * 63))
        self.assertFalse(audit.valid_sha256("g" * 64))

    def test_release_locks_are_all_false(self):
        self.assertEqual(audit.LOCKS, {
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "builder_v10_allowed": False,
            "rc1_release_allowed": False,
        })

if __name__ == "__main__":
    unittest.main()
