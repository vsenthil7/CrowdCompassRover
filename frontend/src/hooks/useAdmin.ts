import { useCallback, useState } from "react";
import * as api from "../lib/api";
import { getSessionId } from "../lib/session";
import type { AdminStatus, AuditReport, OutboxStats, SloReport, UsageInfo, VersionInfo } from "../lib/types";

export interface AdminState {
  status: AdminStatus | null;
  usage: UsageInfo | null;
  audit: AuditReport | null;
  slo: SloReport | null;
  version: VersionInfo | null;
  outbox: OutboxStats | null;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, u, a, sl, v, o] = await Promise.all([
        api.adminStatus(),
        api.usage(getSessionId()),
        api.auditLog(),
        api.sloReport(),
        api.versionInfo(),
        api.outboxStats(),
      ]);
      setStatus(s);
      setUsage(u);
      setAudit(a);
      setSlo(sl);
      setVersion(v);
      setOutbox(o);
    } catch (e) {
      setError(message(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const reindex = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await api.reindex();
      await refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const flushCache = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await api.flushCache();
      await refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const relayOutbox = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await api.outboxRelay();
      await refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  return {
    state: { status, usage, audit, slo, version, outbox, loading, error, busy },
    refresh,
    reindex,
    flushCache,
    relayOutbox,
  };
}
