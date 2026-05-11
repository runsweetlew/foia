export const dynamic = "force-dynamic";

import Link from "next/link";
import {
  Building2,
  GraduationCap,
  Landmark,
  Home,
  TreePine,
  MapPin,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { prisma } from "@/lib/prisma";
import { MICHIGAN_COUNTIES } from "@/lib/constants";

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

export default async function BrowsePage() {
  const typeCounts = await prisma.entity.groupBy({
    by: ["type"],
    _count: true,
  });
  const typeCountMap: Record<string, number> = {};
  for (const tc of typeCounts) {
    typeCountMap[tc.type] = tc._count;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-8 text-3xl font-bold text-foreground">
        Browse Entities
      </h1>

      {/* By type */}
      <section className="mb-12">
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          By Entity Type
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
                    {(typeCountMap[item.type] || 0).toLocaleString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* By county */}
      <section>
        <h2 className="mb-4 text-xl font-semibold text-foreground">
          By County
        </h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {MICHIGAN_COUNTIES.map((county) => (
            <Link
              key={county}
              href={`/browse/counties/${county}`}
              className="flex items-center gap-2 rounded-lg border p-3 text-sm transition-colors hover:bg-muted"
            >
              <MapPin className="h-4 w-4 shrink-0 text-muted-foreground" />
              {county}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
