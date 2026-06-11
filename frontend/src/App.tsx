import { useRover } from "./hooks/useRover";
import { useAdmin } from "./hooks/useAdmin";
import { useState } from "react";
import { SearchControls } from "./components/SearchControls";
import { PlanStrip } from "./components/PlanStrip";
import { AnswerCard } from "./components/AnswerCard";
import { ResultRow } from "./components/ResultRow";
import { FeaturePanel } from "./components/FeaturePanel";
import { HistoryPanel } from "./components/HistoryPanel";
import { RoutePanel } from "./components/RoutePanel";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Pagination } from "./components/Pagination";
import { SavedSearches } from "./components/SavedSearches";
import { AdminDashboard } from "./components/AdminDashboard";
import { onActivate } from "./lib/a11y";
import "./styles/app.css";

const EXAMPLES = [
  "halal food open now",
  "dónde cambiar dinero",
  "nearest transit to stadium",
  "où est le stade",
];

export function App() {
  const { state, setQuery, setUseLocation, run, loadMore, routeTo, clearRoute, saveCurrent, removeSaved } =
    useRover();
  const { response, results, answer, loading, error, health, history, routeView, saved } = state;
  const admin = useAdmin();
  const [showAdmin, setShowAdmin] = useState(false);

  const toggleAdmin = () => {
    const next = !showAdmin;
    setShowAdmin(next);
    if (next && admin.state.status === null) {
      void admin.refresh();
    }
  };

  return (
    <ErrorBoundary>
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
          <span
            className="admin-toggle"
            role="button"
            tabIndex={0}
            onClick={toggleAdmin}
            onKeyDown={onActivate(toggleAdmin)}
            aria-pressed={showAdmin}
            data-testid="admin-toggle"
          >
            {showAdmin ? "Hide ops" : "Ops"}
          </span>
        </header>

        {showAdmin ? (
          <AdminDashboard
            status={admin.state.status}
            usage={admin.state.usage}
            audit={admin.state.audit}
            slo={admin.state.slo}
            version={admin.state.version}
            loading={admin.state.loading}
            busy={admin.state.busy}
            error={admin.state.error}
            onRefresh={admin.refresh}
            onReindex={admin.reindex}
            onFlush={admin.flushCache}
          />
        ) : null}

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

        {routeView ? (
          <RoutePanel
            routes={routeView.routes}
            destinationName={routeView.destinationName}
            onClose={clearRoute}
          />
        ) : null}

        {answer ? <AnswerCard answer={answer} /> : null}

        {response ? <PlanStrip plan={response.plan} /> : null}

        {response && results.length > 0 ? (
          <>
            <div className="board">
              {results.map((hit, i) => (
                <ResultRow key={`${hit.event.id}-${i}`} hit={hit} index={i} onRoute={routeTo} />
              ))}
            </div>
            <Pagination
              total={response.total}
              shown={results.length}
              hasMore={Boolean(response.next_cursor)}
              loading={state.pageLoading}
              onNext={loadMore}
            />
          </>
        ) : null}

        {response && results.length === 0 && !loading ? (
          <div className="empty" data-testid="empty">
            No matching places found. Try another phrasing or language.
          </div>
        ) : null}

        {!response && !error && !loading ? (
          <div className="empty">
            Ask for stadiums, food, transit, currency exchange or fan zones — in any language.
          </div>
        ) : null}

        <SavedSearches
          saved={saved}
          currentQuery={state.query}
          onSave={saveCurrent}
          onRun={(q) => run(q)}
          onDelete={removeSaved}
          saving={state.saving}
        />

        <HistoryPanel history={history} onReplay={(q) => run(q)} />
      </div>
    </ErrorBoundary>
  );
}
