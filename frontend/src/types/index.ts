export interface Meeting {
  id: string;
  name: string;
  original_filename: string;
  media_type: "audio" | "video";
  expected_languages: string[];
  auto_detect_languages: boolean;
  duration_seconds: number | null;
  created_at: string;
}

export interface Job {
  id: string;
  meeting_id: string;
  filename: string;
  status: string;
  stage: string;
  progress: number | null;
  started_at: string | null;
  ended_at: string | null;
  error: string | null;
  transcription_provider: string | null;
  transcription_model: string | null;
  analysis_provider: string | null;
  analysis_model: string | null;
  transcription_duration_seconds: number | null;
  diarization_duration_seconds: number | null;
  analysis_duration_seconds: number | null;
  created_at: string;
}

export interface TranscriptSegment {
  id: string;
  seq: number;
  start: number;
  end: number;
  speaker_label: string | null;
  language: string | null;
  text: string;
}

export interface Transcript {
  id: string;
  version: number;
  provider: string | null;
  model: string | null;
  languages_detected: string[];
  diarization_status: string;
  segments: TranscriptSegment[];
}

export interface Speaker {
  id: string;
  label: string;
  display_name: string | null;
}

export interface ActionItem {
  id: string;
  action: string;
  owner: string;
  due_date: string;
  priority: string;
  timestamp: string | null;
  source_segment_ids: number[];
  context: string | null;
}

export interface Analysis {
  id: string;
  version: number;
  provider: string | null;
  model: string | null;
  language: string;
  summary: string | null;
  key_discussion_points: string[];
  decisions: { decision: string; source_segment_ids: number[] }[];
  open_issues: { issue: string; source_segment_ids: number[] }[];
  risks: { risk: string; source_segment_ids: number[] }[];
  important_dates: { date: string; description: string; source_segment_ids: number[] }[];
  questions: { question: string; source_segment_ids: number[] }[];
  action_items: ActionItem[];
  created_at: string;
}

export interface RemoteProvider {
  id: string;
  name: string;
  base_url: string;
  endpoint_path: string;
  model: string | null;
  auth_method: string;
  connect_timeout_seconds: number;
  read_timeout_seconds: number;
  total_timeout_seconds: number;
  tls_verify: boolean;
  api_token_masked: string;
}

export interface SystemStatus {
  meetsage_version: string;
  python_version: string;
  ffmpeg_version: string | null;
  ffprobe_version: string | null;
  cpu_count: number;
  ram_total_gb: number;
  ram_available_gb: number;
  disk_total_gb: number;
  disk_free_gb: number;
  installed_models: string[];
}

export interface DashboardStats {
  total_meetings: number;
  completed: number;
  processing: number;
  failed: number;
  total_meeting_duration_seconds: number;
  total_action_items: number;
}

export interface ModelInfo {
  name: string;
  installed: boolean;
  is_current_default: boolean;
}

export const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  hi: "Hindi",
  te: "Telugu",
};
