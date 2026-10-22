import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center p-6 text-center">
          <div className="max-w-md rounded-xl border border-crit/30 bg-paper p-8 shadow-md">
            <span className="grid size-12 place-items-center rounded-full bg-crit-wash text-2xl font-bold text-crit mx-auto mb-4">
              !
            </span>
            <h2 className="text-xl font-bold text-ink">Something went wrong</h2>
            <p className="mt-2 text-sm text-muted">
              An unexpected interface error occurred. NetAudit protected the application state from collapsing.
            </p>
            {this.state.error && (
              <pre className="mt-4 max-h-32 overflow-x-auto rounded bg-mist p-2.5 text-left font-mono text-xs text-crit">
                {this.state.error.message}
              </pre>
            )}
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="rounded-lg bg-signal px-4 py-2 text-xs font-semibold text-white hover:bg-signal-dark transition-colors"
              >
                Reload page
              </button>
              <button
                type="button"
                onClick={() => {
                  this.setState({ hasError: false, error: null });
                  window.location.href = "/";
                }}
                className="rounded-lg border border-line bg-paper px-4 py-2 text-xs font-medium text-ink hover:bg-mist transition-colors"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
