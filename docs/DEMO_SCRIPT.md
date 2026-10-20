# 5-minute demo script
1. `docker compose up --build` → open http://localhost:8080 → sign in as **admin**.
2. **Dashboard:** 4 seeded audits, score trend (weak → hardened), failures by severity.
3. **New audit:** upload `samples/cisco_ios_weak.cfg` → score ~10, grade F. Open the Telnet/SNMP findings: show evidence lines, `<redacted>` secrets, copy the fix.
4. Point out **Unverified** findings: "missing evidence is never a pass".
5. **Unrecognized commands → Suggest meanings → Approve** (explain advisory, human-in-the-loop, score unchanged).
6. **Download PDF report.** 7. **History → select weak vs hardened → Compare.**
8. Sign out, sign in as **viewer**: read-only (no upload/delete/users).
9. Upload `arista_eos_unsupported.cfg` → clear "not supported yet" error.
10. Show `docs/ARCHITECTURE.md` and run `python -m pytest -q` (121 passing).
