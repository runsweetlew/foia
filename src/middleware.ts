import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "foia-dev-secret-change-in-production"
);
const COOKIE_NAME = "foia_session";

export async function middleware(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;

  if (!token) {
    if (request.nextUrl.pathname.startsWith("/api/settings")) {
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
    if (request.nextUrl.pathname.startsWith("/api/settings")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: ["/settings/:path*", "/api/settings/:path*"],
};
