import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import TranscriptView from "../components/TranscriptView";
import ActionItemsTable from "../components/ActionItemsTable";
import type { Analysis, Job, Meeting, Speaker, Transcript } from "../types";
import { LANGUAGE_NAMES } from "../types";

type Tab = "overview" | "transcript" | "analysis" | "action-items" | "exports";

function formatDuration(seconds: number | null): string {
  if (!seconds && seconds !== 0) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export default function MeetingDetail() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [tab, setTab] = useState<Tab>("overview");
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [seekRequest, setSeekRequest] = useState<{ time: number; nonce: number } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!meetingId) return;
    const m = await api.get<Meeting>(`/api/meetings/${meetingId}`);
    setMeeting(m);
    try {
      setJob(await api.get<Job>(`/api/meetings/${meetingId}/job`));
    } catch {
      setJob(null);
    }
    try {
      setTranscript(await api.get<Transcript>(`/api/meetings/${meetingId}/transcript`));
    } catch {
      setTranscript(null);
    }
    try {
      setAnalysis(await api.get<Analysis>(`/api/meetings/${meetingId}/analysis`));
    } catch {
      setAnalysis(null);
    }
    try {
      setSpeakers(await api.get<Speaker[]>(`/api/meetings/${meetingId}/speakers`));
    } catch {
      setSpeakers([]);
    }
  }, [meetingId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!job || job.status === "COMPLETED" || job.status === "FAILED" || job.status === "CANCELLED") return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [job, load]);

  const navigateToTranscript = (seconds: number) => {
    setTab("transcript");
    setSeekRequest({ time: seconds, nonce: Date.now() });
  };

  const reanalyze = async () => {
    setBusy(true);
    try {
      await api.post(`/api/meetings/${meetingId}/reanalyze`, {});
      await load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const rediarize = async () => {
    setBusy(true);
    try {
      await api.post(`/api/meetings/${meetingId}/rediarize`);
      await load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const retranscribe = async () => {
    if (!confirm("Re-transcribe this meeting? This creates a new transcript version; speaker labels will need to be re-diarized/renamed afterward.")) {
      return;
    }
    setBusy(true);
    try {
      await api.post(`/api/meetings/${meetingId}/retranscribe`);
      await load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!meeting) return <p className="empty-state">Loading...</p>;

  return (
    <div>
      <h2 className="page-title">{meeting.name}</h2>
      <div className="card" style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <div>
          <div className="muted">Date</div>
          <div>{new Date(meeting.created_at).toLocaleString()}</div>
        </div>
        <div>
          <div className="muted">Duration</div>
          <div>{formatDuration(meeting.duration_seconds)}</div>
        </div>
        <div>
          <div className="muted">Status</div>
          <div>{job ? <StatusBadge status={job.status} /> : "-"}</div>
        </div>
        <div>
          <div className="muted">Languages</div>
          <div>{meeting.expected_languages.map((l) => LANGUAGE_NAMES[l] || l).join(", ")}</div>
        </div>
        <div>
          <div className="muted">Speakers</div>
          <div>{speakers.length}</div>
        </div>
      </div>

      {job && job.status !== "COMPLETED" && job.status !== "FAILED" && (
        <div className="card">
          Processing: <strong>{job.stage}</strong> {job.progress != null && `(${job.progress}%)`}
        </div>
      )}
      {job?.status === "FAILED" && (
        <div className="card error-text">
          Processing failed at stage {job.stage}: {job.error}
        </div>
      )}

      <div className="tabs">
        {(["overview", "transcript", "analysis", "action-items", "exports"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "action-items" ? "Action Items" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="card">
          <h3>Executive Summary</h3>
          <p>{analysis?.summary || <span className="empty-state">Analysis not available yet.</span>}</p>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="value">{speakers.length}</div>
              <div className="label">Speakers</div>
            </div>
            <div className="stat-card">
              <div className="value">{transcript?.languages_detected.length ?? 0}</div>
              <div className="label">Languages Detected</div>
            </div>
            <div className="stat-card">
              <div className="value">{analysis?.action_items.length ?? 0}</div>
              <div className="label">Action Items</div>
            </div>
            <div className="stat-card">
              <div className="value">{analysis?.decisions.length ?? 0}</div>
              <div className="label">Decisions</div>
            </div>
          </div>
          {job && (
            <p className="muted">
              Transcription: {job.transcription_provider}/{job.transcription_model} in{" "}
              {job.transcription_duration_seconds?.toFixed(1)}s
              {job.analysis_duration_seconds != null && <> · Analysis in {job.analysis_duration_seconds.toFixed(1)}s</>}
            </p>
          )}
        </div>
      )}

      {tab === "transcript" &&
        (transcript ? (
          <div>
            <button className="btn" onClick={retranscribe} disabled={busy} style={{ marginBottom: 12 }}>
              Retry Transcription
            </button>
            <TranscriptView
              meeting={meeting}
              transcript={transcript}
              speakers={speakers}
              onSpeakersChanged={load}
              seekRequest={seekRequest}
            />
          </div>
        ) : (
          <p className="empty-state">Transcript not available yet.</p>
        ))}

      {tab === "analysis" && (
        <div>
          <button className="btn" onClick={reanalyze} disabled={busy || !transcript}>
            Re-run Analysis
          </button>
          <button className="btn" onClick={rediarize} disabled={busy || !transcript} style={{ marginLeft: 8 }}>
            Retry Diarization
          </button>
          {!analysis ? (
            <p className="empty-state">Analysis not available yet.</p>
          ) : (
            <>
              <div className="card">
                <h3>Executive Summary</h3>
                <p>{analysis.summary}</p>
              </div>
              <div className="card">
                <h3>Key Discussion Points</h3>
                {analysis.key_discussion_points.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.key_discussion_points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card">
                <h3>Decisions</h3>
                {analysis.decisions.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.decisions.map((d, i) => (
                      <li key={i}>
                        <a
                          href="#"
                          onClick={(e) => {
                            e.preventDefault();
                            const idx = d.source_segment_ids[0];
                            const seg = transcript?.segments[idx];
                            if (seg) navigateToTranscript(seg.start);
                          }}
                        >
                          {d.decision}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card">
                <h3>Action Items</h3>
                <ActionItemsTable
                  items={analysis.action_items}
                  segments={transcript?.segments}
                  onNavigate={navigateToTranscript}
                />
              </div>
              <div className="card">
                <h3>Open Issues</h3>
                {analysis.open_issues.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.open_issues.map((d, i) => (
                      <li key={i}>{d.issue}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card">
                <h3>Risks / Concerns</h3>
                {analysis.risks.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.risks.map((d, i) => (
                      <li key={i}>{d.risk}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card">
                <h3>Important Dates</h3>
                {analysis.important_dates.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.important_dates.map((d, i) => (
                      <li key={i}>
                        <strong>{d.date}</strong>: {d.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="card">
                <h3>Questions / Follow-ups</h3>
                {analysis.questions.length === 0 ? (
                  <p className="empty-state">None identified.</p>
                ) : (
                  <ul>
                    {analysis.questions.map((d, i) => (
                      <li key={i}>{d.question}</li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "action-items" && (
        <div className="card">
          {analysis ? (
            <ActionItemsTable
              items={analysis.action_items}
              segments={transcript?.segments}
              onNavigate={navigateToTranscript}
            />
          ) : (
            <p className="empty-state">Analysis not available yet.</p>
          )}
        </div>
      )}

      {tab === "exports" && (
        <div className="card">
          <h3>Transcript</h3>
          {["txt", "srt", "vtt", "json", "md"].map((fmt) => (
            <a
              key={fmt}
              className="btn"
              style={{ marginRight: 8, marginBottom: 8, display: "inline-block" }}
              href={api.mediaUrl(`/api/meetings/${meetingId}/export/transcript?format=${fmt}`)}
              target="_blank"
              rel="noreferrer"
            >
              {fmt.toUpperCase()}
            </a>
          ))}
          <h3>Analysis</h3>
          {["json", "md"].map((fmt) => (
            <a
              key={fmt}
              className="btn"
              style={{ marginRight: 8, display: "inline-block" }}
              href={api.mediaUrl(`/api/meetings/${meetingId}/export/analysis?format=${fmt}`)}
              target="_blank"
              rel="noreferrer"
            >
              {fmt.toUpperCase()}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
