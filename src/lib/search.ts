import { prisma } from "@/lib/prisma";

export interface SearchResult {
  id: string;
  title: string;
  meetingDate: Date;
  committeeName: string | null;
  sourceUrl: string | null;
  entityName: string;
  entitySlug: string;
  entityType: string;
  countyName: string;
  rank: number;
  headline: string;
}

export interface SearchParams {
  query?: string;
  entity?: string;
  county?: string;
  entityType?: string;
  dateFrom?: string;
  dateTo?: string;
  sort?: "relevance" | "date_desc" | "date_asc";
  page?: number;
  limit?: number;
}

/**
 * Sanitize a single token for use in a tsquery expression.
 * Strips everything except word characters (letters, digits, underscore).
 */
function sanitizeToken(token: string): string {
  return token.replace(/[^\w]/g, "");
}

/**
 * Convert a user query into a tsquery string.
 *
 * Supports:
 *  - "exact phrase" → 'exact <-> phrase' (phrase search)
 *  - word1 OR word2  → word1 | word2
 *  - plain words     → word1 & word2 (AND)
 *  - word*           → word:* (prefix match)
 */
function buildTsQuery(input: string): string {
  const parts: string[] = [];
  // Extract quoted phrases first
  const phraseRe = /"([^"]+)"/g;
  let remaining = input;
  let match;

  while ((match = phraseRe.exec(input)) !== null) {
    const words = match[1]
      .trim()
      .split(/\s+/)
      .map(sanitizeToken)
      .filter((w) => w.length > 0);
    if (words.length > 0) {
      parts.push(words.join(" <-> "));
    }
    remaining = remaining.replace(match[0], " ");
  }

  // Process remaining tokens
  const tokens = remaining.trim().split(/\s+/).filter((t) => t.length > 0);
  let i = 0;
  while (i < tokens.length) {
    const token = tokens[i];
    // Handle OR operator
    if (
      token.toUpperCase() === "OR" &&
      i > 0 &&
      i < tokens.length - 1
    ) {
      // Replace last AND-joined part with OR
      const prev = parts.pop();
      const isPrefix = tokens[i + 1].endsWith("*");
      const next = sanitizeToken(tokens[i + 1].replace(/\*$/, ""));
      if (prev && next) {
        parts.push(`${prev} | ${next}${isPrefix ? ":*" : ""}`);
      }
      i += 2;
      continue;
    }

    // Handle prefix matching (word*)
    const isPrefix = token.endsWith("*");
    const clean = sanitizeToken(token.replace(/\*$/, ""));
    if (clean) {
      parts.push(isPrefix ? `${clean}:*` : clean);
    }
    i++;
  }

  const result = parts.join(" & ");
  // Return a safe fallback if sanitization removed everything
  return result || "";
}

export async function searchMeetings(params: SearchParams) {
  const { query, entity, county, entityType, dateFrom, dateTo } = params;
  const sort = params.sort ?? "relevance";
  const page = params.page ?? 1;
  const limit = Math.min(params.limit ?? 20, 50);
  const offset = (page - 1) * limit;

  const conditions: string[] = [];
  const sqlParams: (string | number)[] = [];
  let paramIndex = 1;

  // Full-text search condition — track the param index for rank/headline
  let ftsParamIndex = 0;
  const hasQuery = query && query.trim().length >= 2;
  if (hasQuery) {
    const tsQueryStr = buildTsQuery(query.trim());
    if (tsQueryStr) {
      ftsParamIndex = paramIndex;
      conditions.push(`m.search_vector @@ to_tsquery('english', $${paramIndex})`);
      sqlParams.push(tsQueryStr);
      paramIndex++;
    }
  }
  const hasFts = ftsParamIndex > 0;

  if (entity) {
    conditions.push(`e.name ILIKE $${paramIndex}`);
    sqlParams.push(`%${entity}%`);
    paramIndex++;
  }
  if (county) {
    conditions.push(`c.name = $${paramIndex}`);
    sqlParams.push(county);
    paramIndex++;
  }
  if (entityType) {
    conditions.push(`e.type::text = $${paramIndex}`);
    sqlParams.push(entityType);
    paramIndex++;
  }
  if (dateFrom) {
    conditions.push(`m."meetingDate" >= $${paramIndex}::timestamp`);
    sqlParams.push(dateFrom);
    paramIndex++;
  }
  if (dateTo) {
    conditions.push(`m."meetingDate" <= $${paramIndex}::timestamp`);
    sqlParams.push(dateTo);
    paramIndex++;
  }

  // If no conditions at all, require at least something
  if (conditions.length === 0) {
    return {
      results: [],
      pagination: { page, limit, total: 0, totalPages: 0 },
    };
  }

  const whereClause = conditions.join(" AND ");

  // Build ORDER BY
  let orderBy: string;
  if (hasFts && sort === "relevance") {
    orderBy = `ts_rank(m.search_vector, to_tsquery('english', $${ftsParamIndex})) DESC, m."meetingDate" DESC NULLS LAST`;
  } else if (sort === "date_asc") {
    orderBy = `m."meetingDate" ASC NULLS LAST`;
  } else {
    orderBy = `m."meetingDate" DESC NULLS LAST`;
  }

  try {
    const countResult = await prisma.$queryRawUnsafe<[{ count: bigint }]>(
      `SELECT COUNT(*) as count
       FROM "Meeting" m
       JOIN "Entity" e ON m."entityId" = e.id
       JOIN "County" c ON e."countyId" = c.id
       WHERE ${whereClause}`,
      ...sqlParams
    );
    const total = Number(countResult[0].count);

    // Build SELECT columns
    const rankExpr = hasFts
      ? `ts_rank(m.search_vector, to_tsquery('english', $${ftsParamIndex})) as rank`
      : `0 as rank`;

    const headlineExpr = hasFts
      ? `ts_headline('english', COALESCE(m."minutesText", m."plainText", ''), to_tsquery('english', $${ftsParamIndex}),
          'StartSel=<mark>, StopSel=</mark>, MaxWords=60, MinWords=20, MaxFragments=3'
         ) as headline`
      : `'' as headline`;

    const results = await prisma.$queryRawUnsafe<SearchResult[]>(
      `SELECT
         m.id,
         m.title,
         m."meetingDate",
         m."committeeName",
         m."sourceUrl",
         e.name as "entityName",
         e.slug as "entitySlug",
         e.type::text as "entityType",
         c.name as "countyName",
         ${rankExpr},
         ${headlineExpr}
       FROM "Meeting" m
       JOIN "Entity" e ON m."entityId" = e.id
       JOIN "County" c ON e."countyId" = c.id
       WHERE ${whereClause}
       ORDER BY ${orderBy}
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      ...sqlParams,
      limit,
      offset
    );

    return {
      results,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    };
  } catch (err) {
    console.error("Search query failed:", err);
    return {
      results: [],
      pagination: { page, limit, total: 0, totalPages: 0 },
    };
  }
}
