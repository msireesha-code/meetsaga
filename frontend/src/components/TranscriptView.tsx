import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { Meeting, Speaker, Transcript } from "../types";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function TranscriptView({
  meeting,
  transcript,
  speakers,
  onSpeakersChanged,
  seekRequest,
}: {
  meeting: Meeting;
  transcript: Transcript;
  speakers: Speaker[];
  onSpeakersChanged: () => void;
  seekRequest?: { time: number; nonce: number } | null;
}) {
  const mediaRef = useRef<HTMLVideoElement & HTMLAudioElement>(null);
  const segmentRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [activeSegmentId, setActiveSegmentId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const speakerName = (label: string | null) => {
    if (!label) return "Unknown";
    const sp = speakers.find((s) => s.label === label);
    return sp?.display_name || label;
  };

  useEffect(() => {
    const el = mediaRef.current;
    if (!el) return;
    const onTimeUpdate = () => {
      const t = el.currentTime;
      const active = transcript.segments.find((s) => t >= s.start && t < s.end);
      if (active) {
        setActiveSegmentId(active.id);
        const ref = segmentRefs.current[active.id];
        ref?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    };
    el.addEventListener("timeupdate", onTimeUpdate);
    return () => el.removeEventListener("timeupdate", onTimeUpdate);
  }, [transcript]);

  const seekTo = (seconds: number) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = seconds;
      mediaRef.current.play().catch(() => {});
    }
  };

  useEffect(() => {
    if (seekRequest != null) {
      seekTo(seekRequest.time);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seekRequest?.nonce]);

  const submitRename = async (speakerId: string) => {
    await api.patch(`/api/meetings/${meeting.id}/speakers/${speakerId}`, { display_name: renameValue });
    setRenamingId(null);
    onSpeakersChanged();
  };

  const mediaUrl = api.mediaUrl(`/api/meetings/${meeting.id}/media`);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <div>
        {meeting.media_type === "video" ? (
          <video ref={mediaRef} src={mediaUrl} controls style={{ width: "100%", borderRadius: 8 }} />
        ) : (
          <audio ref={mediaRef} src={mediaUrl} controls style={{ width: "100%" }} />
        )}

        <div className="card" style={{ marginTop: 12 }}>
          <h4 style={{ marginTop: 0 }}>Speakers</h4>
          {speakers.length === 0 && <p className="empty-state">No speakers identified.</p>}
          {speakers.map((sp) => (
            <div key={sp.id} className="checkbox-row">
              {renamingId === sp.id ? (
                <>
                  <input
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    style={{ width: 160 }}
                  />
                  <button className="btn" onClick={() => submitRename(sp.id)}>
                    Save
                  </button>
                  <button className="btn" onClick={() => setRenamingId(null)}>
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <span>
                    {sp.label} → <strong>{sp.display_name || "(unnamed)"}</strong>
                  </span>
                  <button
                    className="btn"
                    onClick={() => {
                      setRenamingId(sp.id);
                      setRenameValue(sp.display_name || "");
                    }}
                  >
                    Rename
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ maxHeight: 520, overflowY: "auto" }}>
        {transcript.segments.length === 0 ? (
          <p className="empty-state">No speech segments were detected in this recording.</p>
        ) : (
          transcript.segments.map((seg) => (
            <div
              key={seg.id}
              ref={(el) => {
                segmentRefs.current[seg.id] = el;
              }}
              className={`transcript-segment ${activeSegmentId === seg.id ? "active" : ""}`}
              onClick={() => seekTo(seg.start)}
            >
              <div className="meta">
                {formatTime(seg.start)} <span className="speaker">{speakerName(seg.speaker_label)}</span>
                {seg.language && <span className="lang-tag">{seg.language}</span>}
              </div>
              <div>{seg.text}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export { formatTime };
