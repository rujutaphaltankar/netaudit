import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { cn } from "../lib/ui";
import HealthBadge from "./HealthBadge";

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid size-8 place-items-center rounded-lg bg-signal shadow-xs">
        <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden>
          <path d="M16 2 4 7v8c0 7.2 5 13.3 12 15 7-1.7 12-7.8 12-15V7L16 2Z" fill="#ffffff" />
          <path d="M9 12h14M9 16.5h14M9 21h8" stroke="#0e7c86" strokeWidth="2.2" strokeLinecap="round" />
        </svg>
      </div>
      <div>
        <span className="text-base font-bold tracking-tight text-white block leading-tight">NetAudit</span>
        <span className="text-[10px] text-white/50 block font-mono">v1.0.0 · Core</span>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, isAdmin, signOut } = useAuth();
  const { pathname } = useLocation();

  const links = [
    { to: "/", label: "Dashboard", icon: "📊", active: pathname === "/" },
    { to: "/audits/new", label: "New audit", icon: "➕", active: pathname === "/audits/new" },
    { to: "/audits", label: "History", icon: "📁", active: pathname.startsWith("/audits") && pathname !== "/audits/new" },
    { to: "/rules", label: "Rules library", icon: "📖", active: pathname === "/rules" },
    { to: "/ai-review", label: "AI review", icon: "✨", active: pathname === "/ai-review" },
    ...(isAdmin ? [{ to: "/users", label: "Users", icon: "👥", active: pathname === "/users" }] : []),
  ];

  const userInitial = user?.username ? user.username.charAt(0).toUpperCase() : "U";

  return (
    <div className="min-h-screen md:flex bg-mist/60">
      <aside className="bg-ink md:sticky md:top-0 md:flex md:h-screen md:w-60 md:shrink-0 md:flex-col shadow-lg z-20">
        <div className="flex items-center justify-between px-5 py-4 md:block md:py-6">
          <Logo />
          <p className="mt-2.5 hidden text-xs leading-relaxed text-white/60 md:block">
            Network configuration compliance & posture auditor
          </p>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:overflow-visible md:pb-0">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end
              className={cn(
                "flex items-center gap-2.5 whitespace-nowrap rounded-lg border-l-2 px-3 py-2.5 text-xs font-medium transition-all",
                l.active
                  ? "border-signal bg-white/10 font-semibold text-white shadow-xs"
                  : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
              )}
            >
              <span className="text-sm opacity-90">{l.icon}</span>
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="hidden space-y-4 border-t border-white/10 p-5 md:block bg-black/10">
          <HealthBadge />
          <div className="flex items-center gap-3">
            <span className="grid size-8 place-items-center rounded-full bg-signal/20 text-xs font-bold text-signal border border-signal/30">
              {userInitial}
            </span>
            <div className="min-w-0 flex-1 text-xs">
              <div className="font-semibold text-white truncate">{user?.username}</div>
              <div className="text-[11px] text-white/50">{user?.role === "admin" ? "Administrator" : "Viewer (read-only)"}</div>
            </div>
            <button
              onClick={signOut}
              className="text-xs text-white/60 hover:text-white underline underline-offset-2 transition-colors cursor-pointer"
              title="Sign out"
            >
              Exit
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-white/10 px-5 py-2 text-xs text-white/70 md:hidden bg-black/20">
          <span className="font-medium">
            {user?.username} · {user?.role}
          </span>
          <button onClick={signOut} className="underline text-signal-wash">
            Sign out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-10 md:py-9">
        <div className="mx-auto max-w-6xl">{<Outlet />}</div>
      </main>
    </div>
  );
}
