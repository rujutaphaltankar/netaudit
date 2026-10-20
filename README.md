# NetAudit — Network Security Compliance Auditor

Upload a **Cisco IOS** or **Juniper Junos** configuration. NetAudit parses it, evaluates **19 security rules**
(inspired by NIST SP 800-53, ISO/IEC 27001 and CIS Controls), shows the exact config line behind every finding,
gives vendor-specific fixes, scores the device (0–100, grade A–F) and exports a **PDF report**.

## Key design principles
- **Deterministic verdicts.** Rules are data (`backend/app/rules/catalog.json`); no AI decides PASS/FAIL or the score.
- **No guessing.** Missing/ambiguous evidence is `UNKNOWN`, never a pass; it is excluded from the score and shown as "evidence coverage".
- **Secrets redacted** before anything is stored; the raw file is never saved.
- **AI is optional and advisory.** Claude (if `AI_API_KEY` set) or a rule-based fallback suggests meanings for unrecognized commands; a human must approve; it never changes findings or scores.
- **Honest claims.** Passing the rules is *not* a compliance certification.

## Features
| Area | What you get |
|---|---|
| Parsing | Cisco IOS + Junos (`set` and hierarchical), auto vendor detection, upload validation |
| Rule engine | 19 rules, 4 severities, per-vendor remediation, framework references, weighted score, critical-failure grade cap |
| Persistence | SQLAlchemy + Alembic; SQLite (default) or PostgreSQL |
| Auth | JWT login, `admin` / `viewer` roles, scrypt password hashing, rate limiting |
| UI | Dashboard (charts), upload, audit detail (filters, evidence, copy-fix), history + compare, rules library, AI review, user admin |
| Reports | Downloadable PDF per audit |
| Delivery | Dockerfiles, docker-compose (Postgres + nginx), GitHub Actions CI |

## Quick start (Docker, one command)
```bash
cp .env.example .env
docker compose up --build
# open http://localhost:8080   (demo: admin / Admin@12345, viewer / Viewer@12345)
```

## Run locally without Docker
```bash
# backend  (http://localhost:8000, docs at /docs)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload

# frontend (http://localhost:5100)
cd frontend && cp .env.example .env && npm install && npm run dev
```
Demo data (4 sample audits + a `viewer` account) is created when `SEED_DEMO_DATA=true`.

## Tests
```bash
cd backend && python -m pytest -q     # 121 tests: parsers, rules, auth, API, AI (mocked), PDF, migrations
cd frontend && npm test               # 11 tests;  npm run build  also type-checks
```

## Project layout
```
backend/app/  api/ (routes, auth deps)  rules/ (catalog.json, engine)  parsers/  services/ (audits, AI, PDF, bootstrap)
              db/ (models, session)  schemas/  core/ (config, security, rate limit)   backend/migrations/ (Alembic)
frontend/src/ pages/  components/  api/client.ts  auth/  lib/
samples/      weak + hardened Cisco/Junos configs, one unsupported (Arista)
docs/         ARCHITECTURE.md  USER_GUIDE.md  SECURITY.md  DEMO_SCRIPT.md
```
See `docs/` for the architecture, security notes and a step-by-step demo script, and `PROJECT_STATUS.md` for scope and known limitations.
