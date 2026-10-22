import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  show: (message: string, type?: ToastType, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
  warning: (message: string, duration?: number) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, type: ToastType = "info", duration = 3500) => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    if (duration > 0) {
      setTimeout(() => {
        dismiss(id);
      }, duration);
    }
  }, [dismiss]);

  const success = useCallback((message: string, duration?: number) => show(message, "success", duration), [show]);
  const error = useCallback((message: string, duration?: number) => show(message, "error", duration), [show]);
  const info = useCallback((message: string, duration?: number) => show(message, "info", duration), [show]);
  const warning = useCallback((message: string, duration?: number) => show(message, "warning", duration), [show]);

  return (
    <ToastContext.Provider value={{ show, success, error, info, warning, dismiss }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-5 right-5 z-50 flex max-w-sm flex-col gap-2 pointer-events-none"
      >
        {toasts.map((t) => {
          const styles = {
            success: "border-pass/40 bg-white text-ink shadow-lg ring-1 ring-pass/20",
            error: "border-crit/40 bg-white text-ink shadow-lg ring-1 ring-crit/20",
            warning: "border-high/40 bg-white text-ink shadow-lg ring-1 ring-high/20",
            info: "border-signal/40 bg-white text-ink shadow-lg ring-1 ring-signal/20",
          }[t.type];

          const icon = {
            success: (
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-pass-wash text-pass font-bold text-xs">
                ✓
              </span>
            ),
            error: (
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-crit-wash text-crit font-bold text-xs">
                ✕
              </span>
            ),
            warning: (
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-high-wash text-high font-bold text-xs">
                !
              </span>
            ),
            info: (
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-signal-wash text-signal font-bold text-xs">
                ℹ
              </span>
            ),
          }[t.type];

          return (
            <div
              key={t.id}
              role="status"
              className={`pointer-events-auto flex items-start gap-3 rounded-lg border p-3.5 text-sm transition-all animate-in fade-in slide-in-from-bottom-2 ${styles}`}
            >
              {icon}
              <div className="flex-1 text-xs font-medium leading-relaxed">{t.message}</div>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="text-muted hover:text-ink text-xs transition-colors p-0.5"
                aria-label="Dismiss toast"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}
