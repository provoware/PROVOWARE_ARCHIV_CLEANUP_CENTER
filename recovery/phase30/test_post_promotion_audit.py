import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE / "post_promotion_audit.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def write_json(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path

def make_zip(path, text="payload"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("payload.txt", text)

class AuditTests(unittest.TestCase):
    def setup_case(self, d):
        d = Path(d)
        source = d / "source.zip"
        make_zip(source)
        h = m.digest(source)
        size = source.stat().st_size

        vault = d / "vault"
        vault.mkdir()
        marker = vault / "VAULT_MARKER.json"
        marker_obj = {
            "marker_type": "ISOLATED_RC1_PROMOTION_VAULT",
            "purpose": "I015_RC1_PROMOTION_ONLY",
            "vault_root": str(vault),
            "stable_release_allowed": False,
            "rc1_release_allowed": False,
            "builder_v10_allowed": False,
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "safety": dict(m.LOCKS),
        }
        write_json(marker, marker_obj)

        qualification = d / "qualification.json"
        q = {
            "receipt_type": "I015_RC1_RELEASE_QUALIFICATION_RECEIPT",
            "status": "RC1_CANDIDATE_QUALIFIED",
            "next_gate": "RC1_RELEASE_PROMOTION_REQUIRED",
            "candidate_package_path": str(source),
            "candidate_package_sha256": h,
            "candidate_package_size": size,
            "stable_release_allowed": False,
            "rc1_release_allowed": False,
            "builder_v10_allowed": False,
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "safety": dict(m.LOCKS),
        }
        write_json(qualification, q)

        promoted = vault / "I015_RC1.zip"
        promoted.write_bytes(source.read_bytes())
        os.chmod(promoted, 0o444)

        promotion = d / "promotion.json"
        p = {
            "receipt_type": "RC1_PROMOTION_RECEIPT",
            "status": "RC1_PROMOTED_TO_ISOLATED_VAULT",
            "next_gate": "RC1_POST_PROMOTION_AUDIT_REQUIRED",
            "qualification_receipt_sha256": m.digest(qualification),
            "vault_marker_sha256": m.digest(marker),
            "vault_root": str(vault),
            "source_candidate_path": str(source),
            "source_candidate_sha256": h,
            "promoted_candidate_path": str(promoted),
            "promoted_candidate_sha256": h,
            "promoted_candidate_size": size,
            "stable_release_allowed": False,
            "rc1_release_allowed": False,
            "builder_v10_allowed": False,
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "safety": dict(m.LOCKS),
        }
        write_json(promotion, p)
        return qualification, promotion, marker, source, promoted

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            result = m.audit(q,p,marker,source,promoted)
            self.assertEqual(result["status"], "POST_PROMOTION_AUDIT_PASS")
            self.assertTrue(result["source_promoted_byte_equal"])

    def test_release_remains_locked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            result = m.audit(q,p,marker,source,promoted)
            self.assertFalse(result["rc1_release_allowed"])
            self.assertFalse(result["stable_release_allowed"])
            self.assertFalse(result["builder_v10_allowed"])

    def test_qualification_status_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(q.read_text()); obj["status"]="BLOCKED"; write_json(q,obj)
            with self.assertRaisesRegex(ValueError, "QUALIFICATION_STATUS_INVALID"):
                m.audit(q,p,marker,source,promoted)

    def test_promotion_status_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["status"]="BLOCKED"; write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_STATUS_INVALID"):
                m.audit(q,p,marker,source,promoted)

    def test_qualification_hash_binding_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["qualification_receipt_sha256"]="0"*64; write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_QUALIFICATION_HASH_DRIFT"):
                m.audit(q,p,marker,source,promoted)

    def test_marker_hash_binding_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["vault_marker_sha256"]="0"*64; write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_VAULT_MARKER_HASH_DRIFT"):
                m.audit(q,p,marker,source,promoted)

    def test_source_hash_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["source_candidate_sha256"]="0"*64; write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_SOURCE_HASH_DRIFT"):
                m.audit(q,p,marker,source,promoted)

    def test_promoted_hash_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["promoted_candidate_sha256"]="0"*64; write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_TARGET_HASH_DRIFT"):
                m.audit(q,p,marker,source,promoted)

    def test_vault_root_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(p.read_text()); obj["vault_root"]=str(Path(d)/"other"); write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTION_VAULT_ROOT_DRIFT"):
                m.audit(q,p,marker,source,promoted)

    def test_marker_purpose_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            obj=json.loads(marker.read_text()); obj["purpose"]="WRONG"; write_json(marker,obj)
            with self.assertRaisesRegex(ValueError, "VAULT_MARKER_PURPOSE_INVALID"):
                m.audit(q,p,marker,source,promoted)

    def test_source_tamper_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            source.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "SOURCE_HASH_MISMATCH"):
                m.audit(q,p,marker,source,promoted)

    def test_promoted_tamper_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            os.chmod(promoted,0o644); promoted.write_bytes(b"tampered"); os.chmod(promoted,0o444)
            with self.assertRaisesRegex(ValueError, "PROMOTED_HASH_MISMATCH"):
                m.audit(q,p,marker,source,promoted)

    def test_promoted_must_be_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            os.chmod(promoted, 0o644)
            with self.assertRaisesRegex(ValueError, "PROMOTED_WRITABLE"):
                m.audit(q,p,marker,source,promoted)

    def test_invalid_source_zip_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            bad = b"not-a-zip"
            source.write_bytes(bad)
            obj=json.loads(q.read_text()); obj["candidate_package_sha256"]=m.digest(source); obj["candidate_package_size"]=len(bad); write_json(q,obj)
            obj=json.loads(p.read_text())
            obj["qualification_receipt_sha256"]=m.digest(q)
            obj["source_candidate_sha256"]=m.digest(source)
            obj["promoted_candidate_sha256"]=m.digest(source)
            write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "ZIP_INVALID"):
                m.audit(q,p,marker,source,promoted)

    def test_source_symlink_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            link=Path(d)/"source-link.zip"; link.symlink_to(source)
            obj=json.loads(q.read_text()); obj["candidate_package_path"]=str(link); write_json(q,obj)
            obj=json.loads(p.read_text()); obj["qualification_receipt_sha256"]=m.digest(q); obj["source_candidate_path"]=str(link); write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "SOURCE_SYMLINK_COMPONENT"):
                m.audit(q,p,marker,link,promoted)

    def test_promoted_symlink_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            link=promoted.parent/"link.zip"; link.symlink_to(promoted)
            obj=json.loads(p.read_text()); obj["promoted_candidate_path"]=str(link); write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTED_SYMLINK_COMPONENT"):
                m.audit(q,p,marker,source,link)

    def test_promoted_outside_vault_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            outside=Path(d)/"outside.zip"; outside.write_bytes(source.read_bytes()); os.chmod(outside,0o444)
            obj=json.loads(p.read_text()); obj["promoted_candidate_path"]=str(outside); write_json(p,obj)
            with self.assertRaisesRegex(ValueError, "PROMOTED_PATH_OUTSIDE_VAULT"):
                m.audit(q,p,marker,source,outside)

    def test_immutable_output(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            result=m.audit(q,p,marker,source,promoted)
            out,side,h=m.write_immutable(result,Path(d)/"evidence")
            self.assertEqual(out.stat().st_mode & 0o777,0o444)
            self.assertEqual(side.stat().st_mode & 0o777,0o444)

    def test_idempotent_output(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            result=m.audit(q,p,marker,source,promoted); od=Path(d)/"evidence"
            a,_,h1=m.write_immutable(result,od); b,_,h2=m.write_immutable(result,od)
            self.assertEqual(a,b); self.assertEqual(h1,h2)

    def test_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            q,p,marker,source,promoted = self.setup_case(d)
            paths=[q,p,marker,source,promoted]
            before=[x.read_bytes() for x in paths]
            m.audit(q,p,marker,source,promoted)
            self.assertEqual(before,[x.read_bytes() for x in paths])

if __name__=="__main__":
    unittest.main()
