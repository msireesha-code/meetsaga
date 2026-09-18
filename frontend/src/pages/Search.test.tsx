import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Search from "./Search";

function mockSearchResponse(body: object) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => body,
    } as unknown as Response)
  );
}

describe("Search page", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not search until the user types something", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<Search />, { wrapper: MemoryRouter });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows meeting results returned from the search API", async () => {
    mockSearchResponse({
      meetings: [{ id: "m1", name: "Sprint Planning" }],
      transcript_segments: [],
      analyses: [],
      action_items: [],
      speakers: [],
    });
    render(<Search />, { wrapper: MemoryRouter });

    await userEvent.type(screen.getByPlaceholderText(/search meetings/i), "Sprint");

    await waitFor(() => {
      expect(screen.getByText("Sprint Planning")).toBeInTheDocument();
    });
  });

  it("shows a no-results message when nothing matches", async () => {
    mockSearchResponse({
      meetings: [],
      transcript_segments: [],
      analyses: [],
      action_items: [],
      speakers: [],
    });
    render(<Search />, { wrapper: MemoryRouter });

    await userEvent.type(screen.getByPlaceholderText(/search meetings/i), "nothingmatchesthis");

    await waitFor(() => {
      expect(screen.getByText(/no results for/i)).toBeInTheDocument();
    });
  });

  it("shows action items with their owner", async () => {
    mockSearchResponse({
      meetings: [],
      transcript_segments: [],
      analyses: [],
      action_items: [{ id: "a1", action: "Ship the release", owner: "Ravi" }],
      speakers: [],
    });
    render(<Search />, { wrapper: MemoryRouter });

    await userEvent.type(screen.getByPlaceholderText(/search meetings/i), "ship");

    await waitFor(() => {
      expect(screen.getByText(/Ship the release/)).toBeInTheDocument();
      expect(screen.getByText("Ravi")).toBeInTheDocument();
    });
  });
});
