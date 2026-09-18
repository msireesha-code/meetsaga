import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { DashboardStats, Meeting } from "../types";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<Meeting[]>([]);

  useEffect(() => {
    api.get<DashboardStats>("/api/dashboard/stats").then(setStats).catch(() => {});
    api.get<Meeting[]>("/api/dashboard/recent-meetings").then(setRecent).catch(() => {});
  }, []);

  return (
    <div>
      <h2 className="page-title">Dashboard</h2>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="value">{stats?.total_meetings ?? "-"}</div>
          <div className="label">Total Meetings</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats?.completed ?? "-"}</div>
          <div className="label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats?.processing ?? "-"}</div>
          <div className="label">Processing</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats?.failed ?? "-"}</div>
          <div className="label">Failed</div>
        </div>
        <div className="stat-card">
          <div className="value">{formatDuration(stats?.total_meeting_duration_seconds ?? null)}</div>
          <div className="label">Total Duration</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats?.total_action_items ?? "-"}</div>
          <div className="label">Action Items</div>
        </div>
      </div>

      <div className="card">
        <h3>Recent Meetings</h3>
        {recent.length === 0 ? (
          <p className="empty-state">
            No meetings yet. <Link to="/new-meeting">Start your first meeting.</Link>
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Meeting</th>
                <th>Date</th>
                <th>Duration</th>
                <th>Languages</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((m) => (
                <tr key={m.id}>
                  <td>
                    <Link to={`/meetings/${m.id}`}>{m.name}</Link>
                  </td>
                  <td>{new Date(m.created_at).toLocaleString()}</td>
                  <td>{formatDuration(m.duration_seconds)}</td>
                  <td>{m.expected_languages.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
