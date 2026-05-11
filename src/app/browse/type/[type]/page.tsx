export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { EntityCard } from "@/components/entity/EntityCard";
import { ENTITY_TYPE_LABELS } from "@/lib/constants";
import type { EntityType } from "@/generated/prisma";

const VALID_TYPES = Object.keys(ENTITY_TYPE_LABELS);

export default async function TypePage({
  params,
}: {
  params: Promise<{ type: string }>;
}) {
  const { type } = await params;

  if (!VALID_TYPES.includes(type)) {
    notFound();
  }

  const entities = await prisma.entity.findMany({
    where: { type: type as EntityType },
    orderBy: { name: "asc" },
    include: {
      county: true,
      _count: { select: { meetings: true } },
    },
  });

  const label = ENTITY_TYPE_LABELS[type] || type;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Link
        href="/browse"
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Browse
      </Link>

      <h1 className="mb-2 text-3xl font-bold text-foreground">{label}s</h1>
      <p className="mb-8 text-muted-foreground">
        {entities.length} {label.toLowerCase()}s in Michigan
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
          No {label.toLowerCase()}s have been added yet.
        </div>
      )}
    </div>
  );
}
