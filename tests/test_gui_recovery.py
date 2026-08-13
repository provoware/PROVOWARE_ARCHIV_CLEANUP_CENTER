import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("app", ROOT / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class GuiRecoveryTests(unittest.TestCase):
    def test_selfcheck(self):
        self.assertEqual(app.selfcheck()["status"], "PASS")

    def test_status_locks_are_false(self):
        status = app._status()
        self.assertTrue(all(v is False for v in status["locks"].values()))
        self.assertFalse(status["historical_transfer_complete"])

    def test_critical_root_blocked(self):
        with self.assertRaisesRegex(ValueError, "SCAN_ROOT_BLOCKED"):
            app.validate_scan_root("/etc")

    def test_missing_path_blocked(self):
        with self.assertRaisesRegex(ValueError, "SCAN_ROOT_NOT_FOUND"):
            app.validate_scan_root("/definitely/not/here/provoware")

    def test_read_only_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.jpg").write_bytes(b"123")
            (root / "b.txt").write_text("hello", encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            result = app.scan_directory(str(root), max_files=100)
            after = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(before, after)
            self.assertEqual(result["files"], 2)
            self.assertTrue(result["read_only"])

    def test_categories(self):
        self.assertEqual(app.category_for(Path("x.mp4")), "Video")
        self.assertEqual(app.category_for(Path("x.flac")), "Audio")
        self.assertEqual(app.category_for(Path("x.unknown")), "Sonstiges")

    def test_web_index_exists(self):
        self.assertTrue((ROOT / "web" / "index.html").is_file())

    def test_busy_foreign_port_falls_back(self):
        foreign = app.LocalThreadingHTTPServer(("127.0.0.1", 0), app.BaseHTTPRequestHandler)
        port = foreign.server_address[1]
        thread = threading.Thread(target=foreign.serve_forever, daemon=True)
        thread.start()
        server = None
        try:
            server, url, state = app.acquire_local_server(port, fallback_tries=3)
            self.assertIsNotNone(server)
            self.assertNotEqual(int(app.urllib.parse.urlparse(url).port), port)
            self.assertIn(state, {"NEW_FALLBACK", "NEW_EPHEMERAL_AFTER_CONFLICT"})
        finally:
            if server is not None:
                server.server_close()
            foreign.shutdown()
            foreign.server_close()

    def test_same_provoware_instance_is_reused(self):
        existing = app.LocalThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        port = existing.server_address[1]
        thread = threading.Thread(target=existing.serve_forever, daemon=True)
        thread.start()
        try:
            server, url, state = app.acquire_local_server(port, fallback_tries=2)
            self.assertIsNone(server)
            self.assertEqual(state, "REUSE_EXISTING")
            self.assertEqual(int(app.urllib.parse.urlparse(url).port), port)
        finally:
            existing.shutdown()
            existing.server_close()

    def test_ephemeral_port_request(self):
        server, url, state = app.acquire_local_server(0)
        try:
            self.assertIsNotNone(server)
            self.assertGreater(int(app.urllib.parse.urlparse(url).port), 0)
            self.assertEqual(state, "NEW_EPHEMERAL")
        finally:
            server.server_close()

    def test_runtime_receipt_reuses_same_project_instance(self):
        import os, tempfile
        old = os.environ.get("XDG_RUNTIME_DIR")
        with tempfile.TemporaryDirectory() as d:
            os.environ["XDG_RUNTIME_DIR"] = d
            existing = app.LocalThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            port = existing.server_address[1]
            thread = threading.Thread(target=existing.serve_forever, daemon=True)
            thread.start()
            try:
                receipt = app.runtime_receipt.build_receipt(
                    app.ROOT, app._status()["version"], os.getpid(), port,
                    f"http://127.0.0.1:{port}/"
                )
                app.runtime_receipt.write_receipt(app.ROOT, receipt)
                server, url, state = app.acquire_local_server(8765, fallback_tries=1)
                self.assertIsNone(server)
                self.assertEqual(state, "REUSE_RECEIPT")
                self.assertEqual(int(app.urllib.parse.urlparse(url).port), port)
            finally:
                app.runtime_receipt.remove_receipt_if_owner(app.ROOT, os.getpid(), port)
                existing.shutdown()
                existing.server_close()
                if old is None:
                    os.environ.pop("XDG_RUNTIME_DIR", None)
                else:
                    os.environ["XDG_RUNTIME_DIR"] = old

if __name__ == "__main__":
    unittest.main()
