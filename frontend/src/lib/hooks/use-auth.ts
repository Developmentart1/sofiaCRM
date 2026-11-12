"use client";

import { useCallback, useEffect, useState } from "react";
import { authApi } from "@/lib/api/auth";
import { ApiClientError } from "@/lib/api/client";
import type { LoginPayload, SignupPayload, User } from "@/lib/types/api";
import { toast } from "./use-toast";

// The JWT is held in an HttpOnly cookie (set by the backend on login).
// The frontend only tracks the current user; "authenticated" == user known.
interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
}

let memoryState: AuthState = { user: null, loading: true, error: null };
const listeners = new Set<(s: AuthState) => void>();

function setState(next: AuthState) {
  memoryState = next;
  listeners.forEach((l) => l(memoryState));
}

export function useAuth() {
  const [state, setLocal] = useState<AuthState>(memoryState);
  useEffect(() => {
    const l = (s: AuthState) => setLocal(s);
    listeners.add(l);
    return () => { listeners.delete(l); };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const user = await authApi.me();
      setState({ user, loading: false, error: null });
    } catch {
      setState({ user: null, loading: false, error: null });
    }
  }, []);

  useEffect(() => {
    if (memoryState.loading) {
      void refresh();
    }
  }, [refresh]);

  const login = useCallback(async (payload: LoginPayload) => {
    setState({ ...memoryState, loading: true, error: null });
    try {
      const res = await authApi.login(payload);
      setState({ user: res.user, loading: false, error: null });
      toast.success("Sesión iniciada");
      return res;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error de autenticación";
      setState({ user: null, loading: false, error: msg });
      toast.error(msg);
      throw err;
    }
  }, []);

  const signup = useCallback(async (payload: SignupPayload) => {
    setState({ ...memoryState, loading: true, error: null });
    try {
      const { slug } = await authApi.signup(payload);
      const session = await authApi.login({
        organization_slug: slug,
        email: payload.email,
        password: payload.password,
      });
      setState({ user: session.user, loading: false, error: null });
      toast.success("Cuenta creada");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 409) {
        try {
          const slug = authApi.slugify(payload.organization_name);
          const session = await authApi.loginCompany({
            organization_slug: slug,
            password: payload.password,
          });
          setState({ user: session.user, loading: false, error: null });
          toast.success("Sesión iniciada en la empresa existente");
          return;
        } catch {
          err = new Error("La empresa ya existe, pero la contraseña no coincide. Usa Iniciar sesión.");
        }
      }
      const msg = err instanceof Error ? err.message : "Error al crear la cuenta";
      setState({ user: null, loading: false, error: msg });
      toast.error(msg);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setState({ user: null, loading: false, error: null });
  }, []);

  return {
    user: memoryState.user,
    isAuthenticated: !!memoryState.user,
    loading: memoryState.loading,
    error: memoryState.error,
    login,
    signup,
    logout,
    refresh,
  };
}
