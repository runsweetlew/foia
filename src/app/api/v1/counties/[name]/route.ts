import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(
  async (
    _request: NextRequest,
    { params }: { params: Promise<{ name: string }> }
  ) => {
    const { name } = await params;
    const decodedName = decodeURIComponent(name);

    const county = await prisma.county.findUnique({
      where: { name: decodedName },
      include: {
        _count: { select: { entities: true } },
        entities: { select: { type: true } },
      },
    });

    if (!county) {
      return NextResponse.json({ error: "County not found" }, { status: 404 });
    }

    const typeCounts: Record<string, number> = {};
    for (const e of county.entities) {
      typeCounts[e.type] = (typeCounts[e.type] || 0) + 1;
    }

    return NextResponse.json({
      data: {
        id: county.id,
        name: county.name,
        fips: county.fips,
        population: county.population,
        entityCount: county._count.entities,
        entityTypeCounts: typeCounts,
      },
    });
  }
);
