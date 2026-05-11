export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { EntityCard } from "@/components/entity/EntityCard";
import { MICHIGAN_COUNTIES } from "@/lib/constants";

export default async function CountyPage({
  params,
}: {
  params: Promise<{ county: string }>;
}) {
  const { county: rawCounty } = await params;
  const countyName = decodeURIComponent(rawCounty);

  if (!MICHIGAN_COUNTIES.includes(countyName as any)) {
    notFound();
  }

  const county = await prisma.county.findUnique({
    where: { name: countyName },
  });

  if (!county) notFound();

  const entities = await prisma.entity.findMany({
    where: { countyId: county.id },
    orderBy: [{ type: "asc" }, { name: "asc" }],
    include: {
      county: true,
      _count: { select: { meetings: true } },
    },
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Link
        href="/browse"
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Browse
      </Link>

      <h1 className="mb-2 text-3xl font-bold text-foreground">
        {countyName} County
      </h1>
      <p className="mb-8 text-muted-foreground">
        {entities.length} public entities
      </p>

      {entities.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {entities.map((entity) => (
            <EntityCard
              key={entity.id}
              name={entity.name}
              slug={entity.slug}
              type={entity.type}
              countyName={entity.county?.name ?? ""}
              meetingCount={entity._count.meetings}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          No entities found in {countyName} County yet.
        </div>
      )}
    </div>
  );
}
