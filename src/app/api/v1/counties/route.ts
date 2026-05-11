import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(async (_request: NextRequest) => {
  const counties = await prisma.county.findMany({
    orderBy: { name: "asc" },
    select: {
      id: true,
      name: true,
      fips: true,
      population: true,
      _count: { select: { entities: true } },
    },
  });

  return NextResponse.json({
    data: counties.map((c) => ({
      id: c.id,
      name: c.name,
      fips: c.fips,
      population: c.population,
      entityCount: c._count.entities,
    })),
  });
});
