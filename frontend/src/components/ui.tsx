import { useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { cn, SEVERITY_STYLE, STATUS_LABEL, STATUS_STYLE } from "../lib/ui";
import type { FindingStatus, Severity } from "../types";

export function Card({ title, action, children, className }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border border-line bg-paper p-5", className)}>
      {(title || action) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-base font-semibold">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

const chip = "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium";
export const SeverityBadge = ({ severity }: { severity: Severity }) => <span className={cn(chip, SEVERITY_STYLE[severity])}>{severity}</span>;
export const StatusBadge = ({ status }: { status: FindingStatus }) => <span className={cn(chip, STATUS_STYLE[status])}>{STATUS_LABEL[status]}</span>;
export const Chip = ({ children, tone = "bg-unk-wash text-unk" }: { children: ReactNode; tone?: string }) => <span className={cn(chip, tone)}>{children}</span>;

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" };
export function Button({ variant = "secondary", className, ...p }: BtnProps) {
  const styles = {
    primary: "bg-signal text-white hover:bg-signal-dark",
    secondary: "border border-line bg-paper text-ink hover:bg-mist",
    danger: "border border-crit/30 bg-paper text-crit hover:bg-crit-wash",
  }[variant];
  return <button type="button" {...p} className={cn("rounded-md px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50", styles, className)} />;
}

export const inputCls = "rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink placeholder:text-muted/70";
export const fieldCls = `w-full ${inputCls}`;

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-6 text-sm text-muted">
      <span className="size-4 animate-spin rounded-full border-2 border-line border-t-signal" />
      {label}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const msg = error instanceof ApiError ? error.message : "Something went wrong.";
  const code = error instanceof ApiError ? error.code : null;
  return (
    <div role="alert" className="rounded-md border border-crit/25 bg-crit-wash p-3 text-sm text-crit">
      {msg}
      {code && <span className="ml-2 font-mono text-xs opacity-70">[{code}]</span>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line p-8 text-center text-sm text-muted">{children}</p>;
}

/** Small data-loading hook: { data, error, loading, reload }. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    fn()
      .then((d) => alive && (setData(d), setError(null)))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}
