#!/usr/bin/env python3
"""PROVOWARE Single-Instance Runtime Receipt."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PRODUCT = "PROVOWARE Archiv & Cleanup Center"
MODE = "GRAPHICAL_READ_ONLY_RECOVERY"

class RuntimeReceiptError(RuntimeError):
    pass

def canonical_project_root(project_root: Path) -> Path:
    root = Path(project_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise RuntimeReceiptError("PROJECT_ROOT_NOT_DIRECTORY")
    return root

def project_id(project_root: Path) -> str:
    root = canonical_project_root(project_root)
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()

def runtime_base_dir() -> Path:
    xdg = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if xdg:
        return Path(xdg) / "provoware"
    uid = os.getuid() if hasattr(os, "getuid") else 0
    return Path(tempfile.gettempdir()) / f"provoware-{uid}"

def _assert_no_symlink_components(path: Path) -> None:
    p = Path(path).absolute()
    current = Path(p.anchor)
    for part in p.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise RuntimeReceiptError("RUNTIME_DIR_SYMLINK_COMPONENT")

def _assert_safe_dir(path: Path) -> None:
    _assert_no_symlink_components(path)
    if path.exists() and path.is_symlink():
        raise RuntimeReceiptError("RUNTIME_DIR_SYMLINK")
    if path.exists() and not path.is_dir():
        raise RuntimeReceiptError("RUNTIME_DIR_NOT_DIRECTORY")

def ensure_runtime_dir() -> Path:
    base = runtime_base_dir()
    _assert_safe_dir(base.parent)
    _assert_safe_dir(base)
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except OSError:
        pass
    _assert_safe_dir(base)
    return base

def receipt_path(project_root: Path) -> Path:
    return ensure_runtime_dir() / f"instance-{project_id(project_root)}.json"

def _pid_alive(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True

def build_receipt(project_root: Path, version: str, pid: int, port: int, url: str) -> dict[str, Any]:
    root = canonical_project_root(project_root)
    if not (1 <= int(port) <= 65535):
        raise RuntimeReceiptError("PORT_INVALID")
    expected_url = f"http://127.0.0.1:{int(port)}/"
    if url != expected_url:
        raise RuntimeReceiptError("URL_PORT_MISMATCH")
    return {
        "schema_version": SCHEMA_VERSION,
        "receipt_type": "PROVOWARE_SINGLE_INSTANCE_RUNTIME",
        "product": PRODUCT,
        "mode": MODE,
        "version": str(version),
        "project_root": str(root),
        "project_id": project_id(root),
        "pid": int(pid),
        "port": int(port),
        "url": expected_url,
        "created_unix": time.time(),
    }

def write_receipt(project_root: Path, receipt: dict[str, Any]) -> Path:
    path = receipt_path(project_root)
    _assert_no_symlink_components(path.parent)
    if path.exists() and path.is_symlink():
        raise RuntimeReceiptError("RUNTIME_RECEIPT_SYMLINK")
    raw = (json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    if tmp.exists() and tmp.is_symlink():
        raise RuntimeReceiptError("RUNTIME_TEMP_SYMLINK")
    try:
        with tmp.open("xb") as f:
            os.chmod(tmp, 0o600)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return path

def load_receipt(project_root: Path) -> dict[str, Any] | None:
    path = receipt_path(project_root)
    if not path.exists():
        return None
    _assert_no_symlink_components(path.parent)
    if path.is_symlink() or not path.is_file():
        raise RuntimeReceiptError("RUNTIME_RECEIPT_UNSAFE")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode):
        raise RuntimeReceiptError("RUNTIME_RECEIPT_NOT_REGULAR")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeReceiptError("RUNTIME_RECEIPT_INVALID_JSON") from exc
    if not isinstance(obj, dict):
        raise RuntimeReceiptError("RUNTIME_RECEIPT_INVALID")
    return obj

def validate_receipt(project_root: Path, version: str, receipt: dict[str, Any]) -> tuple[bool, str]:
    root = canonical_project_root(project_root)
    expected_id = project_id(root)
    port = receipt.get("port")
    checks = {
        "schema_version": receipt.get("schema_version") == SCHEMA_VERSION,
        "receipt_type": receipt.get("receipt_type") == "PROVOWARE_SINGLE_INSTANCE_RUNTIME",
        "product": receipt.get("product") == PRODUCT,
        "mode": receipt.get("mode") == MODE,
        "version": receipt.get("version") == version,
        "project_root": receipt.get("project_root") == str(root),
        "project_id": receipt.get("project_id") == expected_id,
        "pid": _pid_alive(receipt.get("pid")),
        "port": isinstance(port, int) and 1 <= port <= 65535,
        "url": isinstance(port, int) and receipt.get("url") == f"http://127.0.0.1:{port}/",
    }
    failed = [k for k, ok in checks.items() if not ok]
    return (not failed, "PASS" if not failed else "INVALID:" + ",".join(failed))

def remove_receipt_if_owner(project_root: Path, pid: int, port: int) -> bool:
    path = receipt_path(project_root)
    if not path.exists():
        return False
    try:
        obj = load_receipt(project_root)
    except RuntimeReceiptError:
        return False
    if not obj or obj.get("pid") != int(pid) or obj.get("port") != int(port):
        return False
    path.unlink(missing_ok=True)
    return True
