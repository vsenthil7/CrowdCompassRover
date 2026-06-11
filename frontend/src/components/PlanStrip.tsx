import type { QueryPlan } from "../lib/types";
import { CATEGORY_META, languageLabel } from "../lib/display";

interface Props {
  plan: QueryPlan;
}

export function PlanStrip({ plan }: Props) {
  const f = plan.filters;
  const activeFilters: string[] = [];
  if (f.city) activeFilters.push(f.city);
  if (f.category) activeFilters.push(CATEGORY_META[f.category].label);
  if (f.open_now) activeFilters.push("Open now");
  if (f.halal) activeFilters.push("Halal");
  if (f.vegetarian) activeFilters.push("Vegetarian");
  if (f.wheelchair_accessible) activeFilters.push("Accessible");

  return (
    <div className="plan-strip" data-testid="plan-strip">
      <span>
        Language <b>{languageLabel(plan.detected_language)}</b>
      </span>
      <span>
        Understood as <b>{plan.normalized_query || "—"}</b>
      </span>
      <span>
        Filters <b>{activeFilters.length ? activeFilters.join(", ") : "none"}</b>
      </span>
    </div>
  );
}
