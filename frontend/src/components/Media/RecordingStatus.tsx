import { useTranslation } from "react-i18next";
import { Video, AlertCircle } from "lucide-react";
import { useMediaStore } from "@/store/mediaStore";

/**
 * 录屏状态指示器：显示 Agent 当前是否在录屏。
 *
 * 通过 WS 事件 media_recording_status 实时刷新（store 自动处理）。
 */
export default function RecordingStatus() {
  const { t } = useTranslation();
  const status = useMediaStore((s) => s.recordingStatus);

  const recording = status?.recording ?? false;
  const matchId = status?.match_id ?? "";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-mist-100/[0.06] bg-ink-800/40 px-4 py-3">
      <div
        className={
          recording
            ? "flex h-9 w-9 items-center justify-center rounded-lg bg-flame/15"
            : "flex h-9 w-9 items-center justify-center rounded-lg bg-ink-700/60"
        }
      >
        {recording ? (
          <Video className="h-4 w-4 text-flame" />
        ) : (
          <AlertCircle className="h-4 w-4 text-mist-400" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={
              recording
                ? "h-1.5 w-1.5 rounded-full bg-flame animate-pulse-flame"
                : "h-1.5 w-1.5 rounded-full bg-mist-400"
            }
          />
          <span className="font-mono text-[10px] uppercase tracking-wider text-mist-300">
            {recording
              ? t("media.recording.active")
              : t("media.recording.idle")}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-mist-400">
          {recording && matchId
            ? `${t("media.recording.match")} ${matchId.slice(0, 8)}`
            : t("media.recording.subtitle")}
        </p>
      </div>
    </div>
  );
}
