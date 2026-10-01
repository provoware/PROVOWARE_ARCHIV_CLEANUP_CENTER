#!/usr/bin/env python3
"""I015 Phase 30: independent RC1 post-promotion audit and vault integrity proof.

Read-only against source candidate, promoted candidate, vault marker and receipts.
Writes only immutable audit evidence to an explicitly supplied evidence directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

LOCKS = {
    "production_write_enabled": False,
    "real_user_data_touched": False,
    "builder_v10_allowed": False,
    "rc1_release_allowed": False,
}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def valid_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)

def assert_no_symlink_components(path: Path, label: str) -> None:
    absolute = path if path.is_absolute() else path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label}_SYMLINK_COMPONENT")

def load_regular_json(path: Path, label: str):
    assert_no_symlink_components(path, label)
    if path.is_symlink():
        raise ValueError(f"{label}_SYMLINK")
    st1 = path.stat()
    if not stat.S_ISREG(st1.st_mode):
        raise ValueError(f"{label}_NOT_REGULAR")
    raw = path.read_bytes()
    st2 = path.stat()
    i1 = (st1.st_dev, st1.st_ino, st1.st_size, st1.st_mtime_ns)
    i2 = (st2.st_dev, st2.st_ino, st2.st_size, st2.st_mtime_ns)
    if i1 != i2:
        raise ValueError(f"{label}_DRIFT")
    try:
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        raise ValueError(f"{label}_INVALID_JSON") from exc

def safe_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                pp = PurePosixPath(info.filename)
                if pp.is_absolute() or ".." in pp.parts:
                    raise ValueError("ZIP_PATH_TRAVERSAL")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ValueError("ZIP_SYMLINK")
            bad = z.testzip()
            if bad:
                raise ValueError("ZIP_CRC_ERROR")
    except zipfile.BadZipFile as exc:
        raise ValueError("ZIP_INVALID") from exc

def verify_file(path: Path, label: str, expected_sha: str, expected_size=None, require_readonly=False):
    assert_no_symlink_components(path, label)
    if path.is_symlink():
        raise ValueError(f"{label}_SYMLINK")
    st1 = path.stat()
    if not stat.S_ISREG(st1.st_mode):
        raise ValueError(f"{label}_NOT_REGULAR")
    i1 = (st1.st_dev, st1.st_ino, st1.st_size, st1.st_mtime_ns)
    h = digest(path)
    st2 = path.stat()
    i2 = (st2.st_dev, st2.st_ino, st2.st_size, st2.st_mtime_ns)
    if i1 != i2:
        raise ValueError(f"{label}_DRIFT_DURING_HASH")
    if h != expected_sha:
        raise ValueError(f"{label}_HASH_MISMATCH")
    if expected_size is not None and st2.st_size != expected_size:
        raise ValueError(f"{label}_SIZE_MISMATCH")
    if require_readonly and (st2.st_mode & 0o222):
        raise ValueError(f"{label}_WRITABLE")
    safe_zip(path)
    return {
        "sha256": h,
        "size": st2.st_size,
        "identity": {
            "device": st2.st_dev,
            "inode": st2.st_ino,
            "mtime_ns": st2.st_mtime_ns,
        },
        "mode": stat.S_IMODE(st2.st_mode),
    }

def bytes_equal(a: Path, b: Path) -> bool:
    if a.stat().st_size != b.stat().st_size:
        return False
    with a.open("rb") as fa, b.open("rb") as fb:
        while True:
            aa = fa.read(1024 * 1024)
            bb = fb.read(1024 * 1024)
            if aa != bb:
                return False
            if not aa:
                return True

def validate_qualification(q: dict):
    if q.get("receipt_type") != "I015_RC1_RELEASE_QUALIFICATION_RECEIPT":
        raise ValueError("QUALIFICATION_TYPE_INVALID")
    if q.get("status") != "RC1_CANDIDATE_QUALIFIED":
        raise ValueError("QUALIFICATION_STATUS_INVALID")
    if q.get("next_gate") != "RC1_RELEASE_PROMOTION_REQUIRED":
        raise ValueError("QUALIFICATION_NEXT_GATE_INVALID")
    if q.get("safety") != LOCKS:
        raise ValueError("QUALIFICATION_SAFETY_LOCK_DRIFT")
    for key in (
        "stable_release_allowed",
        "rc1_release_allowed",
        "builder_v10_allowed",
        "production_write_enabled",
        "real_user_data_touched",
    ):
        if q.get(key) is not False:
            raise ValueError("QUALIFICATION_LOCK_DRIFT")
    if not valid_sha256(q.get("candidate_package_sha256")):
        raise ValueError("QUALIFICATION_CANDIDATE_HASH_INVALID")

def validate_vault_marker(marker: dict, marker_path: Path):
    if marker.get("marker_type") != "ISOLATED_RC1_PROMOTION_VAULT":
        raise ValueError("VAULT_MARKER_TYPE_INVALID")
    if marker.get("purpose") != "I015_RC1_PROMOTION_ONLY":
        raise ValueError("VAULT_MARKER_PURPOSE_INVALID")
    if marker.get("safety") != LOCKS:
        raise ValueError("VAULT_MARKER_SAFETY_LOCK_DRIFT")
    for key in (
        "stable_release_allowed",
        "rc1_release_allowed",
        "builder_v10_allowed",
        "production_write_enabled",
        "real_user_data_touched",
    ):
        if marker.get(key) is not False:
            raise ValueError("VAULT_MARKER_LOCK_DRIFT")
    root = Path(marker.get("vault_root", ""))
    if not root.is_absolute():
        raise ValueError("VAULT_ROOT_NOT_ABSOLUTE")
    if marker_path.parent != root:
        raise ValueError("VAULT_MARKER_PARENT_DRIFT")
    assert_no_symlink_components(root, "VAULT_ROOT")
    if root.is_symlink() or not root.is_dir():
        raise ValueError("VAULT_ROOT_INVALID")
    return root

def validate_promotion(p: dict, qualification_hash: str, marker_hash: str, candidate_hash: str, vault_root: Path):
    if p.get("receipt_type") != "RC1_PROMOTION_RECEIPT":
        raise ValueError("PROMOTION_TYPE_INVALID")
    if p.get("status") != "RC1_PROMOTED_TO_ISOLATED_VAULT":
        raise ValueError("PROMOTION_STATUS_INVALID")
    if p.get("next_gate") != "RC1_POST_PROMOTION_AUDIT_REQUIRED":
        raise ValueError("PROMOTION_NEXT_GATE_INVALID")
    if p.get("qualification_receipt_sha256") != qualification_hash:
        raise ValueError("PROMOTION_QUALIFICATION_HASH_DRIFT")
    if p.get("vault_marker_sha256") != marker_hash:
        raise ValueError("PROMOTION_VAULT_MARKER_HASH_DRIFT")
    if p.get("source_candidate_sha256") != candidate_hash:
        raise ValueError("PROMOTION_SOURCE_HASH_DRIFT")
    if p.get("promoted_candidate_sha256") != candidate_hash:
        raise ValueError("PROMOTION_TARGET_HASH_DRIFT")
    if p.get("vault_root") != str(vault_root):
        raise ValueError("PROMOTION_VAULT_ROOT_DRIFT")
    if p.get("safety") != LOCKS:
        raise ValueError("PROMOTION_SAFETY_LOCK_DRIFT")
    for key in (
        "stable_release_allowed",
        "rc1_release_allowed",
        "builder_v10_allowed",
        "production_write_enabled",
        "real_user_data_touched",
    ):
        if p.get(key) is not False:
            raise ValueError("PROMOTION_LOCK_DRIFT")

def audit(qualification_path: Path, promotion_path: Path, marker_path: Path, source_path: Path, promoted_path: Path):
    qualification, qh = load_regular_json(qualification_path, "QUALIFICATION")
    validate_qualification(qualification)
    marker, mh = load_regular_json(marker_path, "VAULT_MARKER")
    vault_root = validate_vault_marker(marker, marker_path)
    promotion, ph = load_regular_json(promotion_path, "PROMOTION")

    candidate_hash = qualification["candidate_package_sha256"]
    validate_promotion(promotion, qh, mh, candidate_hash, vault_root)

    if Path(qualification.get("candidate_package_path", "")) != source_path:
        raise ValueError("SOURCE_PATH_QUALIFICATION_DRIFT")
    if Path(promotion.get("source_candidate_path", "")) != source_path:
        raise ValueError("SOURCE_PATH_PROMOTION_DRIFT")
    if Path(promotion.get("promoted_candidate_path", "")) != promoted_path:
        raise ValueError("PROMOTED_PATH_PROMOTION_DRIFT")

    try:
        promoted_path.relative_to(vault_root)
    except ValueError as exc:
        raise ValueError("PROMOTED_PATH_OUTSIDE_VAULT") from exc

    expected_size = qualification.get("candidate_package_size")
    source = verify_file(source_path, "SOURCE", candidate_hash, expected_size=expected_size)
    promoted = verify_file(
        promoted_path,
        "PROMOTED",
        candidate_hash,
        expected_size=expected_size,
        require_readonly=True,
    )

    if promotion.get("promoted_candidate_size") not in (None, promoted["size"]):
        raise ValueError("PROMOTION_TARGET_SIZE_DRIFT")
    if not bytes_equal(source_path, promoted_path):
        raise ValueError("SOURCE_PROMOTED_BYTE_MISMATCH")

    return {
        "schema_version": 1,
        "evidence_type": "I015_RC1_POST_PROMOTION_AUDIT",
        "status": "POST_PROMOTION_AUDIT_PASS",
        "qualification_receipt_sha256": qh,
        "promotion_receipt_sha256": ph,
        "vault_marker_sha256": mh,
        "vault_root": str(vault_root),
        "source_candidate": source,
        "promoted_candidate": promoted,
        "source_promoted_byte_equal": True,
        "vault_integrity": "PASS",
        "chain_integrity": "PASS",
        "next_gate": "RC1_RELEASE_DECISION_REQUIRED",
        "stable_release_allowed": False,
        "rc1_release_allowed": False,
        "builder_v10_allowed": False,
        "production_write_enabled": False,
        "real_user_data_touched": False,
        "safety": LOCKS,
    }

def write_immutable(obj: dict, out_dir: Path):
    if out_dir.is_symlink():
        raise ValueError("OUTPUT_DIR_SYMLINK")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()
    h = hashlib.sha256(payload).hexdigest()
    out = out_dir / f"RC1_POST_PROMOTION_AUDIT_{h}.json"
    side = out.with_suffix(out.suffix + ".sha256")
    side_payload = f"{h}  {out.name}\n".encode()
    if out.exists() or out.is_symlink() or side.exists() or side.is_symlink():
        if out.exists() and side.exists() and out.read_bytes() == payload and side.read_bytes() == side_payload:
            return out, side, h
        raise ValueError("AUDIT_COLLISION_OR_OVERWRITE")
    out.write_bytes(payload)
    side.write_bytes(side_payload)
    os.chmod(out, 0o444)
    os.chmod(side, 0o444)
    return out, side, h

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qualification", required=True)
    ap.add_argument("--promotion", required=True)
    ap.add_argument("--vault-marker", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--promoted", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    try:
        result = audit(
            Path(a.qualification),
            Path(a.promotion),
            Path(a.vault_marker),
            Path(a.source),
            Path(a.promoted),
        )
        out, side, h = write_immutable(result, Path(a.output_dir))
        print(json.dumps({"status": result["status"], "evidence": str(out), "sha256": h}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 12

if __name__ == "__main__":
    raise SystemExit(main())
