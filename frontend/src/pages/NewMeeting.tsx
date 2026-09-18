import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { ModelInfo, RemoteProvider } from "../types";
import { LANGUAGE_NAMES } from "../types";

const SUPPORTED_LANGS = ["en", "hi", "te"];

export default function NewMeeting() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [languages, setLanguages] = useState<string[]>(["en", "hi", "te"]);
  const [autoDetect, setAutoDetect] = useState(false);
  const [provider, setProvider] = useState("local");
  const [remoteProviders, setRemoteProviders] = useState<RemoteProvider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState("small");
  const [diarization, setDiarization] = useState(true);
  const [generateAnalysis, setGenerateAnalysis] = useState(true);
  const [analysisLanguage, setAnalysisLanguage] = useState("en");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get<ModelInfo[]>("/api/settings/models").then(setModels).catch(() => {});
    api.get<RemoteProvider[]>("/api/settings/remote-providers").then(setRemoteProviders).catch(() => {});
    api
      .get<{ transcription: { default_provider: string; local_model: string } }>("/api/settings")
      .then((s) => {
        setProvider(s.transcription.default_provider);
        setModel(s.transcription.local_model);
      })
      .catch(() => {});
  }, []);

  const toggleLanguage = (lang: string) => {
    setLanguages((prev) => (prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]));
  };

  const onSubmit = async () => {
    if (!file) {
      setError("Please select an audio or video file to upload.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      if (name) form.append("name", name);
      form.append("expected_languages", JSON.stringify(languages));
      form.append("auto_detect_languages", String(autoDetect));
      form.append("transcription_provider", provider);
      form.append("transcription_model", model);
      form.append("diarization_enabled", String(diarization));
      form.append("generate_analysis", String(generateAnalysis));
      form.append("analysis_language", analysisLanguage);

      const resp = await api.postForm<{ meeting_id: string; job_id: string }>("/api/meetings", form);
      navigate(`/meetings/${resp.meeting_id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const isRemote = provider !== "local";

  return (
    <div>
      <h2 className="page-title">New Meeting</h2>

      <div className="card">
        <div className="form-group">
          <label>Meeting Name (optional)</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional meeting name" />
        </div>

        <div className="form-group">
          <label>Upload Audio / Video</label>
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
            }}
          >
            {file ? (
              <span>{file.name} ({(file.size / (1024 * 1024)).toFixed(1)} MB)</span>
            ) : (
              <span>Drag & drop a file here, or click to browse</span>
            )}
            <input
              ref={inputRef}
              type="file"
              hidden
              accept=".m4a,.mp3,.wav,.flac,.ogg,.aac,.mp4,.mkv,.webm,.mov,.avi"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Expected Languages</label>
          {SUPPORTED_LANGS.map((lang) => (
            <div className="checkbox-row" key={lang}>
              <input type="checkbox" checked={languages.includes(lang)} onChange={() => toggleLanguage(lang)} />
              <span>{LANGUAGE_NAMES[lang]}</span>
            </div>
          ))}
          <div className="checkbox-row">
            <input type="checkbox" checked={autoDetect} onChange={(e) => setAutoDetect(e.target.checked)} />
            <span>Auto-detect additional languages</span>
          </div>
        </div>

        <div className="form-group">
          <label>Transcription Provider</label>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="local">Local Model</option>
            {remoteProviders.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name} (Remote)
              </option>
            ))}
          </select>
        </div>

        {isRemote && (
          <div className="privacy-warning">
            The meeting audio will be sent to the configured remote transcription server ("{provider}").
          </div>
        )}

        {!isRemote && (
          <div className="form-group">
            <label>Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name} {m.installed ? "(installed)" : "(will download)"}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="checkbox-row">
          <input type="checkbox" checked={diarization} onChange={(e) => setDiarization(e.target.checked)} />
          <span>Speaker Diarization</span>
        </div>

        <div className="checkbox-row">
          <input type="checkbox" checked={generateAnalysis} onChange={(e) => setGenerateAnalysis(e.target.checked)} />
          <span>Generate Meeting Analysis</span>
        </div>

        {generateAnalysis && (
          <div className="form-group">
            <label>Analysis Language</label>
            <select value={analysisLanguage} onChange={(e) => setAnalysisLanguage(e.target.value)}>
              {SUPPORTED_LANGS.map((lang) => (
                <option key={lang} value={lang}>
                  {LANGUAGE_NAMES[lang]}
                </option>
              ))}
            </select>
          </div>
        )}

        {error && <p className="error-text">{error}</p>}

        <button className="btn btn-primary" onClick={onSubmit} disabled={submitting}>
          {submitting ? "Uploading..." : "Start Processing"}
        </button>
      </div>
    </div>
  );
}
