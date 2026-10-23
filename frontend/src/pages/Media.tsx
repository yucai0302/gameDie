import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Film, Star, Trash2, RefreshCw, Info } from "lucide-react";
import { useMediaStore } from "@/store/mediaStore";
import RecordingStatus from "@/components/Media/RecordingStatus";
import RecordingSettings from "@/components/Media/RecordingSettings";
import ClipFilters from "@/components/Media/ClipFilters";
import ClipCard from "@/components/Media/ClipCard";
import ClipPlayerModal from "@/components/Media/ClipPlayerModal";
import MediaEmpty from "@/components/Media/MediaEmpty";
import { useToast } from "@/components/common/Toast";

/**
 * Media 库页面：本地精彩片段管理 + 录屏配置。
 *
 * 独立页面（功能范畴文档 §7.1）：
 * - 不 import 现有 Dashboard/Timeline/Review 业务组件
 * - 仅依赖 mediaStore / mediaClient / wsBus（均独立于现有 store/api）
 * - 复用通用组件 Card / Toast（与现有页面同级共享，非业务耦合）
 */
export default function Media() {
  const { t } = useTranslation();
  const { show } = useToast();
  const clips = useMediaStore((s) => s.clips);
  const loading = useMediaStore((s) => s.loading);
  const error = useMediaStore((s) => s.error);
  const settings = useMediaStore((s) => s.settings);
  const loadAll = useMediaStore((s) => s.loadAll);
  const selectedClipIds = useMediaStore((s) => s.selectedClipIds);
  const selectAll = useMediaStore((s) => s.selectAll);
  const clearSelection = useMediaStore((s) => s.clearSelection);
  const batchAction = useMediaStore((s) => s.batchAction);

  // 进入页面加载一次 + 每 30s 刷新一次（WS 事件已驱动局部更新，轮询仅兜底）
  useEffect(() => {
    loadAll();
    const id = setInterval(loadAll, 30000);
    return () => clearInterval(id);
  }, [loadAll]);

  const handleBatch = async (action: "keep" | "unkeep" | "delete") => {
    if (selectedClipIds.size === 0) return;
    if (action === "delete" && !confirm(t("media.confirmBatchDelete"))) return;
    try {
      await batchAction(action);
      show(t("media.toast.batchDone"), "success");
    } catch {
      show(t("media.toast.batchFailed"), "error");
    }
  };

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1280px] space-y-4">
        {/* 标题区 */}
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-flame/20 to-transparent border border-flame/30">
            <Film className="h-4 w-4 text-flame" />
          </span>
          <div className="flex-1">
            <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
              {t("media.title")}
            </h1>
            <p className="mt-0.5 text-xs text-mist-400">
              {t("media.subtitle")}
            </p>
          </div>
          <RecordingStatus />
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="rounded-lg border border-flame/30 bg-flame/10 px-4 py-2 text-xs text-flame-soft">
            {error}
          </div>
        )}

        {/* 片段库 */}
        <div className="glass-card p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-sm font-medium text-mist-100">
                {t("media.library.title")}
              </h2>
              <p className="mt-0.5 text-xs text-mist-400">
                {t("media.library.hint", { count: clips.length })}
              </p>
            </div>
            <ClipFilters />
          </div>

          {/* 自动清理提示横幅：未保留片段达到天数后自动清理 */}
          {settings?.auto_cleanup_enabled && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-cyan-neon/15 bg-cyan-neon/[0.04] px-3 py-2">
              <Info className="h-3.5 w-3.5 flex-shrink-0 text-cyan-soft" />
              <span className="text-xs text-mist-300">
                {t("media.cleanupBanner", {
                  days: settings.cleanup_days,
                })}
              </span>
            </div>
          )}
          {!settings?.auto_cleanup_enabled && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-mist-100/[0.06] bg-ink-800/30 px-3 py-2">
              <Info className="h-3.5 w-3.5 flex-shrink-0 text-mist-400" />
              <span className="text-xs text-mist-400">
                {t("media.cleanupDisabled")}
              </span>
            </div>
          )}

          {/* 批量操作工具栏 */}
          {selectedClipIds.size > 0 && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-cyan-neon/20 bg-cyan-neon/5 px-3 py-2">
              <span className="text-xs text-cyan-soft">
                {t("media.selected", { count: selectedClipIds.size })}
              </span>
              <div className="flex-1" />
              <button
                onClick={() => handleBatch("keep")}
                className="flex items-center gap-1 rounded-md bg-lime-neon/10 px-2.5 py-1 text-xs text-lime-soft transition-colors hover:bg-lime-neon/20"
              >
                <Star className="h-3 w-3" />
                {t("media.batchKeep")}
              </button>
              <button
                onClick={() => handleBatch("unkeep")}
                className="flex items-center gap-1 rounded-md bg-ink-700/60 px-2.5 py-1 text-xs text-mist-300 transition-colors hover:bg-ink-600"
              >
                <RefreshCw className="h-3 w-3" />
                {t("media.batchUnkeep")}
              </button>
              <button
                onClick={() => handleBatch("delete")}
                className="flex items-center gap-1 rounded-md bg-flame/10 px-2.5 py-1 text-xs text-flame-soft transition-colors hover:bg-flame/20"
              >
                <Trash2 className="h-3 w-3" />
                {t("media.batchDelete")}
              </button>
              <button
                onClick={clearSelection}
                className="rounded-md px-2 py-1 text-xs text-mist-400 hover:text-mist-200"
              >
                {t("media.clearSelection")}
              </button>
            </div>
          )}

          {/* 片段网格 */}
          {loading && clips.length === 0 ? (
            <div className="py-20 text-center text-sm text-mist-400">
              {t("common.loading")}
            </div>
          ) : clips.length === 0 ? (
            <MediaEmpty />
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between">
                <button
                  onClick={
                    selectedClipIds.size === clips.length
                      ? clearSelection
                      : selectAll
                  }
                  className="text-xs text-mist-400 transition-colors hover:text-mist-200"
                >
                  {selectedClipIds.size === clips.length
                    ? t("media.deselectAll")
                    : t("media.selectAll")}
                </button>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {clips.map((clip) => (
                  <ClipCard key={clip.id} clip={clip} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* 录屏配置 */}
        <RecordingSettings />
      </div>

      {/* 片段播放模态框（全局单例） */}
      <ClipPlayerModal />
    </div>
  );
}
