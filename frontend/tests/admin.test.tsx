import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, renderHook, act } from "@testing-library/react";
import { UsageView } from "../src/components/UsageView";
import { AdminDashboard } from "../src/components/AdminDashboard";
import { useAdmin } from "../src/hooks/useAdmin";
import type { AdminStatus, AuditReport, UsageInfo } from "../src/lib/types";

vi.mock("../src/lib/api");
import * as api from "../src/lib/api";
const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>;

const status: AdminStatus = {
  events: 16,
  cache_size: 4,
  cache_hit_rate: 0.75,
  data_stale: false,
  data_age_seconds: 42,
  flags: { reranking: true },
};

const usage: UsageInfo = {
  tenant: "t",
  period: "2026-06",
  count: 3,
  by_action: { search: 2, chat: 1 },
  remaining: 7,
  quota: 10,
};

const audit: AuditReport = {
  verified: true,
  count: 2,
  entries: [
    { seq: 1, actor: "a", tenant: "t", action: "search", resource: "q", outcome: "success", ts: 1 },
    { seq: 2, actor: "a", tenant: "t", action: "reindex", resource: "all", outcome: "success", ts: 2 },
  ],
};

describe("UsageView", () => {
  it("renders usage bar and action breakdown", () => {
    render(<UsageView usage={usage} />);
    expect(screen.getByTestId("usage-view")).toBeInTheDocument();
    expect(screen.getByText(/3 of 10 used/)).toBeInTheDocument();
    expect(screen.getAllByTestId("usage-action")).toHaveLength(2);
  });

  it("handles zero quota and no actions", () => {
    render(<UsageView usage={{ ...usage, quota: 0, by_action: {} }} />);
    expect(screen.queryAllByTestId("usage-action")).toHaveLength(0);
  });
});

describe("AdminDashboard", () => {
  it("renders status, usage, and audit", () => {
    render(
      <AdminDashboard
        status={status}
        usage={usage}
        audit={audit}
        loading={false}
        busy={false}
        error={null}
        onRefresh={() => {}}
        onReindex={() => {}}
        onFlush={() => {}}
      />,
    );
    expect(screen.getByTestId("admin-status")).toBeInTheDocument();
    expect(screen.getByTestId("usage-view")).toBeInTheDocument();
    expect(screen.getByTestId("audit-integrity")).toHaveTextContent("verified");
    expect(screen.getAllByTestId("audit-row").length).toBeGreaterThan(0);
  });

  it("shows tampered audit state", () => {
    render(
      <AdminDashboard
        status={{ ...status, data_stale: true }}
        usage={null}
        audit={{ ...audit, verified: false }}
        loading={false}
        busy={false}
        error={null}
        onRefresh={() => {}}
        onReindex={() => {}}
        onFlush={() => {}}
      />,
    );
    expect(screen.getByTestId("audit-integrity")).toHaveTextContent("tampered");
    expect(screen.getByText(/stale/)).toBeInTheDocument();
  });

  it("renders nothing-but-actions when data is null and shows error", () => {
    render(
      <AdminDashboard
        status={null}
        usage={null}
        audit={null}
        loading={true}
        busy={false}
        error="boom"
        onRefresh={() => {}}
        onReindex={() => {}}
        onFlush={() => {}}
      />,
    );
    expect(screen.getByTestId("admin-error")).toHaveTextContent("boom");
    expect(screen.queryByTestId("admin-status")).toBeNull();
    expect(screen.getByText("Refreshing…")).toBeInTheDocument();
  });

  it("fires refresh on click and keyboard", () => {
    const onRefresh = vi.fn();
    render(
      <AdminDashboard
        status={status}
        usage={null}
        audit={null}
        loading={false}
        busy={false}
        error={null}
        onRefresh={onRefresh}
        onReindex={() => {}}
        onFlush={() => {}}
      />,
    );
    fireEvent.click(screen.getByTestId("admin-refresh"));
    fireEvent.keyDown(screen.getByTestId("admin-refresh"), { key: "Enter" });
    expect(onRefresh).toHaveBeenCalledTimes(2);
  });

  it("fires reindex and flush, disabled when busy", () => {
    const onReindex = vi.fn();
    const onFlush = vi.fn();
    const { rerender } = render(
      <AdminDashboard
        status={status}
        usage={null}
        audit={null}
        loading={false}
        busy={false}
        error={null}
        onRefresh={() => {}}
        onReindex={onReindex}
        onFlush={onFlush}
      />,
    );
    fireEvent.click(screen.getByTestId("admin-reindex"));
    fireEvent.click(screen.getByTestId("admin-flush"));
    expect(onReindex).toHaveBeenCalled();
    expect(onFlush).toHaveBeenCalled();
    rerender(
      <AdminDashboard
        status={status}
        usage={null}
        audit={null}
        loading={false}
        busy={true}
        error={null}
        onRefresh={() => {}}
        onReindex={onReindex}
        onFlush={onFlush}
      />,
    );
    expect(screen.getByTestId("admin-reindex")).toBeDisabled();
    expect(screen.getByText("Working…")).toBeInTheDocument();
  });
});

describe("useAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.adminStatus = vi.fn().mockResolvedValue(status);
    mockedApi.usage = vi.fn().mockResolvedValue(usage);
    mockedApi.auditLog = vi.fn().mockResolvedValue(audit);
    mockedApi.reindex = vi.fn().mockResolvedValue({ indexed: 16, healthy: true });
    mockedApi.flushCache = vi.fn().mockResolvedValue({ flushed: true });
  });

  it("refresh loads status, usage, audit", async () => {
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.state.status?.events).toBe(16);
    expect(result.current.state.usage?.remaining).toBe(7);
    expect(result.current.state.audit?.verified).toBe(true);
  });

  it("refresh captures errors", async () => {
    mockedApi.adminStatus = vi.fn().mockRejectedValue(new Error("nope"));
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.state.error).toBe("nope");
  });

  it("reindex then refreshes", async () => {
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.reindex();
    });
    expect(mockedApi.reindex).toHaveBeenCalled();
    expect(mockedApi.adminStatus).toHaveBeenCalled();
  });

  it("reindex captures errors", async () => {
    mockedApi.reindex = vi.fn().mockRejectedValue("weird");
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.reindex();
    });
    expect(result.current.state.error).toBe("Unknown error");
  });

  it("flushCache then refreshes", async () => {
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.flushCache();
    });
    expect(mockedApi.flushCache).toHaveBeenCalled();
  });

  it("flushCache captures errors", async () => {
    mockedApi.flushCache = vi.fn().mockRejectedValue(new Error("flush fail"));
    const { result } = renderHook(() => useAdmin());
    await act(async () => {
      await result.current.flushCache();
    });
    expect(result.current.state.error).toBe("flush fail");
  });
});
