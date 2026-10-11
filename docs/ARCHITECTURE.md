# Architecture

## Overview
```
 React + Vite + TS (frontend)  --HTTP/JSON-->  FastAPI (backend, /api/v1)
                                                  |
   upload -> validate -> detect vendor -> vendor parser -> NormalizedConfig
                                                  |
                                   [Phase 4] rule engine -> findings
                                   [Phase 6] PostgreSQL persistence
                                   [Phase 8] ReportLab PDF
```
Frontend and backend run independently; the frontend only needs `VITE_API_BASE_URL`.

## Backend layout (`backend/app`)
| Path | Responsibility |
|---|---|
| `core/` | Settings from env vars, `AppError` |
| `schemas/` | Pydantic models: normalized schema, parser output, API contracts |
| `parsers/` | `BaseConfigParser`, Cisco IOS + Junos parsers, redaction, weakness derivation, registry |
| `services/` | Upload validation, vendor detection, pipeline orchestration |
| `api/v1/` | Thin routes (health, vendors, configs/parse) |
| `db/` | Engine + health check (models/migrations arrive in Phase 6) |

Adding a vendor = write a parser subclass, register it in `parsers/registry.py`, add tests.

## Normalized schema (v1.0.0)
Every extracted value is a **Setting** with `state` (`known`/`unknown`), `value`, `unknown_reason`
(`not_found`, `ambiguous`, `unsupported`, `unrecognized`), redacted `evidence` (line number + text) and an optional `note`.
The model validator makes it impossible to build a known setting without a value or an unknown one with a value.

### Absence conventions (important for the rule engine)
1. Absence of a **global command** -> `unknown / not_found` (configs can be partial; defaults vary by version).
2. Absence **inside a block that is present** (e.g. no `access-class` under `line vty`) or inside a **command family where other
   members exist** (e.g. SNMP lines present but no community) -> known.
3. Explicit negatives (`no ip http server`) -> known `false`.
4. Conflicting or default-dependent evidence -> `unknown / ambiguous`.
5. `detected_weak_settings` lists only *positively detected* weaknesses; an empty list never proves a config is safe.

Phase 4 rules can treat `not_found` and `ambiguous` differently (e.g. a rule may FAIL on `not_found` for a full running-config)
but must never PASS on either.

## Security design
- Uploads are untrusted: size/line/extension/binary checks, held in memory only, never written to disk or executed.
- Filenames are display-only (sanitized), never used as paths.
- Secrets are redacted from all evidence and unknown-command text before leaving the parser; only the exception *type* is logged on failure.
- DB URL and AI key are backend env vars; the frontend only sees `VITE_API_BASE_URL`.
- CORS is restricted to `CORS_ORIGINS`.
- **No authentication yet** (see limitations in PROJECT_STATUS.md).

## Parsers
- **Cisco IOS**: indentation-based block tree; banners skipped; last-wins for flag commands.
- **Junos**: `set` and hierarchical formats flattened to token paths; `inactive:`/`deactivate`/`delete` honoured; `groups` not evaluated (warned).
- Unknown commands = unconsumed lines under security-relevant roots, minus a small benign list (input for Phase 5).
