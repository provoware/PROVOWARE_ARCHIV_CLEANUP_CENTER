# GitHub Baseline Import — I014

Dieser Branch verankert die **verifizierte Release-Identität** von I014 im Repository.

- Release: `I014 / 0.14.0`
- Release-ZIP SHA-256: `72393a4ed445a765a7542d7a28c42171dbae66ed927dd0207c31f05a2a159899`
- Manifest SHA-256: `ab8dd9a4ee99c04f3e8050b8fff1ea7cce44bfed3941236066c5eae58de7be1b`
- Parent: `I013`
- Parent SHA-256: `1d2d7bb14689daf50fd5b0a31cb3fef65e06d7dcb6f75e97e74b05da62290460`
- Entwicklungs-Gate: **PASS**
- Produktionsfreigabe: **LOCKED**
- Write Readiness: `BLOCKED_REAL_WRITE`

## Importumfang

Der GitHub-Connector dieser Sitzung kann Git-Trees und UTF-8-Dateien schreiben, besitzt jedoch keinen direkten Uploadparameter für lokale Binärdateien. Daher wird dieser PR **nicht** fälschlich als vollständiger Quell-/Binärimport markiert. Er enthält den maschinenlesbaren Release-Identity-Anker, das vollständige Release-Manifest, Qualitäts-/Gate-Nachweise und Änderungsmetrik.

Das vollständige I014-Release bleibt durch den obigen ZIP-SHA und das Manifest eindeutig identifizierbar. Ein späterer Vollimport muss exakt gegen diese Werte verifiziert werden.

## Sicherheitsstatus

`actual_moved_files = 0`, `production_action_enabled = false`, reale Quarantäne und endgültiges Löschen bleiben gesperrt.
