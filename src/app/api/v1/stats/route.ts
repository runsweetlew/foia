import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(async () => {
  const [totalEntities, totalMeetings, totalDocuments, totalCounties, latestMeeting] =
    await Promise.all([
      prisma.entity.count(),
      prisma.meeting.count(),
      prisma.document.count(),
      prisma.county.count(),
      prisma.meeting.findFirst({ orderBy: { scrapedAt: "desc" } }),
    ]);

  const typeCounts = await prisma.entity.groupBy({
    by: ["type"],
    _count: true,
  });

  return NextResponse.json({
    data: {
      totalCounties,
      totalEntities,
      totalMeetings,
      totalDocuments,
      lastUpdate: latestMeeting?.scrapedAt || null,
      entityTypeCounts: Object.fromEntries(
        typeCounts.map((tc) => [tc.type, tc._count])
      ),
    },
  });
});
