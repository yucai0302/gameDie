import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { X, RefreshCw, Star, Trash2 } from "lucide-react";
import { useMediaStore } from "@/store/mediaStore";
import { mediaApi } from "@/api/mediaClient";
import { useToast } from "@/components/common/Toast";
import { cn, friendlyMapName, formatRelative } from "@/lib/utils";

/**
 * 片段播放模态框：视频 + 字幕 + AI 标题/简介 + 操作。
 *
 * 通过 mediaStore.playingClip 控制（null 表示关闭）。
 * ESC 键关闭；点击遮罩关闭。
 */
export default function ClipPlayerModal() {
  const { t } = useTranslation();
  const { show } = useToast();
  const clip = useMediaStore((s) => s.playingClip);
  const setPlayingClip = useMediaStore((s) => s.setPlayingClip);
  const keepClip = useMediaStore((s) => s.keepClip);
  const deleteClip = useMediaStore((s) => s.deleteClip);
  const regenerateAssets = useMediaStore((s) => s.regenerateAssets);
  const [regenerating, setRegenerating] = useState(false);

  // ESC 关闭
  useEffect(() => {
    if (!clip) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPlayingClip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [clip, setPlayingClip]);

  if (!clip) return null;

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await regenerateAssets(clip.id);
      show(t("media.toast.regenerated"), "success");
    } catch {
      show(t("media.toast.regenerateFailed"), "error");
    } finally {
      setRegenerating(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(t("media.confirmDelete"))) return;
    try {
      await deleteClip(clip.id);
      show(t("media.toast.deleted"), "success");
    } catch {
      show(t("media.toast.deleteFailed"), "error");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/80 backdrop-blur-sm"
      onClick={() => setPlayingClip(null)}
    >
      <div
        className="glass-card relative w-[min(960px,92vw)] max-h-[88vh] overflow-y-auto p-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={() => setPlayingClip(null)}
          className="absolute right-3 top-3 z-10 rounded-md p-1.5 text-mist-300 transition-colors hover:bg-ink-700/60 hover:text-mist-100"
        >
          <X className="h-4 w-4" />
        </button>

        {/* 视频播放器 */}
        <div className="overflow-hidden rounded-xl bg-black">
          <video
            key={clip.id}
            controls
            autoPlay
            className="aspect-video w-full"
            poster={mediaApi.coverUrl(clip.id)}
          >
            <source src={mediaApi.videoUrl(clip.id)} type="video/mp4" />
            <track
              kind="subtitles"
              srcLang="zh"
              label="AI"
              src={mediaApi.subtitleUrl(clip.id)}
              default
            />
          </video>
        </div>

        {/* 元信息 */}
        <div className="mt-4 flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="font-display text-lg font-semibold text-mist-100">
              {clip.ai_title || clip.label || clip.id.slice(0, 8)}
            </h3>
            {clip.ai_intro && (
              <p className="mt-1.5 text-sm leading-relaxed text-mist-300">
                {clip.ai_intro}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-mist-400">
              {clip.map_name && (
                <span>{friendlyMapName(clip.map_name)}</span>
              )}
              {clip.round_number != null && (
                <span>
                  {t("media.unit.round")} {clip.round_number}
                </span>
              )}
              <span>{clip.duration_seconds}s</span>
              <span>{formatRelative(clip.created_at)}</span>
              {clip.match_id && (
                <span className="font-mono">
                  {t("media.recording.match")} {clip.match_id.slice(0, 8)}
                </span>
              )}
            </div>
          </div>

          {/* 操作 */}
          <div className="flex flex-shrink-0 items-center gap-2">
            <button
              onClick={() => keepClip(clip.id, !clip.kept)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                clip.kept
                  ? "border-lime-neon/30 bg-lime-neon/10 text-lime-soft"
                  : "border-mist-100/[0.08] bg-ink-800/60 text-mist-300 hover:text-mist-100",
              )}
            >
              <Star
                className={cn("h-3.5 w-3.5", clip.kept && "fill-current")}
              />
              {clip.kept ? t("media.unkeep") : t("media.keep")}
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              title={t("media.regenerate")}
              className="rounded-lg border border-mist-100/[0.08] bg-ink-800/60 p-2 text-mist-300 transition-colors hover:text-cyan-soft disabled:opacity-50"
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5", regenerating && "animate-spin")}
              />
            </button>
            <button
              onClick={handleDelete}
              title={t("media.delete")}
              className="rounded-lg border border-mist-100/[0.08] bg-ink-800/60 p-2 text-mist-300 transition-colors hover:border-flame/30 hover:text-flame"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* 阶段 B 占位：发布到抖音 */}
        <div className="mt-4 flex items-center justify-between rounded-lg border border-dashed border-mist-100/[0.08] bg-ink-800/30 px-4 py-2.5">
          <span className="text-xs text-mist-400">
            {t("media.publish.placeholder")}
          </span>
          <button
            disabled
            className="rounded-md bg-ink-700/60 px-3 py-1 text-xs text-mist-400"
          >
            {t("media.publish.douyin")}
          </button>
        </div>
      </div>
    </div>
  );
}
