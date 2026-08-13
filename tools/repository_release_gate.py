#!/usr/bin/env python3
"""PROVOWARE Repository↔Release Gate.

Builds a canonical Git tree from the explicit release payload using
`git write-tree` and compares it to PROJEKTSTATUS.json. Optionally verifies
a release ZIP against the same canonical tree. Fail-closed by design.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, stat, subprocess, tempfile, zipfile
from pathlib import Path, PurePosixPath

LOCK_KEYS = (
    "production_write_enabled",
    "real_user_data_touched",
    "rc1_release_allowed",
    "stable_release_allowed",
    "builder_v10_allowed",
)

class GateError(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024 * 1024), b""):
            h.update(c)
    return h.hexdigest()

def load_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateError(f"INVALID_JSON:{path}") from exc
    if not isinstance(obj, dict):
        raise GateError(f"JSON_OBJECT_REQUIRED:{path}")
    return obj

def safe_rel(value: str) -> Path:
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or value in ("", "."):
        raise GateError(f"UNSAFE_RELATIVE_PATH:{value}")
    return Path(*p.parts)

def no_symlink_components(root: Path, rel: Path) -> None:
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise GateError(f"SYMLINK_COMPONENT:{rel}")

def payload_files(root: Path, contract: dict) -> list[Path]:
    root = root.resolve()
    result: dict[str, Path] = {}
    for raw in contract.get("include_paths", []):
        rel = safe_rel(raw)
        no_symlink_components(root, rel)
        p = root / rel
        if not p.exists():
            raise GateError(f"REQUIRED_PATH_MISSING:{raw}")
        if p.is_symlink():
            raise GateError(f"REQUIRED_PATH_SYMLINK:{raw}")
        if p.is_file():
            result[rel.as_posix()] = p
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                child_rel = child.relative_to(root)
                if "__pycache__" in child_rel.parts or child.suffix in {".pyc", ".pyo"}:
                    continue
                if child.is_symlink():
                    raise GateError(f"PAYLOAD_SYMLINK:{child_rel.as_posix()}")
                if child.is_file():
                    result[child_rel.as_posix()] = child
        else:
            raise GateError(f"UNSUPPORTED_REQUIRED_PATH:{raw}")
    if not result:
        raise GateError("EMPTY_RELEASE_PAYLOAD")
    return [result[k] for k in sorted(result)]

def expected_mode(rel: str, contract: dict) -> str:
    executable = set(contract.get("executable_paths", []))
    return "100755" if rel in executable else "100644"

def manifest_for(root: Path, contract: dict) -> dict:
    files = {}
    for p in payload_files(root, contract):
        rel = p.relative_to(root.resolve()).as_posix()
        files[rel] = {
            "sha256": sha256_file(p),
            "size": p.stat().st_size,
            "mode": expected_mode(rel, contract),
        }
    return {"schema_version": 1, "algorithm": "sha256+git-mode", "files": files}

def verify_repository_manifest(root: Path, contract: dict, manifest_path: Path) -> dict:
    expected = manifest_for(root, contract)
    actual = load_json(manifest_path)
    if actual != expected:
        exp = set(expected["files"])
        act = set(actual.get("files", {})) if isinstance(actual.get("files"), dict) else set()
        missing = sorted(exp - act)
        extra = sorted(act - exp)
        changed = []
        for rel in sorted(exp & act):
            if expected["files"][rel] != actual["files"][rel]:
                changed.append(rel)
        raise GateError(
            "REPOSITORY_MANIFEST_MISMATCH:"
            + json.dumps({"missing": missing, "extra": extra, "changed": changed}, sort_keys=True)
        )
    return expected

def git_write_tree(root: Path, contract: dict) -> str:
    root = root.resolve()
    with tempfile.TemporaryDirectory(prefix="provoware_release_tree_") as td:
        stage = Path(td)
        for src in payload_files(root, contract):
            rel = src.relative_to(root)
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755 if expected_mode(rel.as_posix(), contract) == "100755" else 0o644)
        subprocess.run(["git", "init", "-q"], cwd=stage, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=stage, check=True)
        subprocess.run(["git", "config", "core.filemode", "true"], cwd=stage, check=True)
        subprocess.run(["git", "add", "-A"], cwd=stage, check=True)
        return subprocess.check_output(["git", "write-tree"], cwd=stage, text=True).strip()

def extract_release_zip(zip_path: Path, contract: dict, target: Path) -> None:
    allowed_exec = set(contract.get("executable_paths", []))
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            rel = PurePosixPath(info.filename)
            if rel.is_absolute() or ".." in rel.parts:
                raise GateError(f"ZIP_PATH_TRAVERSAL:{info.filename}")
            mode_type = (info.external_attr >> 16) & 0o170000
            if mode_type == stat.S_IFLNK:
                raise GateError(f"ZIP_SYMLINK:{info.filename}")
            if info.is_dir():
                continue
            out = target.joinpath(*rel.parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            rel_s = rel.as_posix()
            os.chmod(out, 0o755 if rel_s in allowed_exec else 0o644)
        bad = z.testzip()
        if bad:
            raise GateError(f"ZIP_CRC_ERROR:{bad}")

def verify_locks(status: dict, contract: dict) -> None:
    required = contract.get("required_safety_locks", {})
    for key in LOCK_KEYS:
        if required.get(key) is not False or status.get(key) is not False:
            raise GateError(f"SAFETY_LOCK_DRIFT:{key}")

def verify(root: Path, release_zip: Path | None = None) -> dict:
    root = root.resolve()
    contract = load_json(root / "RELEASE_TREE_CONTRACT.json")
    status = load_json(root / "PROJEKTSTATUS.json")
    verify_locks(status, contract)
    verify_repository_manifest(root, contract, root / "REPOSITORY_MANIFEST.json")

    gate = status.get("release_tree_gate")
    if not isinstance(gate, dict) or gate.get("required") is not True:
        raise GateError("RELEASE_TREE_GATE_NOT_REQUIRED")
    expected = gate.get("expected_tree_sha1")
    if not isinstance(expected, str) or len(expected) != 40:
        raise GateError("EXPECTED_TREE_SHA1_INVALID")

    repo_tree = git_write_tree(root, contract)
    if repo_tree != expected:
        raise GateError(f"REPOSITORY_TREE_MISMATCH:expected={expected}:actual={repo_tree}")

    release_tree = None
    if release_zip is not None:
        with tempfile.TemporaryDirectory(prefix="provoware_release_zip_") as td:
            extracted = Path(td)
            extract_release_zip(release_zip, contract, extracted)
            release_tree = git_write_tree(extracted, contract)
            if release_tree != expected:
                raise GateError(f"RELEASE_TREE_MISMATCH:expected={expected}:actual={release_tree}")
            if release_tree != repo_tree:
                raise GateError(f"REPOSITORY_RELEASE_TREE_DIVERGENCE:repo={repo_tree}:release={release_tree}")

    return {
        "schema_version": 1,
        "gate": "PROVOWARE_REPOSITORY_RELEASE_GATE",
        "status": "PASS",
        "expected_tree_sha1": expected,
        "repository_tree_sha1": repo_tree,
        "release_tree_sha1": release_tree,
        "manifest": "PASS",
        "safety_locks": "PASS",
        "release_promotion_allowed_by_this_gate": True,
        "production_write_enabled": False,
        "real_user_data_touched": False,
        "rc1_release_allowed": False,
        "stable_release_allowed": False,
        "builder_v10_allowed": False,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--release-zip")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--receipt")
    args = ap.parse_args()
    try:
        result = verify(Path(args.root), Path(args.release_zip) if args.release_zip else None)
        if args.receipt:
            out = Path(args.receipt)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True) if args.json else f"REPOSITORY_RELEASE_GATE: PASS {result['repository_tree_sha1']}")
        return 0
    except (GateError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        result = {"gate": "PROVOWARE_REPOSITORY_RELEASE_GATE", "status": "BLOCKED", "reason": str(exc)}
        print(json.dumps(result, sort_keys=True) if args.json else f"REPOSITORY_RELEASE_GATE: BLOCKED {exc}")
        return 12

if __name__ == "__main__":
    raise SystemExit(main())
