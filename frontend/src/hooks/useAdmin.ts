import { useCallback, useState } from "react";
import * as api from "../lib/api";
import { getSessionId } from "../lib/session";
import type {
  AdminStatus,
  AnalyticsSnapshot,
  AuditReport,
  BulkheadStats,
  FlagsReport,
  OutboxStats,
  ReadinessReport,
  SloReport,
  TracesReport,
  UsageInfo,
  VersionInfo,
} from "../lib/types";

export interface AdminState {
  status: AdminStatus | null;
  usage: UsageInfo | null;
  audit: AuditReport | null;
  slo: SloReport | null;
  version: VersionInfo | null;
  outbox: OutboxStats | null;
  analytics: AnalyticsSnapshot | null;
  traces: TracesReport | null;
  flags: FlagsReport | null;
  readiness: ReadinessReport | null;
  bulkhead: BulkheadStats | null;
  loading: boolean;
  error: string | null;
  busy: boolean;
}

function message(e: unknown): string {
  return e instanceof Error ? e.message : "Unknown error";
}

export function useAdmin() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [audit, setAudit] = useState<AuditReport | null>(null);
  const [slo, setSlo] = useState<SloReport | null>(null);
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [outbox, setOutbox] = useState<OutboxStats | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSnapshot | null>(null);
  const [traces, setTraces] = useState<TracesReport | null>(null);
  const [flags, setFlags] = useState<FlagsReport | null>(null);
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [bulkhead, setBulkhead] = useState<BulkheadStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, u, a, sl, v, o, an, tr, fl, rd, bh] = await Promise.all([
        api.adminStatus(),
        api.usage(getSessionId()),
        api.auditLog(),
        api.sloReport(),
        api.versionInfo(),
        api.outboxStats(),
        api.analytics(),
        api.traces(),
        api.flags(),
        api.readiness(),
        api.bulkheadStats(),
      ]);
      setStatus(s);
      setUsage(u);
      setAudit(a);
      setSlo(sl);
      setVersion(v);
      setOutbox(o);
      setAnalytics(an);
      setTraces(tr);
      setFlags(fl);
      setReadiness(rd);
      setBulkhead(bh);
    } catch (e) {
      setError(message(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const runAction = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await fn();
        await refresh();
      } catch (e) {
        setError(message(e));
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const reindex = useCallback(() => runAction(api.reindex), [runAction]);
  const flushCache = useCallback(() => runAction(api.flushCache), [runAction]);
  const relayOutbox = useCallback(() => runAction(api.outboxRelay), [runAction]);
  const sweepRetention = useCallback(() => runAction(api.sweepRetention), [runAction]);

  return {
    state: {
      status, usage, audit, slo, version, outbox,
      analytics, traces, flags, readiness, bulkhead,
      loading, error, busy,
    },
    refresh,
    reindex,
    flushCache,
    relayOutbox,
    sweepRetention,
  };
}
