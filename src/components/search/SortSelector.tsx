"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { ArrowUpDown } from "lucide-react";

const SORT_OPTIONS = [
  { value: "relevance", label: "Most relevant" },
  { value: "date_desc", label: "Newest first" },
  { value: "date_asc", label: "Oldest first" },
];

export function SortSelectorClient({ hasQuery }: { hasQuery: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSort =
    searchParams.get("sort") || (hasQuery ? "relevance" : "date_desc");

  function handleChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("sort", value);
    params.set("page", "1");
    router.push(`/search?${params.toString()}`);
  }

  const options = hasQuery
    ? SORT_OPTIONS
    : SORT_OPTIONS.filter((o) => o.value !== "relevance");

  return (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
      <select
        value={currentSort}
        onChange={(e) => handleChange(e.target.value)}
        className="rounded-md border border-input bg-background px-2 py-1.5 text-sm"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
