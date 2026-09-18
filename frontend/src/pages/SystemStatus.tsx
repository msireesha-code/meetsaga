import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { SystemStatus as SystemStatusType } from "../types";

export default function SystemStatus() {
  const [status, setStatus] = useState<SystemStatusType | null>(null);

  useEffect(() => {
    api.get<SystemStatusType>("/api/system/status").then(setStatus).catch(() => {});
  }, []);

  if (!status) return <p className="empty-state">Loading...</p>;

  const rows: [string, string][] = [
    ["MeetSage Version", status.meetsage_version],
    ["Python Version", status.python_version],
    ["FFmpeg Version", status.ffmpeg_version || "Not found"],
    ["FFprobe Version", status.ffprobe_version || "Not found"],
    ["CPU Cores", String(status.cpu_count)],
    ["RAM Total", `${status.ram_total_gb} GB`],
    ["RAM Available", `${status.ram_available_gb} GB`],
    ["Disk Total", `${status.disk_total_gb} GB`],
    ["Disk Free", `${status.disk_free_gb} GB`],
    ["Installed Models", status.installed_models.join(", ") || "None"],
  ];

  return (
    <div>
      <h2 className="page-title">System Status</h2>
      <div className="card">
        <table>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <th>{label}</th>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(!status.ffmpeg_version || !status.ffprobe_version) && (
        <div className="card error-text">
          FFmpeg/FFprobe were not found on PATH. Install with: <code>sudo apt install ffmpeg</code>
        </div>
      )}
    </div>
  );
}
