# AI-Driven Multi-Vendor Network Security Compliance Auditor

Upload network device configurations, normalize them into a vendor-neutral schema, and (in later phases) audit them against
selected security checks inspired by CIS, NIST SP 800-53, DISA STIG and ISO/IEC 27001. This project does **not** claim full
compliance with any framework.

**Progress is tracked in [`PROJECT_STATUS.md`](PROJECT_STATUS.md)** (single source of truth).

## What works today (Phases 1–3)
- Upload + validation + vendor auto-detection / explicit selection (Cisco IOS, Juniper Junos in `set` and hierarchical format)
- Parsing into a normalized schema with redacted evidence, explicit unknown states, parser warnings and unrecognized commands
- React UI to upload a file and inspect the real parsed result

Not implemented yet: rule engine, AI mapping, persistence, dashboard, PDF reports, deployment.

## Run locally
```bash
# Backend (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload            # http://localhost:8000/docs

# Frontend (Node 20+)
cd frontend
cp .env.example .env
npm install && npm run dev               # http://localhost:5173
```
Sample (synthetic) configs are in `samples/`.

## Tests
```bash
cd backend && pytest        # 71 tests
cd frontend && npm test && npm run build
```
Backend tests use SQLite for the health check; PostgreSQL is first exercised in Phase 6.

## API (so far, under `/api/v1`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | App, DB and AI-fallback status |
| GET | `/vendors` | Vendors and whether each is supported |
| POST | `/configs/parse` | multipart: `file`, `vendor` (`auto`/vendor id), `force_vendor`; returns normalized result |

Errors use `{"error": {"code", "message", "details"}}` (400 empty/malformed, 413 too large, 415 bad type/binary, 422 vendor problems).

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and the absence/unknown conventions.
