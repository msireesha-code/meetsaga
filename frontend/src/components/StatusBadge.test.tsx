import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBadge from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders COMPLETED with the completed style", () => {
    render(<StatusBadge status="COMPLETED" />);
    const badge = screen.getByText("COMPLETED");
    expect(badge).toHaveClass("badge-completed");
  });

  it("renders FAILED with the failed style", () => {
    render(<StatusBadge status="FAILED" />);
    expect(screen.getByText("FAILED")).toHaveClass("badge-failed");
  });

  it("renders CANCELLED with the failed style", () => {
    render(<StatusBadge status="CANCELLED" />);
    expect(screen.getByText("CANCELLED")).toHaveClass("badge-failed");
  });

  it("renders QUEUED with the queued style", () => {
    render(<StatusBadge status="QUEUED" />);
    expect(screen.getByText("QUEUED")).toHaveClass("badge-queued");
  });

  it("renders any in-progress stage with the processing style", () => {
    render(<StatusBadge status="TRANSCRIBING" />);
    expect(screen.getByText("TRANSCRIBING")).toHaveClass("badge-processing");
  });
});
