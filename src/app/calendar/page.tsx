export const dynamic = "force-dynamic";

import Link from "next/link";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { prisma } from "@/lib/prisma";
import { EntityBadge } from "@/components/entity/EntityBadge";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export default async function CalendarPage({
  searchParams,
}: {
  searchParams: Promise<{ month?: string; year?: string }>;
}) {
  const params = await searchParams;
  const now = new Date();
  const month = params.month ? parseInt(params.month) : now.getMonth() + 1;
  const year = params.year ? parseInt(params.year) : now.getFullYear();

  const startDate = new Date(year, month - 1, 1);
  const endDate = new Date(year, month, 0, 23, 59, 59);

  const meetings = await prisma.meeting.findMany({
    where: {
      meetingDate: {
        gte: startDate,
        lte: endDate,
      },
    },
    orderBy: { meetingDate: "asc" },
    select: {
      id: true,
      title: true,
      meetingDate: true,
      committeeName: true,
      status: true,
      meetingType: true,
      entity: {
        select: { name: true, slug: true, type: true },
      },
    },
  });

  // Group meetings by date
  const grouped = new Map<string, typeof meetings>();
  for (const meeting of meetings) {
    if (!meeting.meetingDate) continue;
    const key = new Date(meeting.meetingDate).toISOString().split("T")[0];
    const existing = grouped.get(key) || [];
    existing.push(meeting);
    grouped.set(key, existing);
  }

  const sortedDates = [...grouped.keys()].sort();

  // Navigation
  const prevMonth = month === 1 ? 12 : month - 1;
  const prevYear = month === 1 ? year - 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Meeting Calendar
          </h1>
          <p className="mt-1 text-muted-foreground">
            Board meetings across Michigan public entities
          </p>
        </div>
      </div>

      <div className="mb-6 flex items-center justify-between rounded-lg border bg-card p-4">
        <Link
          href={`/calendar?month=${prevMonth}&year=${prevYear}`}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          {MONTH_NAMES[prevMonth - 1]}
        </Link>
        <h2 className="text-lg font-semibold">
          {MONTH_NAMES[month - 1]} {year}
        </h2>
        <Link
          href={`/calendar?month=${nextMonth}&year=${nextYear}`}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {MONTH_NAMES[nextMonth - 1]}
          <ChevronRight className="h-4 w-4" />
        </Link>
      </div>

      {sortedDates.length > 0 ? (
        <div className="space-y-6">
          {sortedDates.map((dateStr) => {
            const dayMeetings = grouped.get(dateStr)!;
            const d = new Date(dateStr + "T12:00:00");
            return (
              <div key={dateStr}>
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Calendar className="h-4 w-4 text-primary" />
                  {d.toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                  <span className="text-muted-foreground font-normal">
                    ({dayMeetings.length} meeting{dayMeetings.length !== 1 ? "s" : ""})
                  </span>
                </h3>
                <div className="space-y-2 pl-6">
                  {dayMeetings.map((meeting) => (
                    <div
                      key={meeting.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <EntityBadge type={meeting.entity.type} />
                          <Link
                            href={`/entity/${meeting.entity.slug}`}
                            className="text-sm font-medium text-foreground hover:text-primary transition-colors truncate"
                          >
                            {meeting.entity.name}
                          </Link>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground truncate">
                          {meeting.title}
                          {meeting.committeeName && (
                            <span> &middot; {meeting.committeeName}</span>
                          )}
                        </p>
                      </div>
                      {meeting.status === "APPROVED" ? (
                        <Link
                          href={`/meeting/${meeting.id}`}
                          className="shrink-0 ml-3 rounded-md border px-2.5 py-1 text-xs font-medium text-primary hover:bg-muted transition-colors"
                        >
                          View Minutes
                        </Link>
                      ) : meeting.status === "SCHEDULED" ? (
                        <span className="shrink-0 ml-3 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                          Upcoming
                        </span>
                      ) : (
                        <Link
                          href={`/meeting/${meeting.id}`}
                          className="shrink-0 ml-3 rounded-md border px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
                        >
                          View
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          No meetings found for {MONTH_NAMES[month - 1]} {year}.
        </div>
      )}
    </div>
  );
}
