import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ActionItemsTable from "./ActionItemsTable";
import type { ActionItem } from "../types";

function makeItem(overrides: Partial<ActionItem> = {}): ActionItem {
  return {
    id: "1",
    action: "Ship the release",
    owner: "Not specified",
    due_date: "Not specified",
    priority: "Not specified",
    timestamp: "00:01:00",
    source_segment_ids: [0],
    context: null,
    ...overrides,
  };
}

describe("ActionItemsTable", () => {
  it("shows an empty state when there are no items", () => {
    render(<ActionItemsTable items={[]} onNavigate={() => {}} />);
    expect(screen.getByText(/no action items identified/i)).toBeInTheDocument();
  });

  it("renders 'Not specified' fields distinctly rather than blank or guessed", () => {
    render(<ActionItemsTable items={[makeItem()]} onNavigate={() => {}} />);
    const notSpecified = screen.getAllByText("Not specified");
    expect(notSpecified.length).toBe(3); // owner, due_date, priority
    notSpecified.forEach((el) => expect(el).toHaveClass("not-specified"));
  });

  it("renders explicit owner/due date/priority as plain values, not italicized", () => {
    render(
      <ActionItemsTable
        items={[makeItem({ owner: "Ravi", due_date: "Friday", priority: "High" })]}
        onNavigate={() => {}}
      />
    );
    expect(screen.getByText("Ravi")).toBeInTheDocument();
    expect(screen.getByText("Friday")).toBeInTheDocument();
    const priorityCell = screen.getByText("High");
    expect(priorityCell).toHaveClass("priority-high");
    expect(priorityCell).not.toHaveClass("not-specified");
  });

  it("clicking a timestamp navigates using the source segment's start time, not the raw timestamp string", async () => {
    const onNavigate = vi.fn();
    const segments = [
      { id: "s0", seq: 0, start: 42.5, end: 45, speaker_label: null, language: "en", text: "hi" },
    ];
    render(
      <ActionItemsTable
        items={[makeItem({ timestamp: "00:01:00", source_segment_ids: [0] })]}
        onNavigate={onNavigate}
        segments={segments}
      />
    );
    await userEvent.click(screen.getByText("00:01:00"));
    expect(onNavigate).toHaveBeenCalledWith(42.5);
  });

  it("falls back to parsing the timestamp string when no segments are provided", async () => {
    const onNavigate = vi.fn();
    render(
      <ActionItemsTable
        items={[makeItem({ timestamp: "00:01:05", source_segment_ids: [] })]}
        onNavigate={onNavigate}
      />
    );
    await userEvent.click(screen.getByText("00:01:05"));
    expect(onNavigate).toHaveBeenCalledWith(65);
  });
});
