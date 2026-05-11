import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "foia-dev-secret-change-in-production"
);
const COOKIE_NAME = "foia_session";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public API v1: early reject if missing API key (docs are public)
  if (pathname.startsWith("/api/v1/")) {
    if (
      pathname === "/api/v1/docs" ||
      pathname === "/api/v1/openapi.json"
    ) {
      return NextResponse.next();
    }
    const apiKey = request.headers.get("x-api-key");
    if (!apiKey) {
      return NextResponse.json(
        { error: "Missing API key. Provide an X-API-Key header." },
        { status: 401 }
      );
    }
    return NextResponse.next();
  }

  // Admin settings routes: JWT auth
  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    if (pathname.startsWith("/api/settings")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(token, JWT_SECRET);
    const userId = payload.userId as string;
    if (!userId) throw new Error("no userId");

    const response = NextResponse.next();
    response.headers.set("x-user-id", userId);
    return response;
  } catch {
    if (pathname.startsWith("/api/settings")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/settings/:path*", "/api/settings/:path*", "/api/v1/:path*"],
};
