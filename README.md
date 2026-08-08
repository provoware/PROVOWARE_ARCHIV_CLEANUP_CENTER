# PROVOWARE Archiv & Cleanup Center — Iteration 014

## Unified Diagnostic Report + Acceptance Evidence Bundle

I014 baut ausschließlich auf dem validierten I013-Vollrelease auf.

**Verifizierte I013-Basis:**

`SHA-256 1d2d7bb14689daf50fd5b0a31cb3fef65e06d7dcb6f75e97e74b05da62290460`

Reale Nutzdaten-Schreibaktionen, reale Quarantäne und endgültiges Löschen bleiben technisch gesperrt.

## Ziel der Iteration

Die vorhandenen Evidence-Schichten werden nicht länger nur einzeln dargestellt. I014 führt die für eine Abnahme maßgeblichen Zustände über einen Cross-Reference-Validator zu einem kanonischen Diagnosemodell zusammen:

```text
Health Evidence
+
Production Contract
+
ExecutionIntent
+
Unified Audit Chain
+
Real-Target Acceptance / Reconnect Checkpoint
↓
Cross-Reference Validation
↓
kanonisches Diagnostic Model
↓
JSON + Markdown + HTML
↓
Component SHA-256
↓
Bundle Manifest
↓
Bundle Fingerprint
↓
immutable Evidence-Generation
```

## Cross-Reference Validation

Vor jeder Bundle-Erzeugung werden unter anderem gegeneinander geprüft:

- Session-ID
- Device-ID
- Contract-Fingerprint
- Intent-Fingerprint
- Plan-ID
- Unified-Audit-Chain-Hash
- Acceptance-Checkpoint-Fingerprint
- Contract-Integrität
- ExecutionIntent-Integrität
- Unified-Audit-Verifikation
- Health-/Reconnect-Vollständigkeit

Die Diagnose besitzt vier explizite Zustände:

```text
DIAGNOSTIC_COMPLETE
DIAGNOSTIC_PARTIAL
DIAGNOSTIC_INCONSISTENT
DIAGNOSTIC_BLOCKED
```

`PARTIAL` bedeutet fehlende oder noch nicht abgeschlossene Evidence. `INCONSISTENT` bedeutet vorhandene, aber widersprüchliche Bindungen. Integritätsverletzungen oder behauptete reale Nutzdatenaktionen führen zu `BLOCKED`.

## Ein kanonisches Modell

`diagnose.json`, `diagnose.md` und `diagnose.html` werden aus exakt demselben Modell erzeugt. Dadurch kann keine Darstellung einen anderen Sicherheitszustand behaupten als eine andere.

Das Modell besitzt einen deterministischen SHA-256-`model_fingerprint`. Die einzelnen Evidence-Komponenten erhalten zusätzlich eigene kanonische SHA-256-Fingerprints.

## Immutable Evidence Bundle

Eine erfolgreiche Generierung erzeugt ausschließlich im PROVOWARE-Runtimebereich:

```text
runtime/sessions/<session>/i014_diagnostic/
├── .bundle.lock
├── generation_000001/
│   ├── diagnose.json
│   ├── diagnose.md
│   ├── diagnose.html
│   ├── manifest.json
│   └── evidence_bundle.zip
└── generation_000002/
    └── ...
```

Vorhandene Generationen werden nie überschrieben. Ein exklusiver `flock` verhindert parallele Writer. Temporäre Generationen werden atomar vorbereitet und erst nach Datei-/Verzeichnis-`fsync` sichtbar gemacht. Fehlgeschlagene Builds hinterlassen keine scheinbar gültige Generation.

Der Bundle-Fingerprint ist generationsunabhängig: identische Evidence besitzt denselben inhaltlichen Fingerprint, während die Generation lediglich die unveränderliche Historie abbildet.

## Harte Sicherheitsinvariante

I014 akzeptiert keine Evidence, die reale Nutzdatenaktionen behauptet. Unter anderem müssen dauerhaft gelten:

```text
actual_moved_files = 0
target_writes_attempted = 0
target_directories_created = 0
target_files_created = 0
real_user_data_touched = false
production_action_enabled = false
real_quarantine_release = false
real_delete_enabled = false
```

Auch bei `DIAGNOSTIC_COMPLETE` bleibt:

```text
write_readiness = BLOCKED_REAL_WRITE
```

Der nächste Blocker ist ausdrücklich ein **separater Production Authorization Contract plus explizite Nutzerfreigabe**. I014 erzeugt diese Freigabe nicht.

## Neue API

```text
GET  /api/unified-diagnostic
GET  /api/unified-diagnostic/file?kind=json|markdown|html|manifest|zip
POST /api/unified-diagnostic/build
```

Die Dateiausgabe wird auf die aktuelle immutable Bundle-Generation begrenzt; Pfade außerhalb der Generation werden blockiert.

## GUI

Die Oberfläche zeigt zusätzlich:

- Diagnosezustand
- Generation
- Bundle-Verifikation
- Bundle-Fingerprint
- permanenten Produktions-Hard-Lock
- HTML-Abnahmebericht
- Evidence-ZIP

## Start

```bash
cd PROVOWARE_ARCHIV_CLEANUP_CENTER_I014
chmod +x start.sh
./start.sh
```

Die Startsequenz umfasst 23 Prüfschritte und startet den lokalen Kern nur nach grünen Vorprüfungen.

## Rückfallbasis

Im Projekt liegt ausschließlich der unmittelbar vorherige validierte Vollrelease:

```text
Backup/PROVOWARE_ARCHIV_CLEANUP_CENTER_I013.zip
```

SHA-256: `1d2d7bb14689daf50fd5b0a31cb3fef65e06d7dcb6f75e97e74b05da62290460`

## Direkt folgender technischer Entwicklungsschritt

### Iteration 015 — Production Authorization Envelope — Preview Only

Als nächster Schritt sollte weiterhin **kein realer Execute-Pfad** entstehen. Stattdessen sollte ein kurzlebiger Authorization Envelope ausschließlich als Preview eingeführt werden. Er muss an Contract-, Intent-, Device-, Acceptance-, Audit- und Diagnostic-Bundle-Fingerprints sowie ein Ablaufzeitfenster gebunden sein und bei jeder Drift automatisch ungültig werden.

## Alternative Verbesserung mit hohem Nutzen und geringem Risiko

### Audit-/Diagnostic Generation Diff

Zwei immutable Audit-/Diagnostic-Generationen deterministisch vergleichen und Änderungen an Device, Mount, Health, Contract, Intent, Acceptance und Hashbindungen kompakt ausgeben. Das verbessert Fehlerdiagnose und reale Abnahme, ohne irgendeine Nutzdaten-Schreibberechtigung einzuführen.
