# CHANGELOG

## 0.14.0 — Iteration 014

### Unified Diagnostic Report + Acceptance Evidence Bundle

- neuer `core/diagnostic_bundle.py`
- kanonisches Diagnosemodell als einzige Datenquelle für JSON, Markdown und HTML
- Cross-Reference-Validator für Session, Device, Contract, Intent, Audit, Plan und Acceptance-Checkpoint
- Zustände `DIAGNOSTIC_COMPLETE`, `DIAGNOSTIC_PARTIAL`, `DIAGNOSTIC_INCONSISTENT`, `DIAGNOSTIC_BLOCKED`
- deterministischer Model-Fingerprint und Komponenten-SHA-256
- generationsunabhängiger Bundle-Fingerprint
- immutable Bundle-Generationen ohne Überschreiben
- exklusiver Single-Writer-`flock` für Bundle-Erzeugung
- atomare Staging→Generation-Promotion mit `fsync`
- automatische Bereinigung unvollständiger Runtime-Staging-Verzeichnisse
- deterministisches Evidence-ZIP mit `manifest.json`, `diagnose.json`, `diagnose.md`, `diagnose.html`
- Bundle-Verifikation erkennt Datei-, Manifest-, Model- und Symlink-Manipulation
- Ausgabe innerhalb des Nutzdatenziels wird blockiert
- reale Schreib-/Quarantäne-/Löschbehauptungen werden als Sicherheitsverletzung blockiert

### API / GUI

- `GET /api/unified-diagnostic`
- `GET /api/unified-diagnostic/file?kind=...`
- `POST /api/unified-diagnostic/build`
- GUI-Panel für Diagnosezustand, Generation, Verifikation, Fingerprint, HTML-Bericht und Evidence-ZIP
- veraltete GUI-Kernversionsanzeige von 0.12 auf 0.14 korrigiert
- Evidence Report um I014-Status erweitert

### Readiness / Sicherheit

- `write_readiness_gate` berücksichtigt nun das I014 Diagnostic Evidence Bundle
- auch `DIAGNOSTIC_COMPLETE` bleibt `BLOCKED_REAL_WRITE`
- verbleibender Blocker: separater Production Authorization Contract + explizite Nutzerfreigabe
- `actual_moved_files = 0`
- `production_action_enabled = false`
- `real_quarantine_release = false`
- `real_delete_enabled = false`

### Wartbarkeit

- obsoleten Testüberrest `tests/test_i013.py.tmp` entfernt
- Downstream-Invalidierung gehärtet: neue Audit-/Acceptance-Zustände invalidieren alte Diagnostic Bundles
- Backup-Basis auf den unmittelbar vorherigen validierten I013-Vollrelease verschoben
- Startsequenz auf 23 Gates erweitert
- I014 API-End-to-End-Smoke ergänzt
- interne Selftests bis I014 erweitert
### Finale Qualitätsgates

- Unit-/Integrations-Tests: 133/133 PASS
- interne Selftests: 53/53 PASS
- I/O Fault Matrix: 11/11 PASS
- Python-Syntax/Bytecode: 61 Dateien PASS
- JavaScript-Syntax: 14 Blöcke PASS
- Shell-Syntax: PASS
- I011–I014 API-Regression: PASS
- I014 Hard-Lock Static Gate: PASS
- Release-ZIP-Integrität: wird nach Packaging erneut verifiziert

