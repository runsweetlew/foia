import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const [totalEntities, activeEntities, totalMeetings, latestMeeting] =
    await Promise.all([
      prisma.entity.count(),
      prisma.entity.count({ where: { scrapeStatus: "ACTIVE" } }),
      prisma.meeting.count(),
      prisma.meeting.findFirst({ orderBy: { scrapedAt: "desc" } }),
    ]);

  const typeCounts = await prisma.entity.groupBy({
    by: ["type"],
    _count: true,
  });

  return NextResponse.json({
    totalEntities,
    activeEntities,
    totalMeetings,
    lastUpdate: latestMeeting?.scrapedAt || null,
    entityTypeCounts: Object.fromEntries(
      typeCounts.map((tc) => [tc.type, tc._count])
    ),
  });
}
