import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";
import type { Prisma } from "@/generated/prisma";

export const GET = withApiKey(async (request: NextRequest) => {
  const sp = request.nextUrl.searchParams;
  const entityId = sp.get("entityId") || undefined;
  const county = sp.get("county") || undefined;
  const entityType = sp.get("entityType") || undefined;
  const from = sp.get("from") || undefined;
  const to = sp.get("to") || undefined;
  const page = Math.max(1, parseInt(sp.get("page") || "1"));
  const limit = Math.min(Math.max(1, parseInt(sp.get("limit") || "20")), 100);

  const where: Prisma.MeetingWhereInput = {};
  if (entityId) where.entityId = entityId;
  if (county || entityType) {
    where.entity = {};
    if (county) where.entity.county = { name: county };
    if (entityType) where.entity.type = entityType as any;
  }
  if (from || to) {
    where.meetingDate = {};
    if (from) (where.meetingDate as any).gte = new Date(from);
    if (to) (where.meetingDate as any).lte = new Date(to);
  }

  const [meetings, total] = await Promise.all([
    prisma.meeting.findMany({
      where,
      orderBy: { meetingDate: "desc" },
      skip: (page - 1) * limit,
      take: limit,
      select: {
        id: true,
        title: true,
        meetingDate: true,
        committeeName: true,
        meetingType: true,
        status: true,
        sourceUrl: true,
        pdfUrl: true,
        pageCount: true,
        entity: {
          select: {
            id: true,
            name: true,
            slug: true,
            type: true,
            county: { select: { name: true } },
          },
        },
      },
    }),
    prisma.meeting.count({ where }),
  ]);

  return NextResponse.json({
    data: meetings.map((m) => ({
      id: m.id,
      title: m.title,
      meetingDate: m.meetingDate,
      committeeName: m.committeeName,
      meetingType: m.meetingType,
      status: m.status,
      sourceUrl: m.sourceUrl,
      pdfUrl: m.pdfUrl,
      pageCount: m.pageCount,
      entityId: m.entity.id,
      entityName: m.entity.name,
      entitySlug: m.entity.slug,
      entityType: m.entity.type,
      county: m.entity.county.name,
    })),
    pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
  });
});
