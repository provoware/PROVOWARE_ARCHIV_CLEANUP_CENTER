#!/usr/bin/env python3
"""PROVOWARE Archiv & Cleanup Center — I015 Recovery GUI.

Lokale, offline-fähige, grafische Read-only-Oberfläche.
Keine realen Nutzdaten-Schreibaktionen, keine Release-Freigabe.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import stat
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
import importlib.util
import uuid
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import runtime_instance_receipt as runtime_receipt
WEB = ROOT / "web"
STATUS_FILE = ROOT / "PROJEKTSTATUS.json"
VERSION = "0.15.0-rc1-recovery-phase31a-runtime-receipt1"
PRODUCT = "PROVOWARE Archiv & Cleanup Center"
CANONICAL = {
    "I014": "72393a4ed445a765a7542d7a28c42171dbae66ed927dd0207c31f05a2a159899",
    "BUILDER_V9": "29ad1a4a2ed8fcc8f1eff5c6bb36ba37425352caab8ecb99c3a992cdeac8780c",
}
LOCKS = {
    "production_write_enabled": False,
    "real_user_data_touched": False,
    "rc1_release_allowed": False,
    "stable_release_allowed": False,
    "builder_v10_allowed": False,
}

BLOCKED_ROOTS = tuple(
    Path(p) for p in (
        "/", "/boot", "/dev", "/etc", "/proc", "/run", "/sys",
        "/usr", "/var", "/bin", "/sbin", "/lib", "/lib64"
    )
)

CATEGORY_EXT = {
    "Bilder": {".jpg",".jpeg",".png",".gif",".webp",".bmp",".tif",".tiff",".svg",".heic"},
    "Video": {".mp4",".mkv",".mov",".avi",".webm",".m4v",".mpeg",".mpg",".ts"},
    "Audio": {".mp3",".flac",".wav",".m4a",".aac",".ogg",".opus",".wma"},
    "Dokumente": {".pdf",".doc",".docx",".odt",".rtf",".txt",".md",".xls",".xlsx",".ods",".ppt",".pptx"},
    "Archive": {".zip",".7z",".rar",".tar",".gz",".bz2",".xz",".tgz"},
    "Code": {".py",".js",".ts",".html",".css",".json",".yaml",".yml",".toml",".sh",".rs",".go",".java",".c",".cpp",".h"},
    "Layouts": {".fig",".sketch",".xd",".psd",".ai",".xcf"},
}

def _status() -> dict[str, Any]:
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return {
        "product": PRODUCT,
        "version": data.get("version", VERSION),
        "mode": "GRAPHICAL_READ_ONLY_RECOVERY",
        "status": data.get("status", "GUI_RECOVERY_READY"),
        "repository": data.get("repository", "provoware/PROVOWARE_ARCHIV_CLEANUP_CENTER"),
        "project_id": runtime_receipt.project_id(ROOT),
        "historical_i014_original_bytes_available": False,
        "historical_transfer_complete": False,
        "canonical_hashes": CANONICAL,
        "locks": LOCKS,
        "write_readiness": "BLOCKED_REAL_WRITE",
        "message": "Grafische Recovery-Oberfläche aktiv. Historische I014-Originalbytes fehlen weiterhin.",
    }

def _is_relative(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False

def validate_scan_root(raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("SCAN_PATH_EMPTY")
    p = Path(raw).expanduser()
    if p.is_symlink():
        raise ValueError("SCAN_ROOT_SYMLINK")
    try:
        r = p.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("SCAN_ROOT_NOT_FOUND") from exc
    if not r.is_dir():
        raise ValueError("SCAN_ROOT_NOT_DIRECTORY")
    for blocked in BLOCKED_ROOTS:
        if r == blocked or (blocked != Path("/") and _is_relative(r, blocked)):
            raise ValueError(f"SCAN_ROOT_BLOCKED:{blocked}")
    return r

def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for name, exts in CATEGORY_EXT.items():
        if ext in exts:
            return name
    return "Sonstiges"

def human_size(n: int) -> str:
    value = float(n)
    for unit in ("B","KiB","MiB","GiB","TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{n} B"

def scan_directory(raw: str, max_files: int = 50000, job: dict[str, Any] | None = None) -> dict[str, Any]:
    root = validate_scan_root(raw)
    root_dev = root.stat().st_dev
    categories: Counter[str] = Counter()
    category_bytes: Counter[str] = Counter()
    largest: list[tuple[int,str]] = []
    total_bytes = 0
    total_files = 0
    skipped_symlinks = 0
    skipped_devices = 0
    errors = 0
    started = time.time()

    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        c = Path(current)
        kept = []
        for d in dirs:
            p = c / d
            try:
                if p.is_symlink():
                    skipped_symlinks += 1
                    continue
                if p.stat().st_dev != root_dev:
                    skipped_devices += 1
                    continue
                kept.append(d)
            except OSError:
                errors += 1
        dirs[:] = kept

        for name in files:
            if total_files >= max_files:
                break
            p = c / name
            try:
                if p.is_symlink():
                    skipped_symlinks += 1
                    continue
                st = p.stat()
                if not stat.S_ISREG(st.st_mode):
                    continue
                if st.st_dev != root_dev:
                    skipped_devices += 1
                    continue
                size = int(st.st_size)
                cat = category_for(p)
                categories[cat] += 1
                category_bytes[cat] += size
                total_bytes += size
                total_files += 1
                largest.append((size, str(p)))
                if len(largest) > 80:
                    largest.sort(reverse=True)
                    del largest[40:]
                if job is not None and total_files % 100 == 0:
                    job.update({
                        "files": total_files,
                        "bytes": total_bytes,
                        "current": str(p),
                        "elapsed": round(time.time() - started, 2),
                    })
            except OSError:
                errors += 1
        if total_files >= max_files:
            break

    largest.sort(reverse=True)
    return {
        "root": str(root),
        "read_only": True,
        "same_device_only": True,
        "follow_symlinks": False,
        "files": total_files,
        "bytes": total_bytes,
        "bytes_human": human_size(total_bytes),
        "max_files": max_files,
        "limit_reached": total_files >= max_files,
        "skipped_symlinks": skipped_symlinks,
        "skipped_other_devices": skipped_devices,
        "errors": errors,
        "elapsed": round(time.time() - started, 3),
        "categories": [
            {
                "name": k,
                "files": categories[k],
                "bytes": category_bytes[k],
                "bytes_human": human_size(category_bytes[k]),
            }
            for k in sorted(categories)
        ],
        "largest": [
            {"path": p, "bytes": s, "bytes_human": human_size(s)}
            for s, p in largest[:25]
        ],
    }

class Jobs:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jobs: dict[str, dict[str, Any]] = {}

    def create(self, path: str, max_files: int) -> str:
        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "state": "QUEUED",
            "path": path,
            "files": 0,
            "bytes": 0,
            "current": "",
            "started": time.time(),
        }
        with self.lock:
            self.jobs[job_id] = job
        threading.Thread(target=self._run, args=(job_id, path, max_files), daemon=True).start()
        return job_id

    def _run(self, job_id: str, path: str, max_files: int) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job["state"] = "RUNNING"
        try:
            result = scan_directory(path, max_files=max_files, job=job)
            with self.lock:
                job["result"] = result
                job["state"] = "DONE"
                job["finished"] = time.time()
        except Exception as exc:
            with self.lock:
                job["state"] = "ERROR"
                job["error"] = str(exc)
                job["finished"] = time.time()

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.lock:
            item = self.jobs.get(job_id)
            return dict(item) if item else None

JOBS = Jobs()

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def recovery_index(roots: list[str], evidence_root: str) -> dict[str, Any]:
    if not isinstance(roots, list) or not roots:
        raise ValueError("RECOVERY_ROOTS_EMPTY")
    module = load_module(ROOT / "recovery" / "phase31" / "candidate_index_collector.py", "candidate_index_collector")
    result = module.collect(roots)
    out, digest = module.write_index(result, Path(evidence_root), roots)
    return {
        "status": "CANDIDATE_INDEX_READY",
        "candidate_count": result["candidate_count"],
        "index": str(out),
        "sha256": digest,
        "next_gate": result["next_gate"],
        "read_only": True,
    }

class Handler(BaseHTTPRequestHandler):
    server_version = "PROVOWARE-Recovery-GUI/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[HTTP]", fmt % args)

    def _json(self, obj: Any, status: int = 200) -> None:
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("INVALID_CONTENT_LENGTH")
        if length > 1024 * 1024:
            raise ValueError("REQUEST_TOO_LARGE")
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8") or "{}")
        except Exception as exc:
            raise ValueError("INVALID_JSON") from exc
        if not isinstance(obj, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        return obj

    def _static(self, rel: str) -> None:
        target = (WEB / rel.lstrip("/")).resolve()
        if not _is_relative(target, WEB.resolve()) or not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        ctype, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", (ctype or "application/octet-stream") + ("" if ctype and not ctype.startswith("text/") else "; charset=utf-8"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._static("index.html")
        if parsed.path == "/api/status":
            return self._json(_status())
        if parsed.path == "/api/scan/status":
            q = urllib.parse.parse_qs(parsed.query)
            job_id = q.get("id", [""])[0]
            item = JOBS.get(job_id)
            return self._json(item if item else {"error": "JOB_NOT_FOUND"}, 200 if item else 404)
        if parsed.path.startswith("/web/"):
            return self._static(parsed.path[len("/web/"):])
        self.send_error(404)

    def do_POST(self) -> None:
        try:
            body = self._body()
            if self.path == "/api/scan":
                path = body.get("path", "")
                max_files = int(body.get("max_files", 50000))
                max_files = max(1, min(max_files, 200000))
                validate_scan_root(path)
                job_id = JOBS.create(path, max_files)
                return self._json({"status": "STARTED", "job_id": job_id, "read_only": True}, 202)
            if self.path == "/api/recovery/index":
                roots = body.get("roots")
                evidence = body.get("evidence_root", "")
                return self._json(recovery_index(roots, evidence))
            return self._json({"error": "ENDPOINT_NOT_FOUND"}, 404)
        except Exception as exc:
            return self._json({"error": str(exc), "fail_closed": True}, 400)

def selfcheck() -> dict[str, Any]:
    errors = []
    if not (WEB / "index.html").is_file():
        errors.append("WEB_INDEX_MISSING")
    if not STATUS_FILE.is_file():
        errors.append("PROJEKTSTATUS_MISSING")
    for rel in (
        "recovery/phase31/candidate_index_collector.py",
        "recovery/phase31/real_artifact_availability.py",
        "recovery/phase30/post_promotion_audit.py",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"MISSING:{rel}")
    status = _status()
    if any(status["locks"].values()):
        errors.append("SAFETY_LOCK_DRIFT")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "version": status["version"]}

class LocalThreadingHTTPServer(ThreadingHTTPServer):
    """Local-only server with safe rapid restart behaviour."""
    allow_reuse_address = True
    daemon_threads = True


def _probe_existing_provoware(port: int, timeout: float = 0.35) -> dict[str, Any] | None:
    """Return status only when the occupied port is a compatible PROVOWARE instance."""
    if not (1 <= int(port) <= 65535):
        return None
    url = f"http://127.0.0.1:{int(port)}/api/status"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            obj = json.loads(resp.read(256 * 1024).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    if obj.get("product") != PRODUCT or obj.get("mode") != "GRAPHICAL_READ_ONLY_RECOVERY":
        return None
    if obj.get("version") != _status()["version"]:
        return None
    return obj


def _probe_receipt_instance() -> tuple[str, dict[str, Any]] | None:
    try:
        receipt = runtime_receipt.load_receipt(ROOT)
    except runtime_receipt.RuntimeReceiptError:
        return None
    if not receipt:
        return None
    ok, _reason = runtime_receipt.validate_receipt(ROOT, _status()["version"], receipt)
    if not ok:
        return None
    port = int(receipt["port"])
    status = _probe_existing_provoware(port)
    if status is None:
        return None
    if status.get("project_id") != receipt.get("project_id"):
        return None
    return receipt["url"], receipt

def acquire_local_server(preferred_port: int = 8765, fallback_tries: int = 32):
    """Bind localhost safely.

    - same current PROVOWARE already running -> reuse existing instance
    - foreign/older process on preferred port -> try following localhost ports
    - finally ask OS for an ephemeral free port
    """
    preferred_port = int(preferred_port)
    if preferred_port < 0 or preferred_port > 65535:
        raise ValueError("PORT_OUT_OF_RANGE")

    existing_by_receipt = _probe_receipt_instance()
    if existing_by_receipt is not None:
        url, _receipt = existing_by_receipt
        return None, url, "REUSE_RECEIPT"

    if preferred_port == 0:
        server = LocalThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        return server, f"http://127.0.0.1:{port}/", "NEW_EPHEMERAL"

    candidates = [preferred_port]
    upper = min(65535, preferred_port + max(0, int(fallback_tries)))
    candidates.extend(range(preferred_port + 1, upper + 1))

    first_busy = False
    for port in candidates:
        try:
            server = LocalThreadingHTTPServer(("127.0.0.1", port), Handler)
            state = "NEW_PREFERRED" if port == preferred_port else "NEW_FALLBACK"
            return server, f"http://127.0.0.1:{port}/", state
        except OSError as exc:
            if exc.errno not in (98, 48, 10048):  # Linux, macOS, Windows EADDRINUSE
                raise
            if port == preferred_port:
                first_busy = True
                existing = _probe_existing_provoware(port)
                if existing is not None:
                    return None, f"http://127.0.0.1:{port}/", "REUSE_EXISTING"
            continue

    # Last-resort local ephemeral port. No fixed port is killed or stolen.
    server = LocalThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    state = "NEW_EPHEMERAL_AFTER_CONFLICT" if first_busy else "NEW_EPHEMERAL"
    return server, f"http://127.0.0.1:{port}/", state


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()

    if args.selfcheck:
        result = selfcheck()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "PASS" else 12

    if args.host not in ("127.0.0.1", "localhost"):
        print("BLOCKIERT: Der GUI-Server darf nur lokal gebunden werden.")
        return 12

    try:
        server, url, bind_state = acquire_local_server(args.port)
    except (OSError, ValueError) as exc:
        print(f"BLOCKIERT: Lokaler GUI-Port konnte nicht bereitgestellt werden: {exc}")
        return 12

    if bind_state in ("REUSE_EXISTING", "REUSE_RECEIPT"):
        print(f"PROVOWARE GUI bereits aktiv: {url}", flush=True)
        print("Hinweis: Keine zweite Serverinstanz gestartet.", flush=True)
        if bind_state == "REUSE_RECEIPT":
            print("Single-Instance Runtime Receipt: PASS", flush=True)
        if not args.no_browser:
            threading.Timer(0.1, lambda: webbrowser.open(url)).start()
        return 0

    actual_port = int(urllib.parse.urlparse(url).port or 0)
    if args.port and actual_port != args.port:
        print(
            f"Hinweis: Port {args.port} ist belegt; "
            f"PROVOWARE verwendet automatisch den freien Port {actual_port}.",
            flush=True,
        )
    print(f"PROVOWARE GUI: {url}", flush=True)
    print("Modus: READ-ONLY / reale Schreibaktionen gesperrt", flush=True)
    receipt = runtime_receipt.build_receipt(ROOT, _status()["version"], os.getpid(), actual_port, url)
    receipt_file = runtime_receipt.write_receipt(ROOT, receipt)
    print(f"Runtime Receipt: {receipt_file}", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        assert server is not None
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime_receipt.remove_receipt_if_owner(ROOT, os.getpid(), actual_port)
        if server is not None:
            server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
