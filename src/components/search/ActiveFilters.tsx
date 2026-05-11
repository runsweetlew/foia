"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { X } from "lucide-react";
import { ENTITY_TYPE_LABELS } from "@/lib/constants";

export function ActiveFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const filters: { key: string; label: string; value: string }[] = [];

  const type = searchParams.get("type");
  if (type) {
    filters.push({
      key: "type",
      label: "Type",
      value: ENTITY_TYPE_LABELS[type] || type,
    });
  }

  const county = searchParams.get("county");
  if (county) {
    filters.push({ key: "county", label: "County", value: county });
  }

  const entity = searchParams.get("entity");
  if (entity) {
    filters.push({ key: "entity", label: "Entity", value: entity });
  }

  const from = searchParams.get("from");
  if (from) {
    filters.push({ key: "from", label: "From", value: from });
  }

  const to = searchParams.get("to");
  if (to) {
    filters.push({ key: "to", label: "To", value: to });
  }

  if (filters.length === 0) return null;

  function removeFilter(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(key);
    params.set("page", "1");
    router.push(`/search?${params.toString()}`);
  }

  function clearAll() {
    const params = new URLSearchParams();
    const q = searchParams.get("q");
    if (q) params.set("q", q);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-muted-foreground">
        Filters:
      </span>
      {filters.map((f) => (
        <button
          key={f.key}
          onClick={() => removeFilter(f.key)}
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
        >
          {f.label}: {f.value}
          <X className="h-3 w-3" />
        </button>
      ))}
      {filters.length > 1 && (
        <button
          onClick={clearAll}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
