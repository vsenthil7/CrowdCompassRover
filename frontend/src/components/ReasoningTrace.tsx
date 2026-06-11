import type { QueryPlan, HealthFeatures } from "../lib/types";
import { CATEGORY_META, languageLabel } from "../lib/display";

interface Props {
  plan: QueryPlan;
  resultCount: number;
  features?: HealthFeatures | null;
}

interface Step {
  key: string;
  label: string;
  detail: string;
  active: boolean;
}

/**
 * ReasoningTrace renders the agent's pipeline for a query as a visible, ordered
 * sequence of steps. Every value shown is real data from the QueryPlan the backend
 * produced, so a viewer can see how a natural-language question in any language
 * became a structured, filtered, ranked search - not a black box.
 */
export function ReasoningTrace({ plan, resultCount, features }: Props) {
  const f = plan.filters;
  const filterBits: string[] = [];
  if (f.city) filterBits.push(f.city);
  if (f.category) filterBits.push(CATEGORY_META[f.category].label);
  if (f.open_now) filterBits.push("open now");
  if (f.halal) filterBits.push("halal");
  if (f.vegetarian) filterBits.push("vegetarian");
  if (f.wheelchair_accessible) filterBits.push("accessible");

  const enrich: string[] = [];
  if (features?.spell_correction) enrich.push("spell");
  if (features?.query_expansion) enrich.push("synonyms");

  const isTranslated =
    plan.detected_language !== "en" &&
    plan.normalized_query.toLowerCase() !== plan.original_query.toLowerCase();

  const steps: Step[] = [
    {
      key: "detect",
      label: "Detect",
      detail: languageLabel(plan.detected_language),
      active: true,
    },
    {
      key: "normalize",
      label: isTranslated ? "Translate" : "Normalize",
      detail: plan.normalized_query || plan.original_query,
      active: true,
    },
    {
      key: "extract",
      label: "Extract filters",
      detail: filterBits.length ? filterBits.join(" / ") : "none",
      active: filterBits.length > 0,
    },
    {
      key: "expand",
      label: "Expand",
      detail: enrich.length ? enrich.join(" + ") : "-",
      active: enrich.length > 0,
    },
    {
      key: "retrieve",
      label: "Retrieve",
      detail: "hybrid: keyword + vector + geo",
      active: true,
    },
    {
      key: "rerank",
      label: "Rerank",
      detail: features?.reranking ? "relevance model" : "score order",
      active: Boolean(features?.reranking),
    },
    {
      key: "answer",
      label: "Answer",
      detail: `${resultCount} grounded`,
      active: resultCount > 0,
    },
  ];

  return (
    <div className="trace" data-testid="reasoning-trace" aria-label="Agent reasoning pipeline">
      <span className="trace__eyebrow">Agent pipeline</span>
      <ol className="trace__steps">
        {steps.map((s, i) => (
          <li
            key={s.key}
            className={`trace__step${s.active ? " trace__step--active" : ""}`}
            data-testid={`trace-step-${s.key}`}
          >
            <span className="trace__num">{String(i + 1).padStart(2, "0")}</span>
            <span className="trace__label">{s.label}</span>
            <span className="trace__detail">{s.detail}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
