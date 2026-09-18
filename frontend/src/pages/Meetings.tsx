import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { Meeting } from "../types";

export default function Meetings() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [q, setQ] = useState("");

  const load = (query: string) => {
    const path = query ? `/api/meetings?q=${encodeURIComponent(query)}` : "/api/meetings";
    api.get<Meeting[]>(path).then(setMeetings).catch(() => {});
  };

  useEffect(() => {
    load("");
  }, []);

  const onDelete = async (id: string) => {
    if (!confirm("Delete this meeting and all its data? This cannot be undone.")) return;
    await api.delete(`/api/meetings/${id}`);
    load(q);
  };

  return (
    <div>
      <h2 className="page-title">Meetings</h2>
      <div className="form-group" style={{ maxWidth: 320 }}>
        <input
          type="text"
          placeholder="Search meetings..."
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            load(e.target.value);
          }}
        />
      </div>
      <div className="card">
        {meetings.length === 0 ? (
          <p className="empty-state">No meetings found.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Meeting</th>
                <th>Type</th>
                <th>Languages</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.id}>
                  <td>
                    <Link to={`/meetings/${m.id}`}>{m.name}</Link>
                  </td>
                  <td>{m.media_type}</td>
                  <td>{m.expected_languages.join(", ")}</td>
                  <td>{new Date(m.created_at).toLocaleString()}</td>
                  <td>
                    <button className="btn" onClick={() => onDelete(m.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
