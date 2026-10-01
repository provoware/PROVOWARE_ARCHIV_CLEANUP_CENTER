# I015 Recovery Phase 30 — RC1 Post-Promotion Audit + Vault Integrity Proof

Diese Iteration ergänzt ausschließlich eine **unabhängige read-only Audit-Schicht** hinter einer bereits erfolgten isolierten RC1-Promotion.

## Sicherheitsgrenze

Der Auditor:
- erzeugt keine Promotion,
- erzeugt keinen Vault,
- verändert weder Source noch promoted Candidate,
- öffnet weder RC1 noch Stable,
- beginnt keinen Builder V10.

Er prüft:
- Qualification Receipt,
- Promotion Receipt,
- Vault Marker,
- Source Candidate,
- promoted Candidate,
- alle relevanten SHA-256-Bindungen,
- Vault-Root-Bindung,
- ZIP-Integrität und Symlinkfreiheit,
- Read-only-Modus des promoted Candidate,
- Bytegleichheit Source ↔ promoted Candidate.

Ein grüner Lauf endet ausschließlich in:

`POST_PROMOTION_AUDIT_PASS → RC1_RELEASE_DECISION_REQUIRED`

`rc1_release_allowed=false` und `stable_release_allowed=false` bleiben bestehen.

## GitHub-Recovery-Priorität

Zum Implementierungszeitpunkt enthält das Repository keine I014-ZIP-Bytes, keine Builder-V9-Originalbytes und keine GitHub-Releases. Daher wurde Phase 30 als Infrastruktur umgesetzt; ein echter Fund dieser Originalartefakte hat weiterhin sofort Vorrang.
