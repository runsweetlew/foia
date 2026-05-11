import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// In-memory rate limiter: Map<apiKeyId, { count, windowStart }>
const rateLimitMap = new Map<
  string,
  { count: number; windowStart: number }
>();
const WINDOW_MS = 60_000; // 1 minute

function checkRateLimit(
  keyId: string,
  limit: number
): { allowed: boolean; remaining: number; resetAt: number } {
  const now = Date.now();
  const entry = rateLimitMap.get(keyId);

  if (!entry || now - entry.windowStart >= WINDOW_MS) {
    rateLimitMap.set(keyId, { count: 1, windowStart: now });
    return { allowed: true, remaining: limit - 1, resetAt: now + WINDOW_MS };
  }

  if (entry.count >= limit) {
    return {
      allowed: false,
      remaining: 0,
      resetAt: entry.windowStart + WINDOW_MS,
    };
  }

  entry.count++;
  return {
    allowed: true,
    remaining: limit - entry.count,
    resetAt: entry.windowStart + WINDOW_MS,
  };
}

type ApiHandler = (
  request: NextRequest,
  context?: any
) => Promise<NextResponse | Response>;

export function withApiKey(handler: ApiHandler): ApiHandler {
  return async (request, context) => {
    const apiKey = request.headers.get("x-api-key");

    if (!apiKey) {
      return NextResponse.json(
        { error: "Missing API key. Provide an X-API-Key header." },
        { status: 401 }
      );
    }

    const keyRecord = await prisma.apiKey.findUnique({
      where: { key: apiKey },
    });

    if (!keyRecord || !keyRecord.isActive) {
      return NextResponse.json(
        { error: "Invalid or inactive API key." },
        { status: 403 }
      );
    }

    const { allowed, remaining, resetAt } = checkRateLimit(
      keyRecord.id,
      keyRecord.rateLimit
    );

    if (!allowed) {
      return NextResponse.json(
        { error: "Rate limit exceeded. Try again later." },
        {
          status: 429,
          headers: {
            "X-RateLimit-Limit": String(keyRecord.rateLimit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": String(Math.ceil(resetAt / 1000)),
            "Retry-After": String(Math.ceil((resetAt - Date.now()) / 1000)),
          },
        }
      );
    }

    // Update lastUsedAt (fire-and-forget)
    prisma.apiKey
      .update({
        where: { id: keyRecord.id },
        data: { lastUsedAt: new Date() },
      })
      .catch(() => {});

    const response = await handler(request, context);

    // Add rate limit headers
    if (response instanceof NextResponse) {
      response.headers.set("X-RateLimit-Limit", String(keyRecord.rateLimit));
      response.headers.set("X-RateLimit-Remaining", String(remaining));
      response.headers.set(
        "X-RateLimit-Reset",
        String(Math.ceil(resetAt / 1000))
      );
    }

    return response;
  };
}
