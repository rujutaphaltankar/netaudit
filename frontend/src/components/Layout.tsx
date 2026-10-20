import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { cn } from "../lib/ui";
import HealthBadge from "./HealthBadge";

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden>
        <path d="M16 2 4 7v8c0 7.2 5 13.3 12 15 7-1.7 12-7.8 12-15V7L16 2Z" fill="#0e7c86" />
        <path d="M9 12h14M9 16.5h14M9 21h8" stroke="#dff0f1" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className="text-lg font-semibold tracking-tight text-white">NetAudit</span>
    </div>
  );
}

export default function Layout() {
  const { user, isAdmin, signOut } = useAuth();
  const { pathname } = useLocation();
  const links = [
    { to: "/", label: "Dashboard", active: pathname === "/" },
    { to: "/audits/new", label: "New audit", active: pathname === "/audits/new" },
    { to: "/audits", label: "History", active: pathname.startsWith("/audits") && pathname !== "/audits/new" },
    { to: "/rules", label: "Rules library", active: pathname === "/rules" },
    { to: "/ai-review", label: "AI review", active: pathname === "/ai-review" },
    ...(isAdmin ? [{ to: "/users", label: "Users", active: pathname === "/users" }] : []),
  ];

  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-ink md:sticky md:top-0 md:flex md:h-screen md:w-60 md:shrink-0 md:flex-col">
        <div className="flex items-center justify-between px-5 py-4 md:block md:py-6">
          <Logo />
          <p className="mt-2 hidden text-xs leading-snug text-white/55 md:block">Network configuration security compliance auditor</p>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-visible md:pb-0">
          {links.map((l) => (
            <NavLink
              key={l.to} to={l.to} end
              className={cn(
                "whitespace-nowrap rounded-md border-l-2 px-3 py-2 text-sm transition-colors",
                l.active ? "border-signal bg-white/10 font-medium text-white" : "border-transparent text-white/70 hover:bg-white/5 hover:text-white",
              )}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden space-y-4 border-t border-white/10 p-5 md:block">
          <HealthBadge />
          <div className="text-sm">
            <div className="font-medium text-white">{user?.username}</div>
            <div className="text-xs text-white/55">{user?.role === "admin" ? "Administrator" : "Viewer (read-only)"}</div>
            <button onClick={signOut} className="mt-2 text-xs text-white/70 underline underline-offset-2 hover:text-white">Sign out</button>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-white/10 px-5 py-2 text-xs text-white/70 md:hidden">
          <span>{user?.username} · {user?.role}</span>
          <button onClick={signOut} className="underline">Sign out</button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-10 md:py-9">
        <div className="mx-auto max-w-6xl"><Outlet /></div>
      </main>
    </div>
  );
}
