import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(
  async (
    _request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
  ) => {
    const { id } = await params;

    const meeting = await prisma.meeting.findUnique({
      where: { id },
      select: {
        id: true,
        title: true,
        meetingDate: true,
        committeeName: true,
        meetingType: true,
        status: true,
        sourceUrl: true,
        pdfUrl: true,
        plainText: true,
        minutesText: true,
        pageCount: true,
        publishedAt: true,
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
    });

    if (!meeting) {
      return NextResponse.json(
        { error: "Meeting not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      data: {
        id: meeting.id,
        title: meeting.title,
        meetingDate: meeting.meetingDate,
        committeeName: meeting.committeeName,
        meetingType: meeting.meetingType,
        status: meeting.status,
        sourceUrl: meeting.sourceUrl,
        pdfUrl: meeting.pdfUrl,
        plainText: meeting.plainText,
        minutesText: meeting.minutesText,
        pageCount: meeting.pageCount,
        publishedAt: meeting.publishedAt,
        entityId: meeting.entity.id,
        entityName: meeting.entity.name,
        entitySlug: meeting.entity.slug,
        entityType: meeting.entity.type,
        county: meeting.entity.county.name,
      },
    });
  }
);
