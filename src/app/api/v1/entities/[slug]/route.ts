import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(
  async (
    _request: NextRequest,
    { params }: { params: Promise<{ slug: string }> }
  ) => {
    const { slug } = await params;

    const entity = await prisma.entity.findUnique({
      where: { slug },
      select: {
        id: true,
        name: true,
        slug: true,
        type: true,
        platform: true,
        county: { select: { id: true, name: true } },
        websiteUrl: true,
        minutesUrl: true,
        population: true,
        isCharter: true,
        foiaOfficerName: true,
        foiaOfficerEmail: true,
        foiaOfficerPhone: true,
        foiaOfficerAddress: true,
        meetings: {
          orderBy: { meetingDate: "desc" },
          take: 10,
          select: {
            id: true,
            title: true,
            meetingDate: true,
            committeeName: true,
            meetingType: true,
            status: true,
            sourceUrl: true,
          },
        },
        documents: {
          orderBy: { createdAt: "desc" },
          select: {
            id: true,
            title: true,
            type: true,
            fiscalYear: true,
            sourceUrl: true,
            pageCount: true,
            fileSize: true,
          },
        },
        _count: { select: { meetings: true, documents: true } },
      },
    });

    if (!entity) {
      return NextResponse.json({ error: "Entity not found" }, { status: 404 });
    }

    return NextResponse.json({
      data: {
        id: entity.id,
        name: entity.name,
        slug: entity.slug,
        type: entity.type,
        platform: entity.platform,
        county: entity.county.name,
        countyId: entity.county.id,
        websiteUrl: entity.websiteUrl,
        minutesUrl: entity.minutesUrl,
        population: entity.population,
        isCharter: entity.isCharter,
        foiaOfficerName: entity.foiaOfficerName,
        foiaOfficerEmail: entity.foiaOfficerEmail,
        foiaOfficerPhone: entity.foiaOfficerPhone,
        foiaOfficerAddress: entity.foiaOfficerAddress,
        meetingCount: entity._count.meetings,
        documentCount: entity._count.documents,
        recentMeetings: entity.meetings,
        documents: entity.documents,
      },
    });
  }
);
