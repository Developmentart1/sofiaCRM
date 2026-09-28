import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "access_token";

// NOTE: Next.js statically parses `config.matcher` — it must be an inline array
// literal. Referencing a variable makes Next ignore the whole `config` export
// ("Unknown identifier ... at config.matcher"), and the middleware then runs on
// EVERY route: /login redirects to itself (infinite loop) and /api/* is
// swallowed by the auth redirect instead of reaching the rewrite proxy.
//
// All matched paths belong to the `(authed)` route group; route-group segments
// are stripped from the URL, so the concrete paths are listed below.

export function middleware(request: NextRequest) {
  const hasToken = Boolean(request.cookies.get(AUTH_COOKIE)?.value);
  if (hasToken) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/contacts/:path*",
    "/companies/:path*",
    "/opportunities/:path*",
    "/pipelines/:path*",
    "/tasks/:path*",
    "/activities/:path*",
    "/documents/:path*",
    "/reports/:path*",
    "/settings/:path*",
  ],
};
