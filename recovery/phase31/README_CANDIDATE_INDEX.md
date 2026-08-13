# Phase 31A — Candidate Index Collector (read-only)

Der Collector inventarisiert ausschließlich explizit angegebene Recovery-/Vault-/Intake-Wurzeln.

Er folgt keinen Symlinks, liest nur Dateimetadaten und maximal vier Bytes für ZIP-Magic, berechnet keine Release-SHA-256, kopiert/verschiebt/löscht/benennt keine Kandidaten und besitzt keine Intake-, RC1-, Stable- oder Builder-V10-Rechte.

Ausgabe: `I015_RECOVERY_CANDIDATE_INDEX → Phase 31 Real Artifact Availability Gate`.

Die bytegenaue Qualifikation bleibt ausschließlich Aufgabe von Phase 31.
