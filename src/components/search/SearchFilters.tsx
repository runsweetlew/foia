"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { ENTITY_TYPE_LABELS, MICHIGAN_COUNTIES } from "@/lib/constants";

export function SearchFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentType = searchParams.get("type") || "";
  const currentCounty = searchParams.get("county") || "";
  const currentFrom = searchParams.get("from") || "";
  const currentTo = searchParams.get("to") || "";
  const currentEntity = searchParams.get("entity") || "";

  const [entityInput, setEntityInput] = useState(currentEntity);

  function updateFilter(key: string, value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set("page", "1");
    router.push(`/search?${params.toString()}`);
  }

  function handleEntitySubmit(e: React.FormEvent) {
    e.preventDefault();
    updateFilter("entity", entityInput.trim() || null);
  }

  return (
    <div className="space-y-6">
      {/* Entity name search */}
      <div>
        <h3 className="mb-3 font-semibold text-foreground">Entity Name</h3>
        <form onSubmit={handleEntitySubmit} className="flex gap-1.5">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={entityInput}
              onChange={(e) => setEntityInput(e.target.value)}
              placeholder="e.g. Ann Arbor"
              className="w-full rounded-md border border-input bg-background pl-7 pr-2 py-1.5 text-sm"
            />
          </div>
          <button
            type="submit"
            className="rounded-md bg-primary px-2.5 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            Go
          </button>
        </form>
        {currentEntity && (
          <button
            onClick={() => {
              setEntityInput("");
              updateFilter("entity", null);
            }}
            className="mt-1 text-xs text-primary hover:underline"
          >
            Clear
          </button>
        )}
      </div>

      {/* Entity type */}
      <div>
        <h3 className="mb-3 font-semibold text-foreground">Entity Type</h3>
        <div className="space-y-1.5">
          {Object.entries(ENTITY_TYPE_LABELS).map(([value, label]) => (
            <label
              key={value}
              className="flex cursor-pointer items-center gap-2"
            >
              <input
                type="radio"
                name="type"
                value={value}
                checked={currentType === value}
                onChange={() => updateFilter("type", value)}
                className="text-primary"
              />
              <span className="text-sm text-muted-foreground">{label}</span>
            </label>
          ))}
          {currentType && (
            <button
              onClick={() => updateFilter("type", null)}
              className="text-xs text-primary hover:underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* County */}
      <div>
        <h3 className="mb-3 font-semibold text-foreground">County</h3>
        <select
          value={currentCounty}
          onChange={(e) => updateFilter("county", e.target.value || null)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Counties</option>
          {MICHIGAN_COUNTIES.map((county) => (
            <option key={county} value={county}>
              {county}
            </option>
          ))}
        </select>
      </div>

      {/* Date range */}
      <div>
        <h3 className="mb-3 font-semibold text-foreground">Date Range</h3>
        <div className="space-y-2">
          <div>
            <label className="text-xs text-muted-foreground">From</label>
            <input
              type="date"
              value={currentFrom}
              onChange={(e) => updateFilter("from", e.target.value || null)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">To</label>
            <input
              type="date"
              value={currentTo}
              onChange={(e) => updateFilter("to", e.target.value || null)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
