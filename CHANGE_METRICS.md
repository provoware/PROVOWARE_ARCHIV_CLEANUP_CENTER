# Änderungsmetrik — Iteration 014

Basis: **I013 / 0.13.0 → I014 / 0.14.0**

| Metrik | Wert |
|---|---:|
| Geänderte Textdateien | 16 |
| Eingefügte Zeichen | 56348 |
| Gelöschte Zeichen | 203 |
| Ersetzte Alt-Zeichen | 6328 |
| Ersetzte Neu-Zeichen | 9566 |
| Netto-Zeichenänderung | +59383 |
| Neue Zeilen | 1234 |
| Gelöschte Zeilen | 5 |
| Ersetzte Alt-Zeilen | 94 |
| Ersetzte Neu-Zeilen | 193 |

## Aufteilung

- **Dokumentation:** `CHANGELOG.md`, `README.md`
- **Release-Metadaten:** `CURRENT_BASELINE.json`, `VERSION`
- **Produktcode:** `app.py`, `core/__init__.py`, `core/diagnostic_bundle.py`, `core/quarantine_plan.py`, `core/report_composer.py`, `core/testsystem.py`
- **Skripte:** `scripts/api_i014_smoke.py`, `scripts/evidence_report_demo.py`, `scripts/selftest.sh`, `start.sh`
- **Tests:** `tests/test_i014.py`
- **Oberfläche:** `web/index.html`

## Nicht in Zeichenmetriken enthaltene Dateiänderungen

- `Backup/PROVOWARE_ARCHIV_CLEANUP_CENTER_I012.zip` — removed, 613840 → 0 Byte
- `Backup/PROVOWARE_ARCHIV_CLEANUP_CENTER_I013.zip` — added, 0 → 839271 Byte
- `Backup/README.txt` — modified, 71 → 282 Byte
- `tests/test_i013.py.tmp` — removed, 0 → 0 Byte

Generierte Qualitäts-/Gate-/Manifestdateien, Runtime-Evidence und Binär-Backups sind bewusst aus den Zeichenwerten ausgeschlossen, damit die Metrik ohne Selbstreferenz reproduzierbar bleibt.
