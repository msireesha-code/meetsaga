import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import type { Job } from "../types";

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const load = () => api.get<Job[]>("/api/jobs").then(setJobs).catch(() => {});

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, []);

  const cancel = async (id: string) => {
    try {
      await api.post(`/api/jobs/${id}/cancel`);
      load();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  return (
    <div>
      <h2 className="page-title">Jobs</h2>
      <div className="card">
        {jobs.length === 0 ? (
          <p className="empty-state">No jobs yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Job</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Progress</th>
                <th>Transcription</th>
                <th>Analysis</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>
                    <Link to={`/meetings/${j.meeting_id}`}>{j.filename}</Link>
                  </td>
                  <td>
                    <StatusBadge status={j.status} />
                  </td>
                  <td>{j.stage}</td>
                  <td>{j.progress != null ? `${j.progress}%` : "-"}</td>
                  <td>
                    {j.transcription_provider ? `${j.transcription_provider}/${j.transcription_model}` : "-"}
                  </td>
                  <td>{j.analysis_provider ? `${j.analysis_provider}/${j.analysis_model}` : "-"}</td>
                  <td>{j.started_at ? new Date(j.started_at).toLocaleString() : "-"}</td>
                  <td>
                    {j.status === "QUEUED" && (
                      <button className="btn" onClick={() => cancel(j.id)}>
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {jobs.some((j) => j.error) && (
        <div className="card">
          <h3>Errors</h3>
          {jobs
            .filter((j) => j.error)
            .map((j) => (
              <p key={j.id} className="error-text">
                <strong>{j.filename}:</strong> {j.error}
              </p>
            ))}
        </div>
      )}
    </div>
  );
}
