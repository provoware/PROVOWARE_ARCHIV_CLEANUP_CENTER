# I015 Recovery Phase 31 — Real Artifact Availability + Verified Intake Handoff

Phase 31 qualifiziert ausschließlich explizit indexierte Kandidatenpfade gegen die kanonischen I014- und Builder-V9-SHA-256-Werte. Kandidaten werden nur gelesen und niemals kopiert, verschoben, umbenannt oder gelöscht.

Zustände: `RECOVERY_ARTIFACTS_STILL_MISSING`, `RECOVERY_ARTIFACTS_PARTIAL`, `RECOVERY_ARTIFACTS_MULTIPLE_MATCHES`, `VERIFIED_INTAKE_HANDOFF_READY`.

Nur exakt ein bytegenauer und ZIP-validierter Treffer je Ziel führt zu `VERIFIED_INTAKE_HANDOFF_READY`; danach bleibt `VERIFIED_ARTIFACT_INTAKE_REQUIRED` ein separates Gate.

GitHub enthielt zum Phase-31-Start keine Originalbytes der beiden Zielartefakte und keine Releases. Der GitHub-Verfügbarkeitssnapshot wird deshalb extern durch die Connector-Prüfung erzeugt und als Eingabeevidence gebunden.

Alle Sicherheitsgates bleiben geschlossen: kein Produktionsschreiben, kein RC1-/Stable-Release, kein Builder V10.
