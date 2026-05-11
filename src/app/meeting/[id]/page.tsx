export const dynamic = "force-dynamic";

import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Calendar, ExternalLink, FileText } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { EntityBadge } from "@/components/entity/EntityBadge";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MEETING_STATUS_LABELS } from "@/lib/constants";

export default async function MeetingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const meeting = await prisma.meeting.findUnique({
    where: { id },
    include: {
      entity: {
        include: { county: true },
      },
    },
  });

  if (!meeting) notFound();

  const statusInfo = MEETING_STATUS_LABELS[meeting.status] || null;
  const hasMinutes = !!meeting.minutesText;
  const hasAgenda = !!meeting.plainText;
  const hasBothContent = hasMinutes && hasAgenda;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link
        href={`/entity/${meeting.entity.slug}`}
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to {meeting.entity.name}
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">{meeting.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <EntityBadge type={meeting.entity.type} />
          <Link
            href={`/entity/${meeting.entity.slug}`}
            className="font-medium hover:text-primary transition-colors"
          >
            {meeting.entity.name}
          </Link>
          {meeting.entity.county && (
            <span>{meeting.entity.county.name} County</span>
          )}
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {meeting.meetingDate
              ? new Date(meeting.meetingDate).toLocaleDateString("en-US", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })
              : "Date unknown"}
          </span>
          {meeting.committeeName && (
            <Badge variant="outline">{meeting.committeeName}</Badge>
          )}
          {statusInfo && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
          )}
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          {meeting.sourceUrl && (
            <a
              href={meeting.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              View Original
            </a>
          )}
          {meeting.pdfStoragePath ? (
            <a
              href={`/api/documents/${meeting.id}`}
              target="_blank"
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              <FileText className="h-3 w-3" />
              View PDF
            </a>
          ) : meeting.pdfUrl ? (
            <a
              href={meeting.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              <FileText className="h-3 w-3" />
              Download PDF
            </a>
          ) : null}
          {meeting.ocrApplied && (
            <Badge variant="secondary">OCR Processed</Badge>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-card p-6">
        {hasBothContent ? (
          <Tabs defaultValue="minutes">
            <TabsList className="mb-4">
              <TabsTrigger value="minutes">Approved Minutes</TabsTrigger>
              <TabsTrigger value="agenda">Agenda</TabsTrigger>
            </TabsList>
            <TabsContent value="minutes">
              <div className="prose prose-sm max-w-none whitespace-pre-wrap text-muted-foreground leading-relaxed">
                {meeting.minutesText}
              </div>
            </TabsContent>
            <TabsContent value="agenda">
              <div className="prose prose-sm max-w-none whitespace-pre-wrap text-muted-foreground leading-relaxed">
                {meeting.plainText}
              </div>
            </TabsContent>
          </Tabs>
        ) : hasMinutes ? (
          <>
            <h2 className="mb-4 text-lg font-semibold">Approved Minutes</h2>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap text-muted-foreground leading-relaxed">
              {meeting.minutesText}
            </div>
          </>
        ) : hasAgenda ? (
          <>
            <h2 className="mb-4 text-lg font-semibold">Meeting Minutes</h2>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap text-muted-foreground leading-relaxed">
              {meeting.plainText}
            </div>
          </>
        ) : (
          <p className="text-muted-foreground">
            Full text content is not yet available for this meeting. The original
            document may be accessible via the source link above.
          </p>
        )}
      </div>
    </div>
  );
}
