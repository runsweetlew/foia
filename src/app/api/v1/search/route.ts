import { NextRequest, NextResponse } from "next/server";
import { searchMeetings } from "@/lib/search";
import { withApiKey } from "@/lib/api-key";

export const GET = withApiKey(async (request: NextRequest) => {
  const sp = request.nextUrl.searchParams;
  const q = sp.get("q") || undefined;
  const entity = sp.get("entity") || undefined;
  const county = sp.get("county") || undefined;
  const entityType = sp.get("type") || undefined;
  const dateFrom = sp.get("from") || undefined;
  const dateTo = sp.get("to") || undefined;
  const sort = sp.get("sort") as
    | "relevance"
    | "date_desc"
    | "date_asc"
    | undefined;
  const page = parseInt(sp.get("page") || "1");
  const limit = Math.min(parseInt(sp.get("limit") || "20"), 50);

  const hasQuery = q && q.length >= 2;
  const hasFilter = entity || county || entityType || dateFrom || dateTo;

  if (!hasQuery && !hasFilter) {
    return NextResponse.json(
      { error: "Provide a search query (q) or at least one filter." },
      { status: 400 }
    );
  }

  const result = await searchMeetings({
    query: q,
    entity,
    county,
    entityType,
    dateFrom,
    dateTo,
    sort: sort || (hasQuery ? "relevance" : "date_desc"),
    page,
    limit,
  });

  return NextResponse.json({
    data: result.results,
    pagination: result.pagination,
  });
});
