import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { ModelInfo, RemoteProvider } from "../types";

interface SettingsData {
  general: { app_name: string; default_analysis_language: string };
  transcription: {
    default_provider: string;
    local_model: string;
    compute_type: string;
    cpu_threads: number;
    max_concurrent_jobs: number;
  };
  languages: { enabled: string[]; auto_detect_default: boolean };
  diarization: { enabled: boolean };
  llm: {
    provider: string;
    base_url: string;
    model: string;
    temperature: number;
    max_tokens: number;
    timeout_seconds: number;
    analysis_language: string;
  };
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [providers, setProviders] = useState<RemoteProvider[]>([]);
  const [newProvider, setNewProvider] = useState({
    name: "",
    base_url: "",
    endpoint_path: "/v1/audio/transcriptions",
    model: "",
    api_token: "",
  });
  const [testResult, setTestResult] = useState<Record<string, string>>({});
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const loadAll = () => {
    api.get<SettingsData>("/api/settings").then(setSettings).catch(() => {});
    api.get<ModelInfo[]>("/api/settings/models").then(setModels).catch(() => {});
    api.get<RemoteProvider[]>("/api/settings/remote-providers").then(setProviders).catch(() => {});
  };

  useEffect(loadAll, []);

  const saveSection = async (section: string, body: object) => {
    await api.put(`/api/settings/${section}`, body);
    setSavedMsg(`Saved ${section} settings.`);
    setTimeout(() => setSavedMsg(null), 2000);
    loadAll();
  };

  const downloadModel = async (name: string) => {
    try {
      await api.post(`/api/settings/models/${name}/download`);
      loadAll();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const deleteModel = async (name: string) => {
    if (!confirm(`Delete model '${name}' from disk?`)) return;
    await api.delete(`/api/settings/models/${name}`);
    loadAll();
  };

  const addProvider = async () => {
    try {
      await api.post("/api/settings/remote-providers", newProvider);
      setNewProvider({ name: "", base_url: "", endpoint_path: "/v1/audio/transcriptions", model: "", api_token: "" });
      loadAll();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const testProvider = async (id: string) => {
    const result = await api.post<{ success: boolean; message: string }>(`/api/settings/remote-providers/${id}/test`);
    setTestResult((prev) => ({ ...prev, [id]: `${result.success ? "OK" : "FAIL"}: ${result.message}` }));
  };

  const deleteProvider = async (id: string) => {
    if (!confirm("Delete this remote provider?")) return;
    await api.delete(`/api/settings/remote-providers/${id}`);
    loadAll();
  };

  if (!settings) return <p className="empty-state">Loading...</p>;

  return (
    <div>
      <h2 className="page-title">Settings</h2>
      {savedMsg && <div className="card">{savedMsg}</div>}

      <div className="card">
        <h3>General</h3>
        <div className="form-group">
          <label>Application Name</label>
          <input
            type="text"
            value={settings.general.app_name}
            onChange={(e) => setSettings({ ...settings, general: { ...settings.general, app_name: e.target.value } })}
          />
        </div>
        <button className="btn btn-primary" onClick={() => saveSection("general", settings.general)}>
          Save
        </button>
      </div>

      <div className="card">
        <h3>Transcription</h3>
        <div className="form-group">
          <label>Default Provider</label>
          <select
            value={settings.transcription.default_provider}
            onChange={(e) =>
              setSettings({
                ...settings,
                transcription: { ...settings.transcription, default_provider: e.target.value },
              })
            }
          >
            <option value="local">Local Model</option>
            {providers.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Local Model</label>
          <select
            value={settings.transcription.local_model}
            onChange={(e) =>
              setSettings({ ...settings, transcription: { ...settings.transcription, local_model: e.target.value } })
            }
          >
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Max Concurrent Jobs</label>
          <input
            type="number"
            min={1}
            value={settings.transcription.max_concurrent_jobs}
            onChange={(e) =>
              setSettings({
                ...settings,
                transcription: { ...settings.transcription, max_concurrent_jobs: Number(e.target.value) },
              })
            }
          />
        </div>
        <button className="btn btn-primary" onClick={() => saveSection("transcription", settings.transcription)}>
          Save
        </button>
      </div>

      <div className="card">
        <h3>Local Models</h3>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.name}>
                <td>
                  {m.name} {m.is_current_default && <span className="badge badge-processing">default</span>}
                </td>
                <td>{m.installed ? "Installed" : "Not installed"}</td>
                <td>
                  {!m.installed ? (
                    <button className="btn" onClick={() => downloadModel(m.name)}>
                      Download
                    </button>
                  ) : (
                    <button className="btn" onClick={() => deleteModel(m.name)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Remote Transcription Providers</h3>
        {providers.map((p) => (
          <div key={p.id} className="card">
            <strong>{p.name}</strong> — {p.base_url}
            {p.endpoint_path} (model: {p.model || "default"}) — token: {p.api_token_masked || "none"}
            <div style={{ marginTop: 8 }}>
              <button className="btn" onClick={() => testProvider(p.id)}>
                Test Connection
              </button>
              <button className="btn" onClick={() => deleteProvider(p.id)} style={{ marginLeft: 8 }}>
                Delete
              </button>
              {testResult[p.id] && <span style={{ marginLeft: 8 }}>{testResult[p.id]}</span>}
            </div>
          </div>
        ))}
        <h4>Add Provider</h4>
        <div className="form-group">
          <label>Name</label>
          <input type="text" value={newProvider.name} onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            placeholder="https://whisper.example.internal"
            value={newProvider.base_url}
            onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Endpoint Path</label>
          <input
            type="text"
            value={newProvider.endpoint_path}
            onChange={(e) => setNewProvider({ ...newProvider, endpoint_path: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Model</label>
          <input type="text" value={newProvider.model} onChange={(e) => setNewProvider({ ...newProvider, model: e.target.value })} />
        </div>
        <div className="form-group">
          <label>API Token</label>
          <input
            type="text"
            value={newProvider.api_token}
            onChange={(e) => setNewProvider({ ...newProvider, api_token: e.target.value })}
          />
        </div>
        <button className="btn btn-primary" onClick={addProvider}>
          Add Provider
        </button>
      </div>

      <div className="card">
        <h3>Speaker Diarization</h3>
        <div className="checkbox-row">
          <input
            type="checkbox"
            checked={settings.diarization.enabled}
            onChange={(e) => setSettings({ ...settings, diarization: { enabled: e.target.checked } })}
          />
          <span>Enabled by default</span>
        </div>
        <button className="btn btn-primary" onClick={() => saveSection("diarization", settings.diarization)}>
          Save
        </button>
      </div>

      <div className="card">
        <h3>LLM / Analysis</h3>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={settings.llm.base_url}
            onChange={(e) => setSettings({ ...settings, llm: { ...settings.llm, base_url: e.target.value } })}
          />
        </div>
        <div className="form-group">
          <label>Model</label>
          <input
            type="text"
            value={settings.llm.model}
            onChange={(e) => setSettings({ ...settings, llm: { ...settings.llm, model: e.target.value } })}
          />
        </div>
        <div className="form-group">
          <label>Temperature</label>
          <input
            type="number"
            step="0.1"
            value={settings.llm.temperature}
            onChange={(e) => setSettings({ ...settings, llm: { ...settings.llm, temperature: Number(e.target.value) } })}
          />
        </div>
        <div className="form-group">
          <label>Max Tokens</label>
          <input
            type="number"
            value={settings.llm.max_tokens}
            onChange={(e) => setSettings({ ...settings, llm: { ...settings.llm, max_tokens: Number(e.target.value) } })}
          />
        </div>
        <p className="muted">
          API keys are configured via the backend .env file and are never displayed or returned by the API.
        </p>
        <button className="btn btn-primary" onClick={() => saveSection("llm", settings.llm)}>
          Save
        </button>
      </div>
    </div>
  );
}
