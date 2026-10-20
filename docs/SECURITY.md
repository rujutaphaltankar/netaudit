# Security notes
- **AuthN/Z:** JWT (HS256, 60 min), scrypt password hashing, role checks on every write endpoint, identical error for bad user/password, login rate limit (10/min/IP), upload rate limit.
- **Production guard:** with `ENVIRONMENT=production` the app refuses to start without a strong `JWT_SECRET` and `ADMIN_PASSWORD`.
- **Data minimisation:** raw configs are never stored; secrets are redacted in evidence; the AI provider only receives redacted single commands (never the full file or hostname).
- **AI safety:** command text is treated as untrusted data; model output is schema-validated; invalid output falls back to deterministic heuristics; output cannot change verdicts.
- **Upload validation:** extension allow-list, size limit, binary/encoding checks.
- **Web:** nginx sets CSP, X-Frame-Options, nosniff; CORS restricted to configured origins; SQLAlchemy parameterised queries; PDF text is escaped.
- **Known limitations:** token kept in `sessionStorage` (an httpOnly cookie would resist XSS better); rate limiter is in-memory (single instance); no MFA/password-reset; framework mappings are the authors' interpretation and should be verified against official documents.
