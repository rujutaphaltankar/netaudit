# NetAudit — Network Security Compliance Auditor

<p align="center">
  <strong>Deterministic, Evidence-Backed Security Compliance & Drift Auditor for Network Device Configurations</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/backend%20tests-121%20passed-137333?style=flat-square&logo=pytest" alt="Backend Tests" />
  <img src="https://img.shields.io/badge/frontend%20tests-15%20passed-137333?style=flat-square&logo=vitest" alt="Frontend Tests" />
  <img src="https://img.shields.io/badge/python-3.10%2B-0e7c86?style=flat-square&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/frontend-React%2019%20%2B%20Vite%20%2B%20TS-61dafb?style=flat-square&logo=react" alt="Frontend Stack" />
  <img src="https://img.shields.io/badge/compliance-NIST%20%7C%20ISO%2027001%20%7C%20CIS-b84208?style=flat-square" alt="Compliance Standards" />
  <img src="https://img.shields.io/badge/security-Zero--Disk%20Raw%20Storage-9f1239?style=flat-square" alt="Security Design" />
</p>

---

## 📌 Executive Summary

**NetAudit** is a specialized security compliance auditing platform for enterprise network infrastructure. Upload a **Cisco IOS** (`.cfg`, `.txt`) or **Juniper Junos** (`.conf`, `.set`) configuration file, and NetAudit:

1. **Validates & Sanitizes**: Parses files in-memory; secrets (passwords, pre-shared keys, SNMP communities) are automatically redacted before storage.
2. **Evaluates 19 Security Controls**: Assesses management access (SSH, Telnet, AUX, HTTP/HTTPS), AAA, secure logging (Syslog, TLS), NTP authentication, and SNMPv3 hardening.
3. **Applies Deterministic Scoring**: Produces an objective compliance score (0–100) and letter grade (A–F) with a strict Critical-Failure grade cap.
4. **Delivers Actionable Remediation**: Pinpoints the exact line numbers behind every finding and generates copyable, vendor-specific CLI remediation scripts.
5. **Tracks Configuration Drift**: Compares baseline vs. target audits side-by-side to highlight improved and regressed security checks.
6. **Exports Professional PDF Reports**: Generates formal, audit-ready compliance documentation with one click.

---

## 🏛️ Core Design Principles

- **Deterministic Rule Engine**: Rules are declarative JSON specifications (`backend/app/rules/catalog.json`). AI never decides PASS/FAIL verdicts or scores.
- **Tri-State Verdicts (No Guessing)**: Missing evidence yields `UNVERIFIED`, never an assumed pass. Unverified checks are factored into an "Evidence Coverage" metric and excluded from the compliance score.
- **Zero Raw Config Storage**: Raw files are processed strictly in-memory and discarded. Only normalized schemas and redacted evidence strings are persisted.
- **Advisory-Only AI**: AI is strictly optional and advisory (`services/ai_mapping.py`). It assists human administrators in categorizing unrecognized proprietary commands, requiring explicit human approval before filing.
- **Fail-Safe Frontend Architecture**: Protected by global `ErrorBoundary` wrappers, accessible live `Toast` notification queues, and responsive data tables.

---

## 🚀 Quick Start Guide

### Option A: 1-Command Docker Setup (Recommended)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/):

```bash
# 1. Clone the repository and enter directory
git clone https://github.com/rujutaphaltankar/netaudit.git
cd netaudit

# 2. Copy the environment configuration
cp .env.example .env

# 3. Build and launch all services (PostgreSQL, FastAPI Backend, React Frontend)
docker compose up --build
```

- **Web Application**: [`http://localhost:8080`](http://localhost:8080)
- **API Documentation**: [`http://localhost:8080/docs`](http://localhost:8080/docs)
- **Default Demo Accounts**:
  - **Administrator**: `admin` / `Admin@12345` (Full access: upload, delete, AI review, user admin)
  - **Viewer**: `viewer` / `Viewer@12345` (Read-only access: view dashboards, findings, reports)

---

### Option B: Local Native Setup (Without Docker)

#### Prerequisites
- **Python 3.10+**
- **Node.js 18+ & npm**

#### 1. Backend Service (FastAPI + SQLite)
```bash
# Enter backend directory
cd backend

# Create and activate virtual environment
# On Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
# python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Configure environment (defaults to SQLite + demo seeding)
cp .env.example .env

# Run database migrations (or let auto-bootstrap initialize)
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```
*Backend runs at `http://localhost:8000` (Swagger UI at `/docs`).*

#### 2. Frontend Service (Vite + React)
```bash
# Open a new terminal and enter frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```
*Frontend runs at `http://localhost:5100` (or `http://localhost:5173`).*

---

## 🎬 Step-by-Step Live Demo Script (5-Minute Presentation)

Use this structured script to present NetAudit smoothly during live evaluations or client demos:

| Step | Screen / Action | What to Demonstrate & Talk About |
|---|---|---|
| **1. Authentication** | Open `http://localhost:5100` | • Point out the **1-Click Quick Demo Login** buttons.<br>• Click **"Login as Administrator"** (`admin`).<br>• Mention role-based access control (RBAC): Admins audit and manage rules; Viewers are read-only. |
| **2. Posture Dashboard** | `/` (Dashboard) | • Review the **Overall Posture Status** banner ("Real-time security posture across all devices").<br>• Highlight the **Score Over Time** trend chart and **Failed Checks by Severity** bar chart.<br>• Notice the 4 pre-seeded realistic audit samples showing progress from vulnerable to hardened states. |
| **3. Run New Audit** | Click **"+ Run New Audit"** (`/audits/new`) | • Drag & drop `samples/cisco_ios_weak.cfg` into the upload zone.<br>• Leave vendor as **"Auto-detect"**.<br>• Click **"Run audit"** — explain that raw config is parsed in-memory with zero disk persistence. |
| **4. Audit Findings Deep Dive** | `/audits/<id>` | • **Score Ring & Grade**: Emphasize how a Critical failure automatically caps the grade at **D** regardless of other passes.<br>• **Findings Filters**: Click through `All`, `Fail`, `Unverified`, `Pass`.<br>• **Evidence & Remediation**: Expand the *Telnet Disabled* or *SNMP Community String* finding:<br>&nbsp;&nbsp;— Show the exact config line evidence (`L14  transport input telnet`).<br>&nbsp;&nbsp;— Show that secrets are `<redacted>`.<br>&nbsp;&nbsp;— Click **"📋 Copy fix"** to copy the ready-to-paste CLI remediation block.<br>• **Parsed Config Tab**: Demonstrate the live search bar (`ssh`, `logging`) and click **"📋 Copy JSON schema"**.<br>• **PDF Report**: Click **"Download PDF report"** — open the generated multi-page, executive-ready PDF report. |
| **5. Configuration Drift Analysis** | Click **"History"** (`/audits`) | • Checkbox the **weak Cisco audit** and the **hardened Cisco audit**.<br>• Click **"Compare selected (2/2)"**.<br>• Review the side-by-side comparison screen (`/audits/compare`):<br>&nbsp;&nbsp;— Show the **Score Delta Badge** (e.g. `+78 pts`).<br>&nbsp;&nbsp;— Filter by **"Differences"**, **"Improved"**, or **"Regressed"** to demonstrate configuration compliance drift. |
| **6. Negative Test & AI Review** | `/audits/new` & `/ai-review` | • Upload `samples/arista_eos_unsupported.cfg` → shows clear, friendly "Vendor not supported yet" validation.<br>• Visit `/ai-review` to show how unknown commands are mapped with human-in-the-loop oversight without altering deterministic scores. |

---

## 🛡️ Rule Catalog & Compliance Controls (19 Rules)

NetAudit enforces 19 enterprise security controls mapped against NIST SP 800-53 Rev. 5, ISO/IEC 27001:2022, and CIS Controls v8:

| Rule ID | Category | Severity | Description |
|---|---|---|---|
| `NET-MGMT-001` | Management Access | Critical | Telnet disabled across all terminal lines (`vty`) |
| `NET-MGMT-002` | Management Access | High | SSH enabled with secure version (`v2` only) |
| `NET-MGMT-003` | Management Access | High | Management access restricted via Access Control Lists (ACLs) |
| `NET-MGMT-004` | Management Access | Medium | Inactive session timeout configured (<= 15 minutes) |
| `NET-MGMT-005` | Management Access | Medium | Auxiliary (`aux`) port disabled when unused |
| `NET-MGMT-006` | Management Access | High | Insecure HTTP server disabled |
| `NET-MGMT-007` | Management Access | Medium | Secure HTTPS server enabled |
| `NET-AUTH-001` | Authentication | High | AAA authentication enabled for login access |
| `NET-AUTH-002` | Authentication | Medium | Centralized authentication servers (RADIUS/TACACS+) configured |
| `NET-AUTH-003` | Authentication | Critical | No default, cleartext, or weak passwords (e.g., Type 0/7) |
| `NET-AUTH-004` | Authentication | Medium | Authorized banner warning presented on login |
| `NET-LOG-001` | Logging | High | Remote Syslog host configured for external auditing |
| `NET-LOG-002` | Logging | Medium | Syslog logging level set to informational or debugging |
| `NET-LOG-003` | Logging | Medium | Timestamps enabled on all log messages |
| `NET-NTP-001` | Time Synchronization | High | Synchronized with reliable Network Time Protocol (NTP) servers |
| `NET-NTP-002` | Time Synchronization | Medium | NTP authentication enabled to prevent time manipulation |
| `NET-SNMP-001` | Monitoring | Critical | Default SNMP community strings (`public`, `private`) removed |
| `NET-SNMP-002` | Monitoring | High | SNMPv3 enforced (encryption + authentication enabled) |
| `NET-SNMP-003` | Monitoring | Medium | SNMP write access (`RW`) disabled or strictly restricted |

---

## 🧪 Testing & Quality Assurance

NetAudit maintains rigorous automated test suites across both backend and frontend:

```bash
# Run backend test suite (121 tests covering parsers, rules, auth, PDF generation, migrations)
cd backend
pytest

# Run frontend test suite (15 unit tests covering utilities, formatting, toasts, and drift comparison)
cd frontend
npm test

# Verify production frontend build & TypeScript static checks
npm run build
```

---

## 📁 Repository Structure

```
netaudit/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # REST API routes (audits, auth, configs, health, rules, users)
│   │   ├── core/           # Security, JWT tokens, rate limiting, and app settings
│   │   ├── db/             # SQLAlchemy database models, sessions, and bootstrap seeders
│   │   ├── parsers/        # Cisco IOS & Juniper Junos AST parsers, redaction engine
│   │   ├── rules/          # 19-rule catalog.json, evaluation engine, tri-state operators
│   │   ├── schemas/        # Pydantic v2 data transfer schemas and contracts
│   │   └── services/       # Audit execution, PDF reporting (ReportLab), AI mapping
│   ├── tests/              # 121 comprehensive pytest unit & integration tests
│   └── migrations/         # Alembic database schema migrations
├── frontend/
│   ├── src/
│   │   ├── api/            # Typed API client with automatic token attachment
│   │   ├── auth/           # React AuthContext, session storage, and route guards
│   │   ├── components/     # FindingCard, ParsedConfig, ErrorBoundary, Toast, ScoreRing
│   │   ├── context/        # ToastContext notification dispatch system
│   │   ├── pages/          # Dashboard, NewAudit, AuditDetail, History, Compare, Rules
│   │   └── lib/            # UI helpers, status styling, and math calculations
│   └── index.html          # HTML entry point with IBM Plex typography
├── samples/                # Reference test configs (Cisco/Junos weak & hardened, Arista unsupported)
├── docs/                   # ARCHITECTURE.md, USER_GUIDE.md, SECURITY.md, DEMO_SCRIPT.md
├── docker-compose.yml      # Multi-container orchestration (PostgreSQL, Backend, Frontend)
└── README.md               # You are here
```

---

## 📄 License & Disclaimer

- **License**: MIT License. See [LICENSE](LICENSE) for details.
- **Compliance Disclaimer**: NetAudit provides automated configuration analysis against selected best-practice baselines. An audit score or passing finding does not constitute a formal regulatory certification (such as official ISO/IEC 27001 or PCI-DSS certification).
