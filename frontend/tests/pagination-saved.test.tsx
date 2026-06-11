import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Pagination } from "../src/components/Pagination";
import { SavedSearches } from "../src/components/SavedSearches";
import type { SavedSearch } from "../src/lib/types";

describe("Pagination", () => {
  it("renders nothing when total is null", () => {
    const { container } = render(
      <Pagination total={null} shown={0} hasMore={false} loading={false} onNext={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows count and a working next button when more exist", () => {
    const onNext = vi.fn();
    render(<Pagination total={15} shown={5} hasMore={true} loading={false} onNext={onNext} />);
    expect(screen.getByText("Showing 5 of 15")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("pagination-next"));
    expect(onNext).toHaveBeenCalled();
  });

  it("disables next while loading", () => {
    render(<Pagination total={15} shown={5} hasMore={true} loading={true} onNext={() => {}} />);
    expect(screen.getByTestId("pagination-next")).toBeDisabled();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows end-of-results when no more", () => {
    render(<Pagination total={3} shown={3} hasMore={false} loading={false} onNext={() => {}} />);
    expect(screen.getByTestId("pagination-end")).toBeInTheDocument();
  });
});

describe("SavedSearches", () => {
  const saved: SavedSearch[] = [
    { id: "s1", owner: "o", query: "halal food", label: "halal food", tags: [] },
  ];

  it("shows empty state with no saved searches", () => {
    render(
      <SavedSearches
        saved={[]}
        currentQuery=""
        onSave={() => {}}
        onRun={() => {}}
        onDelete={() => {}}
        saving={false}
      />,
    );
    expect(screen.getByTestId("saved-empty")).toBeInTheDocument();
  });

  it("hides save button when no current query", () => {
    render(
      <SavedSearches
        saved={[]}
        currentQuery=""
        onSave={() => {}}
        onRun={() => {}}
        onDelete={() => {}}
        saving={false}
      />,
    );
    expect(screen.queryByTestId("saved-add")).toBeNull();
  });

  it("shows save button and fires onSave", () => {
    const onSave = vi.fn();
    render(
      <SavedSearches
        saved={[]}
        currentQuery="stadium"
        onSave={onSave}
        onRun={() => {}}
        onDelete={() => {}}
        saving={false}
      />,
    );
    fireEvent.click(screen.getByTestId("saved-add"));
    expect(onSave).toHaveBeenCalled();
  });

  it("disables save button and shows Saving while saving", () => {
    render(
      <SavedSearches
        saved={[]}
        currentQuery="stadium"
        onSave={() => {}}
        onRun={() => {}}
        onDelete={() => {}}
        saving={true}
      />,
    );
    expect(screen.getByTestId("saved-add")).toBeDisabled();
    expect(screen.getByText("Saving…")).toBeInTheDocument();
  });

  it("runs and deletes a saved search", () => {
    const onRun = vi.fn();
    const onDelete = vi.fn();
    render(
      <SavedSearches
        saved={saved}
        currentQuery="other"
        onSave={() => {}}
        onRun={onRun}
        onDelete={onDelete}
        saving={false}
      />,
    );
    fireEvent.click(screen.getByTestId("saved-run"));
    expect(onRun).toHaveBeenCalledWith("halal food");
    fireEvent.click(screen.getByTestId("saved-delete"));
    expect(onDelete).toHaveBeenCalledWith("s1");
  });
});
