import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

function mockFetchOnce(body: unknown, init: Partial<Response> = {}) {
  const response = {
    ok: init.status ? init.status < 400 : true,
    status: init.status ?? 200,
    statusText: init.statusText ?? "OK",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  return response;
}

describe("api service", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses a successful JSON response", async () => {
    mockFetchOnce({ hello: "world" });
    const result = await api.get<{ hello: string }>("/api/whatever");
    expect(result.hello).toBe("world");
  });

  it("throws ApiError with the backend's detail message on failure", async () => {
    mockFetchOnce({ detail: "Meeting not found" }, { status: 404, statusText: "Not Found" });
    await expect(api.get("/api/meetings/missing")).rejects.toMatchObject({
      status: 404,
      message: "Meeting not found",
    });
  });

  it("falls back to statusText when the error body has no detail field", async () => {
    const response = {
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => {
        throw new Error("not json");
      },
      text: async () => "",
    } as unknown as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(api.get("/api/whatever")).rejects.toMatchObject({
      status: 500,
      message: "Internal Server Error",
    });
  });

  it("does not set a JSON Content-Type header when posting FormData (upload path)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({}),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    const form = new FormData();
    form.append("file", new Blob(["x"]), "x.wav");
    await api.postForm("/api/meetings", form);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers?.["Content-Type"]).toBeUndefined();
  });

  it("sets JSON Content-Type when posting a plain object body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({}),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    await api.post("/api/meetings/x/reanalyze", { analysis_language: "en" });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers?.["Content-Type"]).toBe("application/json");
    expect(options.body).toBe(JSON.stringify({ analysis_language: "en" }));
  });
});

// Re-export check: ApiError should be a real Error subclass with a status field.
describe("ApiError", () => {
  it("carries the HTTP status code", () => {
    const err = new ApiError(404, "not found");
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(404);
    expect(err.message).toBe("not found");
  });
});
