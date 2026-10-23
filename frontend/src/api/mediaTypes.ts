/**
 * Media 模块独立类型定义（与 backend/media_database.py + routers/media.py 对齐）。
 *
 * 独立于现有 api/types.ts —— Media 模块不 import 任何现有业务类型。
 */
export type ClipEventType = "death" | "ace" | "multi_kill";

export interface Clip {
  id: string;
  match_id: string;
  event_type: string;
  label: string;
  severity: number;
  round_number: number | null;
  timestamp: string;
  map_name: string;
  duration_seconds: number;
  video_filename: string;
  kept: boolean;
  status: string;
  ai_title: string;
  ai_intro: string;
  created_at: string;
}

export interface ClipListResponse {
  clips: Clip[];
}

export interface MatchWithClips {
  match_id: string;
  clip_count: number;
  latest_at: string;
}

export interface MatchListResponse {
  matches: MatchWithClips[];
}

export interface MediaSettings {
  rollback_seconds: number;
  encoder: string;
  capture_audio: boolean;
  audio_device: string;
  ffmpeg_path: string;
  auto_generate_ai: boolean;
  min_multikill: number;
  recording_enabled: boolean;
  clips_save_path: string;
  auto_cleanup_enabled: boolean;
  cleanup_days: number;
}

export interface RecordingStatus {
  recording: boolean;
  match_id: string;
  updated_at: string;
}

export interface BatchActionRequest {
  clip_ids: string[];
  action: "keep" | "unkeep" | "delete";
}

export interface BatchActionResponse {
  ok: number;
  total: number;
}

export interface CleanupResponse {
  deleted: number;
  scanned: number;
}
