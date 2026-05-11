import Link from "next/link";
import { Calendar, MapPin, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ENTITY_TYPE_LABELS } from "@/lib/constants";

interface SearchResult {
  id: string;
  title: string;
  meetingDate: string;
  committeeName: string | null;
  sourceUrl: string | null;
  entityName: string;
  entitySlug: string;
  entityType: string;
  countyName: string;
  rank: number;
  headline: string;
}

export function SearchResults({ results }: { results: SearchResult[] }) {
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <p className="text-lg font-medium text-muted-foreground">
          No results found
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Try broadening your search or adjusting filters
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <div key={result.id} className="rounded-lg border bg-card p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <Link
                href={`/meeting/${result.id}`}
                className="text-base font-semibold text-foreground hover:text-primary transition-colors line-clamp-2"
              >
                {result.title}
              </Link>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                <Link
                  href={`/entity/${result.entitySlug}`}
                  className="font-medium hover:text-primary transition-colors"
                >
                  {result.entityName}
                </Link>
                <Badge variant="secondary" className="text-xs">
                  {ENTITY_TYPE_LABELS[result.entityType] || result.entityType}
                </Badge>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {result.countyName} County
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {result.meetingDate
                    ? new Date(result.meetingDate).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })
                    : "Date unknown"}
                </span>
              </div>
            </div>
            {result.sourceUrl && (
              <a
                href={result.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 text-muted-foreground hover:text-primary transition-colors"
                title="View original source"
              >
                <FileText className="h-4 w-4" />
              </a>
            )}
          </div>
          {result.headline && result.headline.length > 0 && (
            <div
              className="mt-2.5 text-sm text-muted-foreground leading-relaxed [&_mark]:bg-yellow-200 [&_mark]:px-0.5 [&_mark]:rounded"
              dangerouslySetInnerHTML={{ __html: result.headline }}
            />
          )}
        </div>
      ))}
    </div>
  );
}
