import Link from "next/link";
import { MapPin, FileText } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { EntityBadge } from "./EntityBadge";

interface EntityCardProps {
  name: string;
  slug: string;
  type: string;
  countyName: string;
  meetingCount: number;
}

export function EntityCard({
  name,
  slug,
  type,
  countyName,
  meetingCount,
}: EntityCardProps) {
  return (
    <Link href={`/entity/${slug}`}>
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="pb-2">
          <EntityBadge type={type} />
          <CardTitle className="text-base mt-1">{name}</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {countyName}
          </span>
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {meetingCount} minutes
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}
