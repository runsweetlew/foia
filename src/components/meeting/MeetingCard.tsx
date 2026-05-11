import Link from "next/link";
import { Calendar, ExternalLink } from "lucide-react";
import { MEETING_STATUS_LABELS } from "@/lib/constants";

interface MeetingCardProps {
  id: string;
  title: string;
  meetingDate: Date | string | null;
  committeeName?: string | null;
  sourceUrl?: string | null;
  status?: string | null;
}

export function MeetingCard({
  id,
  title,
  meetingDate,
  committeeName,
  sourceUrl,
  status,
}: MeetingCardProps) {
  const date = meetingDate ? new Date(meetingDate) : null;
  const isValidDate = date && !isNaN(date.getTime()) && date.getFullYear() > 1990;
  const statusInfo = status ? MEETING_STATUS_LABELS[status] : null;

  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div className="min-w-0 flex-1">
        <Link
          href={`/meeting/${id}`}
          className="font-medium text-foreground hover:text-primary transition-colors"
        >
          {title}
        </Link>
        <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {isValidDate
              ? date.toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })
              : "Date unknown"}
          </span>
          {committeeName && <span>{committeeName}</span>}
          {statusInfo && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
          )}
        </div>
      </div>
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-muted-foreground hover:text-primary"
          title="View original"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      )}
    </div>
  );
}
