/**
 * Media 模块独立状态 store。
 *
 * 设计原则（功能范畴文档 §7.1 / §7.4）：
 * - 独立于现有 useStore.ts，不污染现有 store 状态
 * - 删除本文件 + 移除 TopNav/App/useWebSocket 中的少数引用，现有前端正常编译
 * - 通过 lib/wsBus.ts 订阅 media_* 事件，自动刷新数据
 */
import { create } from "zustand";
import { mediaApi } from "@/api/mediaClient";
import { onMediaEvent } from "@/lib/wsBus";
import type {
  Clip,
  MediaSettings,
  RecordingStatus,
} from "@/api/mediaTypes";

interface MediaState {
  // 数据
  clips: Clip[];
  matches: { match_id: string; clip_count: number; latest_at: string }[];
  settings: MediaSettings | null;
  recordingStatus: RecordingStatus | null;

  // 筛选
  filterMatchId: string;
  filterEventType: string;
  filterKeptOnly: boolean;
  selectedClipIds: Set<string>;

  // 加载态
  loading: boolean;
  error: string | null;

  // 模态框
  playingClip: Clip | null;

  // ---- Actions ----
  loadAll: () => Promise<void>;
  loadClips: () => Promise<void>;
  loadSettings: () => Promise<void>;
  loadRecordingStatus: () => Promise<void>;

  setFilter: (
    patch: Partial<
      Pick<
        MediaState,
        "filterMatchId" | "filterEventType" | "filterKeptOnly"
      >
    >,
  ) => void;

  toggleSelect: (clipId: string) => void;
  selectAll: () => void;
  clearSelection: () => void;

  keepClip: (clipId: string, kept: boolean) => Promise<void>;
  deleteClip: (clipId: string) => Promise<void>;
  batchAction: (
    action: "keep" | "unkeep" | "delete",
  ) => Promise<void>;
  regenerateAssets: (clipId: string) => Promise<void>;
  saveSettings: (patch: Partial<MediaSettings>) => Promise<void>;

  setPlayingClip: (clip: Clip | null) => void;

  // 由 WS 事件触发的局部更新（避免全量刷新）
  _onClipReady: (clip: Clip) => void;
  _onRecordingStatus: (status: RecordingStatus) => void;
}

const DEFAULT_SETTINGS: MediaSettings = {
  rollback_seconds: 30,
  encoder: "auto",
  capture_audio: false,
  audio_device: "",
  ffmpeg_path: "ffmpeg",
  auto_generate_ai: true,
  min_multikill: 3,
  recording_enabled: true,
  clips_save_path: "",
  auto_cleanup_enabled: true,
  cleanup_days: 3,
};

export const useMediaStore = create<MediaState>((set, get) => {
  // 启动时订阅 WS 事件（订阅是 idempotent 的，store 单例所以只订阅一次）
  onMediaEvent("media_clip_ready", (clip) => {
    get()._onClipReady(clip);
  });
  onMediaEvent("media_recording_status", (status) => {
    get()._onRecordingStatus(status);
  });

  return {
    clips: [],
    matches: [],
    settings: null,
    recordingStatus: null,

    filterMatchId: "",
    filterEventType: "",
    filterKeptOnly: false,
    selectedClipIds: new Set<string>(),

    loading: false,
    error: null,

    playingClip: null,

    loadAll: async () => {
      set({ loading: true, error: null });
      try {
        const [clipsRes, matchesRes, settings, recordingStatus] =
          await Promise.all([
            mediaApi.listClips({
              matchId: get().filterMatchId || undefined,
              eventType: get().filterEventType || undefined,
              keptOnly: get().filterKeptOnly,
            }),
            mediaApi.listMatches(),
            mediaApi.getSettings(),
            mediaApi.getRecordingStatus(),
          ]);
        set({
          clips: clipsRes.clips,
          matches: matchesRes.matches,
          settings,
          recordingStatus,
          loading: false,
        });
      } catch (e) {
        set({
          loading: false,
          error: e instanceof Error ? e.message : String(e),
        });
      }
    },

    loadClips: async () => {
      try {
        const res = await mediaApi.listClips({
          matchId: get().filterMatchId || undefined,
          eventType: get().filterEventType || undefined,
          keptOnly: get().filterKeptOnly,
        });
        set({ clips: res.clips });
      } catch (e) {
        set({
          error: e instanceof Error ? e.message : String(e),
        });
      }
    },

    loadSettings: async () => {
      try {
        const settings = await mediaApi.getSettings();
        set({ settings });
      } catch {
        set({ settings: DEFAULT_SETTINGS });
      }
    },

    loadRecordingStatus: async () => {
      try {
        const status = await mediaApi.getRecordingStatus();
        set({ recordingStatus: status });
      } catch {
        // 静默
      }
    },

    setFilter: (patch) => {
      set(patch);
      get().loadClips();
    },

    toggleSelect: (clipId) => {
      const cur = new Set(get().selectedClipIds);
      if (cur.has(clipId)) cur.delete(clipId);
      else cur.add(clipId);
      set({ selectedClipIds: cur });
    },

    selectAll: () => {
      set({
        selectedClipIds: new Set(get().clips.map((c) => c.id)),
      });
    },

    clearSelection: () => {
      set({ selectedClipIds: new Set<string>() });
    },

    keepClip: async (clipId, kept) => {
      const updated = await mediaApi.keepClip(clipId, kept);
      set({
        clips: get().clips.map((c) => (c.id === clipId ? updated : c)),
      });
    },

    deleteClip: async (clipId) => {
      await mediaApi.deleteClip(clipId);
      set({
        clips: get().clips.filter((c) => c.id !== clipId),
        selectedClipIds: (() => {
          const s = new Set(get().selectedClipIds);
          s.delete(clipId);
          return s;
        })(),
        playingClip:
          get().playingClip?.id === clipId ? null : get().playingClip,
      });
    },

    batchAction: async (action) => {
      const ids = Array.from(get().selectedClipIds);
      if (ids.length === 0) return;
      await mediaApi.batchAction({ clip_ids: ids, action });
      set({ selectedClipIds: new Set<string>() });
      await get().loadClips();
    },

    regenerateAssets: async (clipId) => {
      const updated = await mediaApi.regenerateAssets(clipId);
      set({
        clips: get().clips.map((c) => (c.id === clipId ? updated : c)),
        playingClip:
          get().playingClip?.id === clipId ? updated : get().playingClip,
      });
    },

    saveSettings: async (patch) => {
      const updated = await mediaApi.updateSettings(patch);
      set({ settings: updated });
    },

    setPlayingClip: (clip) => set({ playingClip: clip }),

    _onClipReady: (clip) => {
      // 新片段就绪：合并到列表头部，避免全量刷新
      const exists = get().clips.some((c) => c.id === clip.id);
      set({
        clips: exists
          ? get().clips.map((c) => (c.id === clip.id ? clip : c))
          : [clip, ...get().clips],
      });
    },

    _onRecordingStatus: (status) => {
      set({ recordingStatus: status });
    },
  };
});
