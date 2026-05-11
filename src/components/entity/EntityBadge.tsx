import { Badge } from "@/components/ui/badge";
import { ENTITY_TYPE_LABELS } from "@/lib/constants";

const TYPE_COLORS: Record<string, string> = {
  COUNTY: "bg-blue-100 text-blue-800",
  TOWNSHIP: "bg-green-100 text-green-800",
  CITY: "bg-purple-100 text-purple-800",
  VILLAGE: "bg-orange-100 text-orange-800",
  SCHOOL_DISTRICT: "bg-red-100 text-red-800",
  ISD: "bg-rose-100 text-rose-800",
  STATE_BOARD: "bg-indigo-100 text-indigo-800",
  SPECIAL_DISTRICT: "bg-amber-100 text-amber-800",
};

export function EntityBadge({ type }: { type: string }) {
  return (
    <Badge
      variant="secondary"
      className={TYPE_COLORS[type] || "bg-gray-100 text-gray-800"}
    >
      {ENTITY_TYPE_LABELS[type] || type}
    </Badge>
  );
}
