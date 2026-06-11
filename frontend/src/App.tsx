import { useRover } from "./hooks/useRover";
import { SearchControls } from "./components/SearchControls";
import { PlanStrip } from "./components/PlanStrip";
import { AnswerCard } from "./components/AnswerCard";
import { ResultRow } from "./components/ResultRow";
import { FeaturePanel } from "./components/FeaturePanel";
import { HistoryPanel } from "./components/HistoryPanel";
import "./styles/app.css";

const EXAMPLES = [
  "halal food open now",
  "dónde cambiar dinero",
  "nearest transit to stadium",
  "où est le stade",
];

export function App() {
  const { state, setQuery, setUseLocation, run } = useRover();
  const { response, answer, loading, error, health, history } = state;

  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="brand">
          <span className="brand__kicker">2026 World Cup · Host City Agent</span>
          <h1 className="brand__title">
            CrowdCompass <span>Rover</span>
          </h1>
        </div>
        {health ? (
          <span className="mode-chip" data-mode={health.mode} data-testid="mode-chip">
            {health.mode} mode
          </span>
        ) : null}
      </header>

      {health ? <FeaturePanel health={health} /> : null}

      <SearchControls
        query={state.query}
        onQueryChange={setQuery}
        onSubmit={() => run()}
        useLocation={state.useLocation}
        onToggleLocation={setUseLocation}
        loading={loading}
        examples={EXAMPLES}
        onExample={(q) => run(q)}
      />

      {error ? (
        <div className="error" data-testid="error">
          {error}
        </div>
      ) : null}

      {answer ? <AnswerCard answer={answer} /> : null}

      {response ? <PlanStrip plan={response.plan} /> : null}

      {response && response.results.length > 0 ? (
        <div className="board">
          {response.results.map((hit, i) => (
            <ResultRow key={hit.event.id} hit={hit} index={i} />
          ))}
        </div>
      ) : null}

      {response && response.results.length === 0 && !loading ? (
        <div className="empty" data-testid="empty">
          No matching places found. Try another phrasing or language.
        </div>
      ) : null}

      {!response && !error && !loading ? (
        <div className="empty">
          Ask for stadiums, food, transit, currency exchange or fan zones — in any language.
        </div>
      ) : null}

      <HistoryPanel history={history} onReplay={(q) => run(q)} />
    </div>
  );
}
