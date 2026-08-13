import importlib.util,os,tempfile,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("launcher",ROOT/"tools"/"runtime_launcher.py")
launcher=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(launcher)
class RuntimeLauncherTests(unittest.TestCase):
 def test_selfcheck(self): self.assertEqual(launcher.selfcheck()["status"],"PASS")
 def test_ephemeral_bind(self):
  server,url,state=launcher.acquire(0)
  try:self.assertEqual(state,"NEW_EPHEMERAL");self.assertGreater(int(launcher.urllib.parse.urlparse(url).port),0)
  finally:server.server_close()
 def test_receipt_reuse(self):
  old=os.environ.get("XDG_RUNTIME_DIR")
  with tempfile.TemporaryDirectory() as d:
   os.environ["XDG_RUNTIME_DIR"]=d
   server=launcher.LocalServer(("127.0.0.1",0),launcher.gui.Handler);port=server.server_address[1]
   threading.Thread(target=server.serve_forever,daemon=True).start()
   try:
    obj=launcher.receipt.build_receipt(ROOT,launcher.project_status()["version"],os.getpid(),port,f"http://127.0.0.1:{port}/")
    launcher.receipt.write_receipt(ROOT,obj)
    new,url,state=launcher.acquire(8765,1)
    self.assertIsNone(new);self.assertEqual(state,"REUSE_RECEIPT")
   finally:
    launcher.receipt.remove_receipt_if_owner(ROOT,os.getpid(),port);server.shutdown();server.server_close()
    if old is None:os.environ.pop("XDG_RUNTIME_DIR",None)
    else:os.environ["XDG_RUNTIME_DIR"]=old
if __name__=="__main__":unittest.main()
