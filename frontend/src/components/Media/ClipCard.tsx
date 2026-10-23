import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Play,
  Star,
  Trash2,
  RefreshCw,
  Skull,
  Flame,
  Trophy,
} from "lucide-react";
import { useMediaStore } from "@/store/mediaStore";
import { mediaApi } from "@/api/mediaClient";
import { useToast } from "@/components/common/Toast";
import { cn, formatRelative, friendlyMapName } from "@/lib/utils";
import type { Clip } from "@/api/mediaTypes";

/**
 * 单个片段卡片：封面 + AI 标题 + 元数据 + 操作按钮。
 *
 * 事件类型徽章颜色：
 * - ace        flame（橙红，最显眼）
 * - multi_kill cyan（青色，高光）
 * - death      mist（灰色，沉稳）
 */
function EventBadge({ eventType, severity }: { eventType: string; severity: number }) {
  const { t } = useTranslation();
  const cfg = (() => {
    if (eventType === "ace")
      return {
        icon: <Trophy className="h-3 w-3" />,
        cls: "bg-flame/15 text-flame-soft border-flame/30",
        label: t("media.filters.ace"),
      };
    if (eventType === "multi_kill")
      return {
        icon: <Flame className="h-3 w-3" />,
        cls: "bg-cyan-neon/15 text-cyan-soft border-cyan-neon/30",
        label: `${severity} ${t("media.unit.kills")}`,
      };
    return {
      icon: <Skull className="h-3 w-3" />,
      cls: "bg-ink-700/60 text-mist-300 border-mist-100/[0.08]",
      label: t("media.filters.death"),
    };
  })();
  return (
    <span
      className={cn(
        "flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider",
        cfg.cls,
      )}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

export default function ClipCard({ clip }: { clip: Clip }) {
  const { t } = useTranslation();
  const { show } = useToast();
  const setPlayingClip = useMediaStore((s) => s.setPlayingClip);
  const keepClip = useMediaStore((s) => s.keepClip);
  const deleteClip = useMediaStore((s) => s.deleteClip);
  const regenerateAssets = useMediaStore((s) => s.regenerateAssets);
  const selected = useMediaStore((s) => s.selectedClipIds.has(clip.id));
  const toggleSelect = useMediaStore((s) => s.toggleSelect);
  const [coverError, setCoverError] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

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
      className={cn(
        "glass-card group overflow-hidden transition-all duration-300 hover:-translate-y-0.5",
        selected && "ring-1 ring-cyan-neon/40",
      )}
    >
      {/* 封面 */}
      <button
        onClick={() => setPlayingClip(clip)}
        className="relative block aspect-video w-full overflow-hidden bg-ink-900"
      >
        {!coverError && clip.video_filename ? (
          <img
            src={mediaApi.coverUrl(clip.id)}
            alt={clip.ai_title || clip.label}
            onError={() => setCoverError(true)}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-ink-700 to-ink-900">
            <Play className="h-8 w-8 text-mist-400" />
          </div>
        )}
        {/* hover 播放遮罩 */}
        <div className="absolute inset-0 flex items-center justify-center bg-ink-900/40 opacity-0 transition-opacity group-hover:opacity-100">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-flame/80 shadow-glow">
            <Play className="h-5 w-5 fill-current text-white" />
          </span>
        </div>
        {/* 时长徽章 */}
        <span className="absolute bottom-2 right-2 rounded bg-ink-900/80 px-1.5 py-0.5 font-mono text-[10px] text-mist-100">
          {clip.duration_seconds}s
        </span>
        {/* 保留徽章 */}
        {clip.kept && (
          <span className="absolute left-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-lime-neon/20 backdrop-blur-sm">
            <Star className="h-3 w-3 fill-current text-lime-neon" />
          </span>
        )}
      </button>

      {/* 内容 */}
      <div className="p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <EventBadge eventType={clip.event_type} severity={clip.severity} />
          <span className="text-[10px] text-mist-400">
            {formatRelative(clip.created_at)}
          </span>
        </div>

        <h4 className="line-clamp-2 min-h-[2.5rem] text-sm font-medium leading-tight text-mist-100">
          {clip.ai_title || clip.label || clip.id.slice(0, 8)}
        </h4>
        {clip.ai_intro && (
          <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-mist-400">
            {clip.ai_intro}
          </p>
        )}

        {/* 元数据 */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-mist-400">
          {clip.map_name && (
            <span>{friendlyMapName(clip.map_name)}</span>
          )}
          {clip.round_number != null && (
            <span>
              {t("media.unit.round")} {clip.round_number}
            </span>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="mt-3 flex items-center justify-between border-t border-mist-100/[0.04] pt-2.5">
          <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-mist-300">
            <input
              type="checkbox"
              checked={selected}
              onChange={() => toggleSelect(clip.id)}
              className="h-3 w-3 accent-cyan-neon"
            />
            {t("media.select")}
          </label>
          <div className="flex items-center gap-1">
            <button
              onClick={() => keepClip(clip.id, !clip.kept)}
              title={clip.kept ? t("media.unkeep") : t("media.keep")}
              className={cn(
                "rounded-md p-1.5 transition-colors",
                clip.kept
                  ? "text-lime-neon hover:bg-lime-neon/10"
                  : "text-mist-400 hover:bg-ink-700/60 hover:text-mist-200",
              )}
            >
              <Star
                className={cn("h-3.5 w-3.5", clip.kept && "fill-current")}
              />
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              title={t("media.regenerate")}
              className="rounded-md p-1.5 text-mist-400 transition-colors hover:bg-ink-700/60 hover:text-cyan-soft disabled:opacity-50"
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5", regenerating && "animate-spin")}
              />
            </button>
            <button
              onClick={handleDelete}
              title={t("media.delete")}
              className="rounded-md p-1.5 text-mist-400 transition-colors hover:bg-flame/10 hover:text-flame"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
