import { useState, type FormEvent } from "react";
import { createUser, listUsers, updateUser } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, Chip, ErrorNote, PageHeader, Spinner, fieldCls, useAsync } from "../components/ui";
import { formatDate } from "../lib/ui";
import type { Role } from "../types";

export default function Users() {
  const { user: me } = useAuth();
  const { data, error, loading, reload } = useAsync(listUsers, []);
  const [form, setForm] = useState({ username: "", password: "", role: "viewer" as Role });
  const [formError, setFormError] = useState<unknown>(null);
  const [rowError, setRowError] = useState<unknown>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try { await createUser(form.username, form.password, form.role); setForm({ username: "", password: "", role: "viewer" }); reload(); } catch (err) { setFormError(err); }
  }
  async function patch(id: number, p: { is_active?: boolean; role?: Role }) {
    setRowError(null);
    try { await updateUser(id, p); reload(); } catch (err) { setRowError(err); }
  }

  if (loading && !data) return <Spinner />;
  return (
    <>
      <PageHeader title="Users" subtitle="Administrators can upload, delete and approve. Viewers have read-only access." />
      <ErrorNote error={error} />
      <Card title="Add a user" className="mb-5 max-w-3xl">
        <form onSubmit={add} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-end">
          <label className="text-sm font-medium text-ink">Username<input className={`${fieldCls} mt-1`} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required pattern="[A-Za-z0-9_.\-]{3,64}" title="3–64 letters, digits, . _ -" /></label>
          <label className="text-sm font-medium text-ink">Password<input className={`${fieldCls} mt-1`} type="password" minLength={8} maxLength={128} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required autoComplete="new-password" /></label>
          <label className="text-sm font-medium text-ink">Role<select className={`${fieldCls} mt-1`} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}><option value="viewer">Viewer</option><option value="admin">Admin</option></select></label>
          <Button variant="primary" type="submit">Add</Button>
        </form>
        <div className="mt-3"><ErrorNote error={formError} /></div>
      </Card>
      <ErrorNote error={rowError} />
      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="border-b border-line text-xs text-muted"><tr><th className="p-3">User</th><th className="p-3">Role</th><th className="p-3">Status</th><th className="p-3">Created</th><th className="p-3" /></tr></thead>
          <tbody className="divide-y divide-line">
            {data?.map((u) => (
              <tr key={u.id}>
                <td className="p-3 font-medium text-ink">{u.username}{u.id === me?.id && <span className="ml-2 text-xs text-muted">(you)</span>}</td>
                <td className="p-3">{u.role}</td>
                <td className="p-3">{u.is_active ? <Chip tone="bg-pass-wash text-pass">active</Chip> : <Chip>disabled</Chip>}</td>
                <td className="p-3 text-muted">{formatDate(u.created_at)}</td>
                <td className="flex justify-end gap-2 p-3">
                  {u.id !== me?.id && <>
                    <Button onClick={() => patch(u.id, { role: u.role === "admin" ? "viewer" : "admin" })}>Make {u.role === "admin" ? "viewer" : "admin"}</Button>
                    <Button variant={u.is_active ? "danger" : "secondary"} onClick={() => patch(u.id, { is_active: !u.is_active })}>{u.is_active ? "Disable" : "Enable"}</Button>
                  </>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
