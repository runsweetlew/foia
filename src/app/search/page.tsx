export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { SearchBar } from "@/components/search/SearchBar";
import { SearchFilters } from "@/components/search/SearchFilters";
import { SearchResults } from "@/components/search/SearchResults";
import { Pagination } from "@/components/search/Pagination";
import { ActiveFilters } from "@/components/search/ActiveFilters";
import { searchMeetings } from "@/lib/search";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    entity?: string;
    county?: string;
    type?: string;
    from?: string;
    to?: string;
    sort?: string;
    page?: string;
  }>;
}) {
  const params = await searchParams;
  const query = params.q || "";
  const page = parseInt(params.page || "1");

  const hasQuery = query.length >= 2;
  const hasFilter =
    params.entity || params.county || params.type || params.from || params.to;

  let data = null;
  if (hasQuery || hasFilter) {
    data = await searchMeetings({
      query: hasQuery ? query : undefined,
      entity: params.entity,
      county: params.county,
      entityType: params.type,
      dateFrom: params.from,
      dateTo: params.to,
      sort:
        (params.sort as "relevance" | "date_desc" | "date_asc") ||
        (hasQuery ? "relevance" : "date_desc"),
      page,
    });
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Suspense>
        <SearchBar className="mb-6" />
      </Suspense>

      {/* Active filter chips */}
      <Suspense>
        <ActiveFilters />
      </Suspense>

      <div className="flex flex-col gap-8 md:flex-row">
        {/* Filters sidebar */}
        <aside className="w-full shrink-0 md:w-64">
          <Suspense>
            <SearchFilters />
          </Suspense>
        </aside>

        {/* Results */}
        <main className="flex-1">
          {data ? (
            <>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-foreground">
                    {hasQuery
                      ? <>Results for &ldquo;{query}&rdquo;</>
                      : "Browse Meetings"}
                  </h1>
                  <p className="mt-1 text-muted-foreground">
                    {data.pagination.total.toLocaleString()} results
                  </p>
                </div>
                <Suspense>
                  <SortSelector hasQuery={hasQuery} />
                </Suspense>
              </div>

              <SearchResults results={data.results as any} />

              <Suspense>
                <Pagination
                  page={data.pagination.page}
                  totalPages={data.pagination.totalPages}
                  total={data.pagination.total}
                />
              </Suspense>
            </>
          ) : (
            <div className="rounded-lg border border-dashed p-12 text-center">
              <p className="text-lg font-medium text-muted-foreground">
                Search meeting minutes across Michigan
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Enter a search term like &ldquo;budget&rdquo;,
                &ldquo;zoning&rdquo;, or &ldquo;curriculum&rdquo;
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Or use the filters to browse meetings by entity type, county, or
                date range
              </p>
              <div className="mt-6 space-y-2 text-left max-w-md mx-auto">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Search tips
                </p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">&quot;exact phrase&quot;</code>{" "}
                    — match an exact phrase
                  </li>
                  <li>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">budget OR tax</code>{" "}
                    — match either word
                  </li>
                  <li>
                    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">infra*</code>{" "}
                    — prefix match (infrastructure, etc.)
                  </li>
                </ul>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function SortSelector({ hasQuery }: { hasQuery: boolean }) {
  // This is a server component wrapper — the actual interactive part is client
  return <SortSelectorClient hasQuery={hasQuery} />;
}

import { SortSelectorClient } from "@/components/search/SortSelector";
