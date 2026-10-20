import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Button, ErrorNote, fieldCls } from "../components/ui";

const SHOW_HINT = import.meta.env.VITE_SHOW_DEMO_HINT === "true";

export default function Login() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="flex flex-col justify-between bg-ink p-8 text-white lg:p-14">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden>
            <path d="M16 2 4 7v8c0 7.2 5 13.3 12 15 7-1.7 12-7.8 12-15V7L16 2Z" fill="#0e7c86" />
            <path d="M9 12h14M9 16.5h14M9 21h8" stroke="#dff0f1" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className="text-lg font-semibold">NetAudit</span>
        </div>
        <div className="my-12 max-w-xl">
          <h1 className="text-3xl font-semibold leading-tight text-white lg:text-4xl">Know what is weak in a router config before an attacker does.</h1>
          <p className="mt-4 text-white/70">
            Upload a Cisco IOS or Juniper Junos configuration. NetAudit checks 19 security rules, shows the exact line behind every finding, and gives the fix.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-white/80">
            <li>Missing evidence is reported as unverified, never as compliant.</li>
            <li>Secrets are redacted before anything is stored.</li>
            <li>AI suggestions are advisory and need human approval.</li>
          </ul>
        </div>
        <p className="font-mono text-xs text-white/40">telnet=enabled · snmp.community=public · ssh.version=1</p>
      </section>

      <section className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <h2 className="text-2xl font-semibold">Sign in</h2>
          <label className="block text-sm font-medium text-ink">
            Username
            <input className={`${fieldCls} mt-1`} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required maxLength={64} />
          </label>
          <label className="block text-sm font-medium text-ink">
            Password
            <input className={`${fieldCls} mt-1`} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required maxLength={128} />
          </label>
          <ErrorNote error={error} />
          <Button variant="primary" type="submit" disabled={busy} className="w-full">{busy ? "Signing in…" : "Sign in"}</Button>
          {SHOW_HINT && (
            <p className="rounded-md bg-signal-wash p-3 text-xs text-signal-dark">
              Demo accounts: <b>admin</b> / Admin@12345 (full access) and <b>viewer</b> / Viewer@12345 (read-only).
            </p>
          )}
        </form>
      </section>
    </div>
  );
}
