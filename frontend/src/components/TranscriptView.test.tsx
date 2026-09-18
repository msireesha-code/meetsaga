import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TranscriptView from "./TranscriptView";
import type { Meeting, Speaker, Transcript } from "../types";

const meeting: Meeting = {
  id: "m1",
  name: "Test Meeting",
  original_filename: "f.wav",
  media_type: "audio",
  expected_languages: ["en"],
  auto_detect_languages: false,
  duration_seconds: 10,
  created_at: new Date().toISOString(),
};

const transcript: Transcript = {
  id: "t1",
  version: 1,
  provider: "local",
  model: "small",
  languages_detected: ["en"],
  diarization_status: "completed",
  segments: [
    { id: "s0", seq: 0, start: 0, end: 3, speaker_label: "SPEAKER_00", language: "en", text: "Hello there." },
    { id: "s1", seq: 1, start: 3, end: 6, speaker_label: "SPEAKER_01", language: "en", text: "Hi back." },
  ],
};

describe("TranscriptView", () => {
  it("shows the raw speaker label when no display name is set", () => {
    render(
      <TranscriptView meeting={meeting} transcript={transcript} speakers={[]} onSpeakersChanged={() => {}} />
    );
    expect(screen.getByText("SPEAKER_00")).toBeInTheDocument();
    expect(screen.getByText("SPEAKER_01")).toBeInTheDocument();
  });

  it("shows the renamed display name instead of the raw speaker label in the transcript itself", () => {
    // Note: the separate "Speakers" panel intentionally still shows the raw
    // label alongside the rename (e.g. "SPEAKER_00 → Ajay") — only the
    // transcript segment list itself should show just the resolved name.
    const speakers: Speaker[] = [
      { id: "sp0", label: "SPEAKER_00", display_name: "Ajay" },
      { id: "sp1", label: "SPEAKER_01", display_name: "Sireesha" },
    ];
    const { container } = render(
      <TranscriptView meeting={meeting} transcript={transcript} speakers={speakers} onSpeakersChanged={() => {}} />
    );
    const speakerNamesInTranscript = Array.from(container.querySelectorAll(".transcript-segment .speaker")).map(
      (el) => el.textContent
    );
    expect(speakerNamesInTranscript).toEqual(["Ajay", "Sireesha"]);
  });

  it("renders both transcript segment texts", () => {
    render(
      <TranscriptView meeting={meeting} transcript={transcript} speakers={[]} onSpeakersChanged={() => {}} />
    );
    expect(screen.getByText("Hello there.")).toBeInTheDocument();
    expect(screen.getByText("Hi back.")).toBeInTheDocument();
  });

  it("shows an empty state when there are no segments", () => {
    render(
      <TranscriptView
        meeting={meeting}
        transcript={{ ...transcript, segments: [] }}
        speakers={[]}
        onSpeakersChanged={() => {}}
      />
    );
    expect(screen.getByText(/no speech segments were detected/i)).toBeInTheDocument();
  });

  it("renders a language tag for each segment", () => {
    render(
      <TranscriptView meeting={meeting} transcript={transcript} speakers={[]} onSpeakersChanged={() => {}} />
    );
    expect(screen.getAllByText("en")).toHaveLength(2);
  });

  it("uses an <audio> element for audio meetings and <video> for video meetings", () => {
    const { container, rerender } = render(
      <TranscriptView meeting={meeting} transcript={transcript} speakers={[]} onSpeakersChanged={() => {}} />
    );
    expect(container.querySelector("audio")).toBeTruthy();
    expect(container.querySelector("video")).toBeFalsy();

    rerender(
      <TranscriptView
        meeting={{ ...meeting, media_type: "video" }}
        transcript={transcript}
        speakers={[]}
        onSpeakersChanged={() => {}}
      />
    );
    expect(container.querySelector("video")).toBeTruthy();
  });
});
