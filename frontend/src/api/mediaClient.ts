/**
 * Media 模块独立 HTTP 客户端。
 *
 * 设计原则（功能范畴文档 §7.1）：
 * - 独立于现有 api/client.ts，不 import 现有业务类型 / api 对象
 * - 复用同一后端地址（API_BASE / WS_URL），但所有方法仅访问 /api/media/* 前缀
 * - 文件下载用原始 URL（视频/字幕/封面通过 <video>/<track>/<img> 加载）
 */
import type {
  BatchActionRequest,
  BatchActionResponse,
  Clip,
  ClipListResponse,
  CleanupResponse,
  MatchListResponse,
  MediaSettings,
  RecordingStatus,
} from "./mediaTypes";

// 复用现有后端地址，但通过自定义常量，避免直接 import api/client.ts
const MEDIA_API_BASE = "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${MEDIA_API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const mediaApi = {
  // ---- 片段查询 ----
  listClips: (params: {
    matchId?: string;
    eventType?: string;
    keptOnly?: boolean;
  } = {}) => {
    const qs = new URLSearchParams();
    if (params.matchId) qs.set("match_id", params.matchId);
    if (params.eventType) qs.set("event_type", params.eventType);
    if (params.keptOnly) qs.set("kept_only", "true");
    const query = qs.toString();
    return request<ClipListResponse>(
      `/api/media/clips${query ? `?${query}` : ""}`,
    );
  },

  listMatches: () =>
    request<MatchListResponse>("/api/media/matches"),

  getClip: (clipId: string) =>
    request<Clip>(`/api/media/clips/${clipId}`),

  // ---- 片段管理 ----
  keepClip: (clipId: string, kept: boolean) =>
    request<Clip>(`/api/media/clips/${clipId}/keep`, {
      method: "PUT",
      body: JSON.stringify({ kept }),
    }),

  deleteClip: (clipId: string) =>
    request<{ ok: boolean; id: string }>(`/api/media/clips/${clipId}`, {
      method: "DELETE",
    }),

  batchAction: (payload: BatchActionRequest) =>
    request<BatchActionResponse>("/api/media/clips/batch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  regenerateAssets: (clipId: string) =>
    request<Clip>(`/api/media/clips/${clipId}/regenerate`, {
      method: "POST",
    }),

  cleanupTemp: (daysOld = 3) =>
    request<CleanupResponse>(
      `/api/media/cleanup?days_old=${daysOld}`,
      { method: "POST" },
    ),

  // ---- 录屏配置 ----
  getSettings: () =>
    request<MediaSettings>("/api/media/settings"),

  updateSettings: (patch: Partial<MediaSettings>) =>
    request<MediaSettings>("/api/media/settings", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  // ---- 录屏状态 ----
  getRecordingStatus: () =>
    request<RecordingStatus>("/api/media/recording/status"),

  // ---- 媒体文件 URL（直接给 <video>/<track>/<img> 用） ----
  videoUrl: (clipId: string) =>
    `${MEDIA_API_BASE}/api/media/clips/${clipId}/video`,
  subtitleUrl: (clipId: string) =>
    `${MEDIA_API_BASE}/api/media/clips/${clipId}/subtitle`,
  coverUrl: (clipId: string) =>
    `${MEDIA_API_BASE}/api/media/clips/${clipId}/cover`,
};
