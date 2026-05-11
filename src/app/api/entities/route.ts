import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import type { EntityType } from "@/generated/prisma";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const type = searchParams.get("type") as EntityType | null;
  const county = searchParams.get("county") || undefined;
  const page = parseInt(searchParams.get("page") || "1");
  const limit = Math.min(parseInt(searchParams.get("limit") || "20"), 50);

  const where: any = {};
  if (type) where.type = type;
  if (county) where.county = { name: county };

  const [entities, total] = await Promise.all([
    prisma.entity.findMany({
      where,
      orderBy: { name: "asc" },
      skip: (page - 1) * limit,
      take: limit,
      include: {
        county: true,
        _count: { select: { meetings: true } },
      },
    }),
    prisma.entity.count({ where }),
  ]);

  return NextResponse.json({
    entities,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  });
}
