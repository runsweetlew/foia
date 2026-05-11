export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import Link from "next/link";
import { ExternalLink, FileText, MapPin, Mail, Phone, User } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { EntityBadge } from "@/components/entity/EntityBadge";
import { MeetingCard } from "@/components/meeting/MeetingCard";
import { PLATFORM_LABELS } from "@/lib/constants";

export default async function EntityPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const entity = await prisma.entity.findUnique({
    where: { slug },
    include: {
      county: true,
      meetings: {
        orderBy: { meetingDate: "desc" },
        take: 100,
      },
      documents: {
        where: { type: "BUDGET" },
        orderBy: { scrapedAt: "desc" },
        take: 20,
      },
    },
  });

  if (!entity) notFound();

  const minutesPortalUrl = entity.publicBoardUrl || entity.minutesUrl;
  const hasFoiaOfficer =
    entity.foiaOfficerName ||
    entity.foiaOfficerEmail ||
    entity.foiaOfficerPhone;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <EntityBadge type={entity.type} />
        <h1 className="mt-2 text-3xl font-bold text-foreground">
          {entity.name}
        </h1>
        <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          {entity.county && (
            <Link
              href={`/browse/counties/${entity.county.name}`}
              className="flex items-center gap-1 hover:text-primary transition-colors"
            >
              <MapPin className="h-4 w-4" />
              {entity.county.name} County
            </Link>
          )}
          {entity.platform !== "UNKNOWN" && (
            <span>
              Platform: {PLATFORM_LABELS[entity.platform] || entity.platform}
            </span>
          )}
          {entity.websiteUrl && (
            <a
              href={entity.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-primary hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              Official Website
            </a>
          )}
          {minutesPortalUrl && (
            <a
              href={minutesPortalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-primary hover:underline"
            >
              <FileText className="h-3 w-3" />
              View Official Minutes & Agendas
            </a>
          )}
        </div>
        {entity.lastScrapedAt && (
          <p className="mt-2 text-xs text-muted-foreground">
            Last updated:{" "}
            {new Date(entity.lastScrapedAt).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        )}
      </div>

      {hasFoiaOfficer && (
        <div className="mb-8 rounded-lg border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
            FOIA Contact
          </h3>
          <div className="mt-3 space-y-2 text-sm">
            {entity.foiaOfficerName && (
              <p className="flex items-center gap-2 text-foreground">
                <User className="h-4 w-4 text-muted-foreground" />
                {entity.foiaOfficerName}
              </p>
            )}
            {entity.foiaOfficerEmail && (
              <a
                href={`mailto:${entity.foiaOfficerEmail}`}
                className="flex items-center gap-2 text-primary hover:underline"
              >
                <Mail className="h-4 w-4 text-muted-foreground" />
                {entity.foiaOfficerEmail}
              </a>
            )}
            {entity.foiaOfficerPhone && (
              <p className="flex items-center gap-2 text-foreground">
                <Phone className="h-4 w-4 text-muted-foreground" />
                {entity.foiaOfficerPhone}
              </p>
            )}
            {entity.foiaOfficerAddress && (
              <p className="text-muted-foreground pl-6">
                {entity.foiaOfficerAddress}
              </p>
            )}
          </div>
        </div>
      )}

      <h2 className="mb-4 text-xl font-semibold">
        Meeting Minutes ({entity.meetings.length})
      </h2>

      {entity.meetings.length > 0 ? (
        <div className="space-y-3">
          {entity.meetings.map((meeting) => (
            <MeetingCard
              key={meeting.id}
              id={meeting.id}
              title={meeting.title}
              meetingDate={meeting.meetingDate}
              committeeName={meeting.committeeName}
              sourceUrl={meeting.sourceUrl}
              status={meeting.status}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          No meeting minutes have been collected yet for this entity.
        </div>
      )}

      {entity.documents.length > 0 && (
        <div className="mt-10">
          <h2 className="mb-4 text-xl font-semibold">
            Budget Documents ({entity.documents.length})
          </h2>
          <div className="space-y-3">
            {entity.documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div>
                  <p className="font-medium text-foreground">{doc.title}</p>
                  <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
                    {doc.fiscalYear && <span>FY {doc.fiscalYear}</span>}
                  </div>
                </div>
                {(doc.pdfUrl || doc.sourceUrl) && (
                  <a
                    href={doc.pdfStoragePath ? `/api/documents/${doc.id}` : (doc.pdfUrl || doc.sourceUrl)!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
                  >
                    <FileText className="h-3 w-3" />
                    View PDF
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
