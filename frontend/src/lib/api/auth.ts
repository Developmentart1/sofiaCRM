import { api } from "./client";
import type { LoginPayload, SignupPayload, User } from "@/lib/types/api";

// Session is cookie-based (HttpOnly `access_token` cookie). The frontend
// never holds the JWT in memory — the cookie is the single source of truth.
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  async login(payload: LoginPayload): Promise<AuthResponse> {
    return api.post<AuthResponse>("/api/users/login", payload);
  },

  async signup(payload: SignupPayload): Promise<void> {
    await api.post("/api/organizations/bootstrap", payload);
  },

  async logout(): Promise<void> {
    try {
      await api.post("/api/users/logout");
    } catch {
      // Ignore network errors on logout; the cookie is cleared client-side
      // by the backend, and the middleware will redirect if it lingers.
    }
  },

  async me(): Promise<User> {
    return api.get<User>("/api/users/me");
  },
};
