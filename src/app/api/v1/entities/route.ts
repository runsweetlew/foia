import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";
import type { Prisma } from "@/generated/prisma";

export const GET = withApiKey(async (request: NextRequest) => {
  const sp = request.nextUrl.searchParams;
  const type = sp.get("type") || undefined;
  const county = sp.get("county") || undefined;
  const page = Math.max(1, parseInt(sp.get("page") || "1"));
  const limit = Math.min(Math.max(1, parseInt(sp.get("limit") || "20")), 100);

  const where: Prisma.EntityWhereInput = {};
  if (type) where.type = type as any;
  if (county) where.county = { name: county };

  const [entities, total] = await Promise.all([
    prisma.entity.findMany({
      where,
      orderBy: { name: "asc" },
      skip: (page - 1) * limit,
      take: limit,
      select: {
        id: true,
        name: true,
        slug: true,
        type: true,
        platform: true,
        county: { select: { name: true } },
        websiteUrl: true,
        population: true,
        isCharter: true,
        foiaOfficerName: true,
        foiaOfficerEmail: true,
        _count: { select: { meetings: true, documents: true } },
      },
    }),
    prisma.entity.count({ where }),
  ]);

  return NextResponse.json({
    data: entities.map((e) => ({
      id: e.id,
      name: e.name,
      slug: e.slug,
      type: e.type,
      platform: e.platform,
      county: e.county.name,
      websiteUrl: e.websiteUrl,
      population: e.population,
      isCharter: e.isCharter,
      foiaOfficerName: e.foiaOfficerName,
      foiaOfficerEmail: e.foiaOfficerEmail,
      meetingCount: e._count.meetings,
      documentCount: e._count.documents,
    })),
    pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
  });
});
