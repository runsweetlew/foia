export const dynamic = "force-dynamic";

import { Suspense } from "react";
import Link from "next/link";
import {
  Building2,
  FileText,
  MapPin,
  GraduationCap,
  Landmark,
  Home,
  TreePine,
  Clock,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { SearchBar } from "@/components/search/SearchBar";
import { prisma } from "@/lib/prisma";

const ENTITY_TYPE_INFO = [
  { type: "SCHOOL_DISTRICT", label: "School Districts", icon: GraduationCap },
  { type: "TOWNSHIP", label: "Townships", icon: TreePine },
  { type: "CITY", label: "Cities", icon: Building2 },
  { type: "COUNTY", label: "Counties", icon: Landmark },
  { type: "VILLAGE", label: "Villages", icon: Home },
  { type: "ISD", label: "ISDs", icon: GraduationCap },
  { type: "STATE_BOARD", label: "State Boards", icon: Landmark },
  { type: "SPECIAL_DISTRICT", label: "Special Districts", icon: Building2 },
];

async function getStats() {
  const [totalEntities, activeEntities, totalMeetings, recentMeetings] =
    await Promise.all([
      prisma.entity.count(),
      prisma.entity.count({ where: { scrapeStatus: "ACTIVE" } }),
      prisma.meeting.count(),
      prisma.meeting.findMany({
        orderBy: { scrapedAt: "desc" },
        take: 5,
        include: {
          entity: {
            include: { county: true },
          },
        },
      }),
    ]);

  const typeCounts = await prisma.entity.groupBy({
    by: ["type"],
    _count: true,
  });

  const typeCountMap: Record<string, number> = {};
  for (const tc of typeCounts) {
    typeCountMap[tc.type] = tc._count;
  }

  return {
    totalEntities,
    activeEntities,
    totalMeetings,
    recentMeetings,
    typeCountMap,
  };
}

export default async function HomePage() {
  const stats = await getStats();

  return (
    <div className="flex flex-col items-center">
      {/* Hero */}
      <div className="w-full bg-gradient-to-b from-blue-50 to-white px-4">
        <div className="mx-auto max-w-4xl py-20 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Search Michigan Public Meeting Minutes
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">
            Full-text search across{" "}
            <strong>{stats.totalMeetings.toLocaleString()}</strong> meetings from{" "}
            <strong>{stats.totalEntities.toLocaleString()}</strong> public
            entities
          </p>
          <Suspense>
            <SearchBar className="mt-8 max-w-2xl mx-auto" />
          </Suspense>
        </div>
      </div>

      {/* Stats */}
      <div className="w-full border-b bg-white px-4 py-8">
        <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 md:grid-cols-4">
          <div className="text-center">
            <Landmark className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-2 text-2xl font-bold">83</p>
            <p className="text-sm text-muted-foreground">Counties</p>
          </div>
          <div className="text-center">
            <Building2 className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-2 text-2xl font-bold">
              {stats.totalEntities.toLocaleString()}
            </p>
            <p className="text-sm text-muted-foreground">Entities Tracked</p>
          </div>
          <div className="text-center">
            <FileText className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-2 text-2xl font-bold">
              {stats.totalMeetings.toLocaleString()}
            </p>
            <p className="text-sm text-muted-foreground">Meeting Minutes</p>
          </div>
          <div className="text-center">
            <Clock className="mx-auto h-6 w-6 text-muted-foreground" />
            <p className="mt-2 text-2xl font-bold">
              {stats.activeEntities.toLocaleString()}
            </p>
            <p className="text-sm text-muted-foreground">Actively Scraped</p>
          </div>
        </div>
      </div>

      {/* Browse by type */}
      <div className="w-full px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-8 text-2xl font-bold text-foreground">
            Browse by Entity Type
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {ENTITY_TYPE_INFO.map((item) => (
              <Link key={item.type} href={`/browse/type/${item.type}`}>
                <Card className="transition-shadow hover:shadow-md text-center">
                  <CardHeader className="pb-2">
                    <item.icon className="mx-auto h-8 w-8 text-muted-foreground" />
                    <CardTitle className="text-base">{item.label}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">
                      {(stats.typeCountMap[item.type] || 0).toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Recent meetings */}
      {stats.recentMeetings.length > 0 && (
        <div className="w-full bg-muted/30 px-4 py-16">
          <div className="mx-auto max-w-5xl">
            <h2 className="mb-8 text-2xl font-bold text-foreground">
              Recently Added
            </h2>
            <div className="space-y-3">
              {stats.recentMeetings.map((meeting) => (
                <Link
                  key={meeting.id}
                  href={`/meeting/${meeting.id}`}
                  className="block"
                >
                  <div className="flex items-center justify-between rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm">
                    <div>
                      <p className="font-medium">{meeting.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {meeting.entity.name}
                        {meeting.entity.county && (
                          <> &middot; {meeting.entity.county.name} County</>
                        )}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm text-muted-foreground">
                      {meeting.meetingDate
                        ? new Date(meeting.meetingDate).toLocaleDateString(
                            "en-US",
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            }
                          )
                        : "Date unknown"}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
