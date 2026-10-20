# Project status

All planned phases are implemented.

| Phase | Status |
|---|---|
| 1-3 Foundation, upload validation, Cisco/Junos parsers, redaction | Done |
| 4 Rule engine (19 rules, scoring, grade) | Done |
| 5 AI unknown-command mapping (Claude + heuristic fallback, human review) | Done |
| 6 Database (SQLAlchemy, Alembic; SQLite + PostgreSQL verified) | Done |
| 7 Frontend (dashboard, audits, history/compare, rules, AI review, users) | Done |
| 8 PDF report | Done |
| 9 Auth (JWT, roles), rate limiting, tests | Done: 121 backend + 11 frontend tests |
| 10 Docker, compose, CI, docs | Done (Docker files written but not executed in the authoring sandbox) |

## Known limitations
- Only Cisco IOS and Junos are parsed; other vendors are rejected clearly.
- Only security settings modelled in the normalized schema are evaluated (19 rules).
- AI path is tested with a mocked provider; verify with a real `AI_API_KEY` before demonstrating it.
- Framework references (NIST/ISO/CIS) are best-effort mappings; verify against official texts.
- In-memory rate limiter; token in sessionStorage (see docs/SECURITY.md).
