import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate", HERE / "tools" / "repository_release_gate.py")
gate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(gate)

def make_project(base: Path):
    (base / "web").mkdir()
    (base / "tools").mkdir()
    (base / ".github" / "workflows").mkdir(parents=True)
    (base / "app.py").write_text("print('ok')\n", encoding="utf-8")
    os.chmod(base / "app.py", 0o755)
    (base / "web" / "index.html").write_text("<h1>ok</h1>\n", encoding="utf-8")
    (base / ".github" / "workflows" / "x.yml").write_text("name: x\n", encoding="utf-8")
    contract = {
        "include_paths": ["app.py", "web", ".github/workflows/x.yml"],
        "executable_paths": ["app.py"],
        "required_safety_locks": {
            "production_write_enabled": False,
            "real_user_data_touched": False,
            "rc1_release_allowed": False,
            "stable_release_allowed": False,
            "builder_v10_allowed": False,
        },
    }
    (base / "RELEASE_TREE_CONTRACT.json").write_text(json.dumps(contract), encoding="utf-8")
    tree = gate.git_write_tree(base, contract)
    status = {
        "release_tree_gate": {"required": True, "expected_tree_sha1": tree},
        "production_write_enabled": False,
        "real_user_data_touched": False,
        "rc1_release_allowed": False,
        "stable_release_allowed": False,
        "builder_v10_allowed": False,
    }
    (base / "PROJEKTSTATUS.json").write_text(json.dumps(status), encoding="utf-8")
    (base / "REPOSITORY_MANIFEST.json").write_text(
        json.dumps(gate.manifest_for(base, contract), sort_keys=True), encoding="utf-8"
    )
    return contract, tree

class RepositoryReleaseGateTests(unittest.TestCase):
    def test_repository_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); _, tree = make_project(root)
            result = gate.verify(root)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["repository_tree_sha1"], tree)

    def test_repository_tamper_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_project(root)
            (root / "app.py").write_text("print('tamper')\n", encoding="utf-8")
            with self.assertRaisesRegex(gate.GateError, "REPOSITORY_MANIFEST_MISMATCH"):
                gate.verify(root)

    def test_status_expected_tree_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_project(root)
            s=json.loads((root/"PROJEKTSTATUS.json").read_text()); s["release_tree_gate"]["expected_tree_sha1"]="0"*40
            (root/"PROJEKTSTATUS.json").write_text(json.dumps(s))
            with self.assertRaisesRegex(gate.GateError, "REPOSITORY_TREE_MISMATCH"):
                gate.verify(root)

    def test_safety_lock_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_project(root)
            s=json.loads((root/"PROJEKTSTATUS.json").read_text()); s["rc1_release_allowed"]=True
            (root/"PROJEKTSTATUS.json").write_text(json.dumps(s))
            with self.assertRaisesRegex(gate.GateError, "SAFETY_LOCK_DRIFT"):
                gate.verify(root)

    def test_missing_required_path_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_project(root)
            (root/"web"/"index.html").unlink()
            with self.assertRaisesRegex(gate.GateError, "REQUIRED_PATH_MISSING|REPOSITORY_MANIFEST_MISMATCH"):
                gate.verify(root)

    def test_symlink_payload_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); make_project(root)
            target=root/"real.html"; target.write_text("x")
            (root/"web"/"index.html").unlink()
            (root/"web"/"index.html").symlink_to(target)
            with self.assertRaisesRegex(gate.GateError, "PAYLOAD_SYMLINK|SYMLINK_COMPONENT"):
                gate.verify(root)

    def test_release_zip_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"p"; root.mkdir(); contract,tree=make_project(root)
            z=Path(d)/"r.zip"
            with zipfile.ZipFile(z,"w") as out:
                for p in gate.payload_files(root,contract):
                    rel=p.relative_to(root).as_posix()
                    info=zipfile.ZipInfo(rel)
                    info.external_attr=((0o100755 if rel=="app.py" else 0o100644)<<16)
                    out.writestr(info,p.read_bytes())
            result=gate.verify(root,z)
            self.assertEqual(result["release_tree_sha1"],tree)

    def test_release_zip_tamper_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"p"; root.mkdir(); contract,_=make_project(root)
            z=Path(d)/"r.zip"
            with zipfile.ZipFile(z,"w") as out:
                for p in gate.payload_files(root,contract):
                    rel=p.relative_to(root).as_posix()
                    out.writestr(rel,b"tamper" if rel=="app.py" else p.read_bytes())
            with self.assertRaisesRegex(gate.GateError, "RELEASE_TREE_MISMATCH"):
                gate.verify(root,z)

    def test_zip_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"p"; root.mkdir(); make_project(root)
            z=Path(d)/"r.zip"
            with zipfile.ZipFile(z,"w") as out:
                out.writestr("../escape","x")
            with self.assertRaisesRegex(gate.GateError, "ZIP_PATH_TRAVERSAL"):
                gate.verify(root,z)

    def test_transient_python_cache_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); contract, tree = make_project(root)
            cache = root / "web" / "__pycache__"
            cache.mkdir()
            (cache / "x.cpython-312.pyc").write_bytes(b"volatile")
            self.assertEqual(gate.git_write_tree(root, contract), tree)
            self.assertNotIn("web/__pycache__/x.cpython-312.pyc", gate.manifest_for(root, contract)["files"])

    def test_manifest_mode_drift_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); make_project(root)
            m=json.loads((root/"REPOSITORY_MANIFEST.json").read_text())
            m["files"]["app.py"]["mode"]="100644"
            (root/"REPOSITORY_MANIFEST.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(gate.GateError, "REPOSITORY_MANIFEST_MISMATCH"):
                gate.verify(root)

if __name__=="__main__":
    unittest.main()
