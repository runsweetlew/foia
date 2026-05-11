import { NextRequest, NextResponse } from "next/server";
import { searchMeetings } from "@/lib/search";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const q = searchParams.get("q") || undefined;
  const entity = searchParams.get("entity") || undefined;
  const county = searchParams.get("county") || undefined;
  const entityType = searchParams.get("type") || undefined;
  const dateFrom = searchParams.get("from") || undefined;
  const dateTo = searchParams.get("to") || undefined;
  const sort = searchParams.get("sort") as "relevance" | "date_desc" | "date_asc" | undefined;
  const page = parseInt(searchParams.get("page") || "1");
  const limit = Math.min(parseInt(searchParams.get("limit") || "20"), 50);

  // Need at least a query or a filter
  const hasQuery = q && q.length >= 2;
  const hasFilter = entity || county || entityType || dateFrom || dateTo;

  if (!hasQuery && !hasFilter) {
    return NextResponse.json(
      { error: "Provide a search query or at least one filter" },
      { status: 400 }
    );
  }

  const data = await searchMeetings({
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

  return NextResponse.json(data);
}
