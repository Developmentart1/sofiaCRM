import { api } from "./client";
import type { LoginPayload, SignupPayload, User } from "@/lib/types/api";

// Session is cookie-based (HttpOnly `access_token` cookie). The frontend
// never holds the JWT in memory — the cookie is the single source of truth.
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function slugify(name: string): string {
  const slug = name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  return slug.length >= 2 ? slug : `org-${Date.now()}`;
}

export const authApi = {
  slugify,
  async login(payload: LoginPayload): Promise<AuthResponse> {
    return api.post<AuthResponse>("/api/users/login", payload);
  },

  async loginCompany(payload: { organization_slug: string; password: string }): Promise<AuthResponse> {
    return api.post<AuthResponse>("/api/users/login/company", payload);
  },

  async signup(payload: SignupPayload): Promise<{ slug: string }> {
    // El backend exige OrganizationCreate (name, slug, admin_email, ...) con
    // extra="forbid"; el slug se deriva del nombre de la organización.
    const slug = slugify(payload.organization_name);
    await api.post("/api/organizations/bootstrap", {
      name: payload.organization_name.trim(),
      slug,
      admin_email: payload.email.trim(),
      admin_password: payload.password,
      admin_full_name: payload.full_name.trim(),
    });
    return { slug };
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
