import { NextResponse } from "next/server";

const ENTITY_TYPES = [
  "COUNTY",
  "TOWNSHIP",
  "CITY",
  "VILLAGE",
  "SCHOOL_DISTRICT",
  "ISD",
  "STATE_BOARD",
  "SPECIAL_DISTRICT",
  "COMMUNITY_COLLEGE",
  "UNIVERSITY",
  "ROAD_COMMISSION",
  "LIBRARY",
];

const spec = {
  openapi: "3.0.3",
  info: {
    title: "FOIA Michigan Public API",
    description:
      "Read-only API for Michigan government meeting minutes, entities, and documents. All data endpoints require an API key via the `X-API-Key` header.",
    version: "1.0.0",
  },
  servers: [{ url: "/api/v1", description: "Current server" }],
  security: [{ apiKey: [] }],
  components: {
    securitySchemes: {
      apiKey: {
        type: "apiKey" as const,
        in: "header" as const,
        name: "X-API-Key",
        description: "API key for authentication.",
      },
    },
    schemas: {
      Error: {
        type: "object",
        properties: { error: { type: "string" } },
      },
      Pagination: {
        type: "object",
        properties: {
          page: { type: "integer" },
          limit: { type: "integer" },
          total: { type: "integer" },
          totalPages: { type: "integer" },
        },
      },
      County: {
        type: "object",
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          fips: { type: "string", nullable: true },
          population: { type: "integer", nullable: true },
          entityCount: { type: "integer" },
        },
      },
      CountyDetail: {
        type: "object",
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          fips: { type: "string", nullable: true },
          population: { type: "integer", nullable: true },
          entityCount: { type: "integer" },
          entityTypeCounts: {
            type: "object",
            additionalProperties: { type: "integer" },
          },
        },
      },
      Entity: {
        type: "object",
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          slug: { type: "string" },
          type: { type: "string", enum: ENTITY_TYPES },
          platform: { type: "string" },
          county: { type: "string" },
          websiteUrl: { type: "string", nullable: true },
          population: { type: "integer", nullable: true },
          isCharter: { type: "boolean" },
          foiaOfficerName: { type: "string", nullable: true },
          foiaOfficerEmail: { type: "string", nullable: true },
          meetingCount: { type: "integer" },
          documentCount: { type: "integer" },
        },
      },
      EntityDetail: {
        type: "object",
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          slug: { type: "string" },
          type: { type: "string", enum: ENTITY_TYPES },
          platform: { type: "string" },
          county: { type: "string" },
          countyId: { type: "string" },
          websiteUrl: { type: "string", nullable: true },
          minutesUrl: { type: "string", nullable: true },
          population: { type: "integer", nullable: true },
          isCharter: { type: "boolean" },
          foiaOfficerName: { type: "string", nullable: true },
          foiaOfficerEmail: { type: "string", nullable: true },
          foiaOfficerPhone: { type: "string", nullable: true },
          foiaOfficerAddress: { type: "string", nullable: true },
          meetingCount: { type: "integer" },
          documentCount: { type: "integer" },
          recentMeetings: {
            type: "array",
            items: { $ref: "#/components/schemas/MeetingSummary" },
          },
          documents: {
            type: "array",
            items: { $ref: "#/components/schemas/Document" },
          },
        },
      },
      MeetingSummary: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          meetingDate: { type: "string", format: "date-time" },
          committeeName: { type: "string", nullable: true },
          meetingType: { type: "string", nullable: true },
          status: {
            type: "string",
            enum: ["SCHEDULED", "HELD", "APPROVED", "CANCELLED"],
          },
          sourceUrl: { type: "string", nullable: true },
          pdfUrl: { type: "string", nullable: true },
          pageCount: { type: "integer", nullable: true },
          entityId: { type: "string" },
          entityName: { type: "string" },
          entitySlug: { type: "string" },
          entityType: { type: "string" },
          county: { type: "string" },
        },
      },
      MeetingDetail: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          meetingDate: { type: "string", format: "date-time" },
          committeeName: { type: "string", nullable: true },
          meetingType: { type: "string", nullable: true },
          status: { type: "string" },
          sourceUrl: { type: "string", nullable: true },
          pdfUrl: { type: "string", nullable: true },
          plainText: { type: "string", nullable: true },
          minutesText: { type: "string", nullable: true },
          pageCount: { type: "integer", nullable: true },
          publishedAt: { type: "string", format: "date-time", nullable: true },
          entityId: { type: "string" },
          entityName: { type: "string" },
          entitySlug: { type: "string" },
          entityType: { type: "string" },
          county: { type: "string" },
        },
      },
      Document: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          type: {
            type: "string",
            enum: [
              "BUDGET",
              "MASTER_PLAN",
              "FOIA_POLICY",
              "ANNUAL_REPORT",
              "OTHER",
            ],
          },
          fiscalYear: { type: "string", nullable: true },
          sourceUrl: { type: "string", nullable: true },
          pageCount: { type: "integer", nullable: true },
          fileSize: { type: "integer", nullable: true },
        },
      },
      SearchResult: {
        type: "object",
        properties: {
          id: { type: "string" },
          title: { type: "string" },
          meetingDate: { type: "string", format: "date-time" },
          committeeName: { type: "string", nullable: true },
          sourceUrl: { type: "string", nullable: true },
          entityName: { type: "string" },
          entitySlug: { type: "string" },
          entityType: { type: "string" },
          countyName: { type: "string" },
          rank: { type: "number" },
          headline: {
            type: "string",
            description: "HTML snippet with <mark> tags highlighting matches",
          },
        },
      },
      Stats: {
        type: "object",
        properties: {
          totalCounties: { type: "integer" },
          totalEntities: { type: "integer" },
          totalMeetings: { type: "integer" },
          totalDocuments: { type: "integer" },
          lastUpdate: {
            type: "string",
            format: "date-time",
            nullable: true,
          },
          entityTypeCounts: {
            type: "object",
            additionalProperties: { type: "integer" },
          },
        },
      },
    },
  },
  paths: {
    "/counties": {
      get: {
        summary: "List all Michigan counties",
        operationId: "listCounties",
        tags: ["Counties"],
        responses: {
          "200": {
            description: "List of all 83 Michigan counties",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: {
                      type: "array",
                      items: { $ref: "#/components/schemas/County" },
                    },
                  },
                },
              },
            },
          },
          "401": {
            description: "Missing API key",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Error" },
              },
            },
          },
        },
      },
    },
    "/counties/{name}": {
      get: {
        summary: "Get a single county by name",
        operationId: "getCounty",
        tags: ["Counties"],
        parameters: [
          {
            name: "name",
            in: "path" as const,
            required: true,
            schema: { type: "string" },
            description: "County name (e.g., Washtenaw, Grand Traverse)",
          },
        ],
        responses: {
          "200": {
            description: "County details with entity type breakdown",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: { $ref: "#/components/schemas/CountyDetail" },
                  },
                },
              },
            },
          },
          "404": {
            description: "County not found",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Error" },
              },
            },
          },
        },
      },
    },
    "/entities": {
      get: {
        summary: "List government entities",
        operationId: "listEntities",
        tags: ["Entities"],
        parameters: [
          {
            name: "type",
            in: "query" as const,
            schema: { type: "string", enum: ENTITY_TYPES },
            description: "Filter by entity type",
          },
          {
            name: "county",
            in: "query" as const,
            schema: { type: "string" },
            description: "Filter by county name",
          },
          {
            name: "page",
            in: "query" as const,
            schema: { type: "integer", default: 1 },
          },
          {
            name: "limit",
            in: "query" as const,
            schema: { type: "integer", default: 20, maximum: 100 },
          },
        ],
        responses: {
          "200": {
            description: "Paginated list of entities",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: {
                      type: "array",
                      items: { $ref: "#/components/schemas/Entity" },
                    },
                    pagination: {
                      $ref: "#/components/schemas/Pagination",
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
    "/entities/{slug}": {
      get: {
        summary: "Get a single entity by slug",
        operationId: "getEntity",
        tags: ["Entities"],
        parameters: [
          {
            name: "slug",
            in: "path" as const,
            required: true,
            schema: { type: "string" },
            description: "Entity slug (e.g., ann-arbor, washtenaw-county)",
          },
        ],
        responses: {
          "200": {
            description:
              "Entity details with recent meetings and documents",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: { $ref: "#/components/schemas/EntityDetail" },
                  },
                },
              },
            },
          },
          "404": {
            description: "Entity not found",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Error" },
              },
            },
          },
        },
      },
    },
    "/meetings": {
      get: {
        summary: "List meetings",
        operationId: "listMeetings",
        tags: ["Meetings"],
        parameters: [
          {
            name: "entityId",
            in: "query" as const,
            schema: { type: "string" },
            description: "Filter by entity ID",
          },
          {
            name: "county",
            in: "query" as const,
            schema: { type: "string" },
            description: "Filter by county name",
          },
          {
            name: "entityType",
            in: "query" as const,
            schema: { type: "string", enum: ENTITY_TYPES },
            description: "Filter by entity type",
          },
          {
            name: "from",
            in: "query" as const,
            schema: { type: "string", format: "date" },
            description: "Start date (YYYY-MM-DD)",
          },
          {
            name: "to",
            in: "query" as const,
            schema: { type: "string", format: "date" },
            description: "End date (YYYY-MM-DD)",
          },
          {
            name: "page",
            in: "query" as const,
            schema: { type: "integer", default: 1 },
          },
          {
            name: "limit",
            in: "query" as const,
            schema: { type: "integer", default: 20, maximum: 100 },
          },
        ],
        responses: {
          "200": {
            description: "Paginated list of meetings (without full text)",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: {
                      type: "array",
                      items: {
                        $ref: "#/components/schemas/MeetingSummary",
                      },
                    },
                    pagination: {
                      $ref: "#/components/schemas/Pagination",
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
    "/meetings/{id}": {
      get: {
        summary: "Get a single meeting with full text",
        operationId: "getMeeting",
        tags: ["Meetings"],
        parameters: [
          {
            name: "id",
            in: "path" as const,
            required: true,
            schema: { type: "string" },
          },
        ],
        responses: {
          "200": {
            description: "Meeting details including plainText and minutesText",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: { $ref: "#/components/schemas/MeetingDetail" },
                  },
                },
              },
            },
          },
          "404": {
            description: "Meeting not found",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Error" },
              },
            },
          },
        },
      },
    },
    "/search": {
      get: {
        summary: "Full-text search across meeting minutes",
        operationId: "searchMeetings",
        tags: ["Search"],
        description:
          'PostgreSQL full-text search. Supports quoted phrases ("exact phrase"), OR operator (budget OR tax), and prefix matching (infra*).',
        parameters: [
          {
            name: "q",
            in: "query" as const,
            schema: { type: "string" },
            description: "Search query (min 2 characters)",
          },
          {
            name: "entity",
            in: "query" as const,
            schema: { type: "string" },
            description: "Filter by entity name (partial match)",
          },
          {
            name: "county",
            in: "query" as const,
            schema: { type: "string" },
            description: "Filter by county name (exact match)",
          },
          {
            name: "type",
            in: "query" as const,
            schema: { type: "string", enum: ENTITY_TYPES },
            description: "Filter by entity type",
          },
          {
            name: "from",
            in: "query" as const,
            schema: { type: "string", format: "date" },
          },
          {
            name: "to",
            in: "query" as const,
            schema: { type: "string", format: "date" },
          },
          {
            name: "sort",
            in: "query" as const,
            schema: {
              type: "string",
              enum: ["relevance", "date_desc", "date_asc"],
              default: "relevance",
            },
          },
          {
            name: "page",
            in: "query" as const,
            schema: { type: "integer", default: 1 },
          },
          {
            name: "limit",
            in: "query" as const,
            schema: { type: "integer", default: 20, maximum: 50 },
          },
        ],
        responses: {
          "200": {
            description: "Search results with highlighted snippets",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: {
                      type: "array",
                      items: {
                        $ref: "#/components/schemas/SearchResult",
                      },
                    },
                    pagination: {
                      $ref: "#/components/schemas/Pagination",
                    },
                  },
                },
              },
            },
          },
          "400": {
            description: "Missing query or filter",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/Error" },
              },
            },
          },
        },
      },
    },
    "/stats": {
      get: {
        summary: "Global statistics",
        operationId: "getStats",
        tags: ["Stats"],
        responses: {
          "200": {
            description: "Database statistics",
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    data: { $ref: "#/components/schemas/Stats" },
                  },
                },
              },
            },
          },
        },
      },
    },
  },
};

export async function GET() {
  return NextResponse.json(spec, {
    headers: { "Cache-Control": "public, max-age=3600" },
  });
}
