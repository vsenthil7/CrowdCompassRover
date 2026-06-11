import type { HealthStatus } from "../lib/types";

interface Props {
  health: HealthStatus;
}

const FEATURE_LABELS: Record<string, string> = {
  reranking: "Smart reranking",
  query_expansion: "Synonym expansion",
  spell_correction: "Spell tolerance",
};

export function FeaturePanel({ health }: Props) {
  const features = Object.entries(health.features);
  return (
    <div className="feature-panel" data-testid="feature-panel">
      <span className="feature-panel__label">Engine</span>
      {features.map(([key, on]) => (
        <span
          key={key}
          className={`feature-pill ${on ? "feature-pill--on" : "feature-pill--off"}`}
          data-testid={`feature-${key}`}
        >
          {FEATURE_LABELS[key] ?? key}
        </span>
      ))}
      <span className="feature-panel__sessions" data-testid="sessions-active">
        {health.sessions_active} active
      </span>
    </div>
  );
}
