import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as api from "../api/client";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!api.getToken());

  const signOut = useCallback(() => {
    api.setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (api.getToken()) {
      api.getMe().then(setUser).catch(signOut).finally(() => setLoading(false));
    }
    window.addEventListener(api.UNAUTHORIZED_EVENT, signOut);
    return () => window.removeEventListener(api.UNAUTHORIZED_EVENT, signOut);
  }, [signOut]);

  const signIn = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    api.setToken(res.access_token);
    setUser(res.user);
  }, []);

  const value = useMemo(() => ({ user, loading, isAdmin: user?.role === "admin", signIn, signOut }), [user, loading, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
