#!/usr/bin/env python3
"""Build a deterministic release-payload ZIP from RELEASE_TREE_CONTRACT.json."""
from __future__ import annotations
import argparse, json, os, stat, zipfile
from pathlib import Path
import importlib.util

def load_gate(root: Path):
    p = root / "tools" / "repository_release_gate.py"
    spec = importlib.util.spec_from_file_location("repository_release_gate", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def build(root: Path, output: Path) -> None:
    root = root.resolve()
    gate = load_gate(root)
    contract = gate.load_json(root / "RELEASE_TREE_CONTRACT.json")
    files = gate.payload_files(root, contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, (2026, 8, 13, 18, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o100755 if gate.expected_mode(rel, contract) == "100755" else 0o100644
            info.external_attr = mode << 16
            z.writestr(info, p.read_bytes())

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    build(Path(a.root), Path(a.output))
    print(Path(a.output))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
