import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

interface SearchResults {
  meetings: { id: string; name: string }[];
  transcript_segments: { id: string; transcript_id: string; text: string; start: number }[];
  analyses: { id: string; meeting_id: string; summary: string }[];
  action_items: { id: string; action: string; owner: string }[];
  speakers: { id: string; display_name: string | null; label: string }[];
}

export default function Search() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);

  const runSearch = async (query: string) => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    setLoading(true);
    try {
      const data = await api.get<SearchResults>(`/api/search?q=${encodeURIComponent(query)}`);
      setResults(data);
    } finally {
      setLoading(false);
    }
  };

  const onChange = (value: string) => {
    setQ(value);
    runSearch(value);
  };

  const hasAnyResults =
    results &&
    (results.meetings.length ||
      results.transcript_segments.length ||
      results.analyses.length ||
      results.action_items.length ||
      results.speakers.length);

  return (
    <div>
      <h2 className="page-title">Search</h2>
      <div className="form-group" style={{ maxWidth: 420 }}>
        <input
          type="text"
          autoFocus
          placeholder="Search meetings, transcripts, summaries, action items, speakers..."
          value={q}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>

      {loading && <p className="empty-state">Searching...</p>}

      {!loading && q && !hasAnyResults && <p className="empty-state">No results for "{q}".</p>}

      {results && results.meetings.length > 0 && (
        <div className="card">
          <h3>Meetings</h3>
          <ul>
            {results.meetings.map((m) => (
              <li key={m.id}>
                <Link to={`/meetings/${m.id}`}>{m.name}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {results && results.transcript_segments.length > 0 && (
        <div className="card">
          <h3>Transcript Matches</h3>
          <ul>
            {results.transcript_segments.map((s) => (
              <li key={s.id}>{s.text}</li>
            ))}
          </ul>
        </div>
      )}

      {results && results.analyses.length > 0 && (
        <div className="card">
          <h3>Summaries</h3>
          <ul>
            {results.analyses.map((a) => (
              <li key={a.id}>
                <Link to={`/meetings/${a.meeting_id}`}>{a.summary}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {results && results.action_items.length > 0 && (
        <div className="card">
          <h3>Action Items</h3>
          <ul>
            {results.action_items.map((a) => (
              <li key={a.id}>
                {a.action} — <span className="muted">{a.owner}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {results && results.speakers.length > 0 && (
        <div className="card">
          <h3>Speakers</h3>
          <ul>
            {results.speakers.map((s) => (
              <li key={s.id}>{s.display_name || s.label}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
