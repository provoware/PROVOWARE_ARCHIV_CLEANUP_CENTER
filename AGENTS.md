# AGENTS.md — PROVOWARE Global Development Contract

Gilt repositoryweit für Menschen, Codex, Subagenten und Automationen.

## Globale Grundregeln
1. **Frozen Current Plan:** Nach Start einer Iteration bleibt ihr freigegebener Plan unverändert. Neue Ideen, TODOs, Findings und Verbesserungen gehen standardmäßig in die nächste Iteration.
2. **Conflict Gate:** Laufende Arbeit nur stoppen, wenn ein neuer Befund eine Planvoraussetzung, Sicherheit, den Ausgangs-SHA, den erlaubten Scope oder einen Invariant nachweislich verletzt.
3. **Single Writer:** Pro produktivem Scope darf gleichzeitig nur ein autorisierter Executor schreiben. Analyse, Planung und Prüfung dürfen parallel lesen.
4. **SHA + Scope:** Vor produktiver Mutation HEAD, Ausgangs-SHA, erlaubten und verbotenen Scope prüfen. Keine stillen Nebenrefactorings.
5. **Evidence statt Behauptung:** Kein PASS ohne tatsächlich ausgeführten Test. Gate-Evidence muss zum geprüften HEAD gehören.
6. **Controlled Evidence Lab:** Checker dürfen in isolierten temporären Testbereichen echte Dateien erzeugen, verändern, löschen, Fehler injizieren und Recovery prüfen; produktive Daten bleiben unangetastet.
7. **Next-Iteration Queue:** Neue Anforderungen append-only erfassen, nicht während der Ausführung heimlich einbauen. Beziehungen wie BLOCKS, REQUIRES, SUPERSEDES, DUPLICATE und CONFLICTS dokumentieren.
8. **Status trennen:** Beobachtung/Vermutung/Befund unterscheiden: OBSERVED → SUSPECTED → REPRODUCED → CONFIRMED oder DISPROVED.
9. **Recovery Key:** Jeder bestätigte Zustand muss ohne alten Chat rekonstruierbar sein: letzter Head, Ziel, Frozen Plan, erledigte Schritte, offener Schritt, Scope, Findings, nächste Queue, Gates und nächster erlaubter Schritt.
10. **Traceability:** Änderungen nach Möglichkeit rückverfolgbar halten: Requirement/Decision → Finding → Plan → Change → Test/Evidence → Gate/Checkpoint.
11. **Invariants + Negativtests:** Schutzregeln selbst testen, u. a. zweiter Writer, falscher SHA, Scope-Verstoß, ungültiger Recovery-Zustand und PASS ohne Evidence.
12. **Sichtbarer Fortschritt:** Bei längeren Prüfungen aktuellen Schritt, Fortschritt, Ergebnis und Ampelstatus nachvollziehbar ausgeben.
13. **Idempotenz und Recovery:** Wiederholbare Schritte bevorzugen; Abbruch darf den letzten bestätigten Zustand nicht unklar machen.
14. **Global vor lokal bei Sicherheit:** Projektspezifische Regeln dürfen diesen Sicherheits- und Nachvollziehbarkeitskern verschärfen, aber nicht stillschweigend abschwächen.

Leitsatz: **Kein Agent muss sich erinnern. Kein Agent darf raten. Keine Änderung verliert ihren Ursprung. Kein PASS existiert ohne Evidence.**
