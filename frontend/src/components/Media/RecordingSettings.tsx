import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Save, RotateCcw, Power, FolderOpen, Trash2 } from "lucide-react";
import { useMediaStore } from "@/store/mediaStore";
import { useToast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { MediaSettings } from "@/api/mediaTypes";

/**
 * 录屏配置面板：总开关 / 回捞时长 / 编码器 / 音频 / 多杀阈值 / AI 生成
 *              / 保存路径 / 自动清理。
 *
 * 独立配置区，放在 Media 页内，不混入现有 Settings 页（功能范畴文档 §八）。
 */
const ENCODER_OPTIONS = [
  { value: "auto", labelKey: "media.settings.encoderAuto" },
  { value: "h264_nvenc", label: "NVIDIA NVENC" },
  { value: "h264_qsv", label: "Intel QSV" },
  { value: "h264_amf", label: "AMD AMF" },
  { value: "libx264", label: "libx264 (软编)" },
];

export default function RecordingSettings() {
  const { t } = useTranslation();
  const { show } = useToast();
  const settings = useMediaStore((s) => s.settings);
  const saveSettings = useMediaStore((s) => s.saveSettings);
  const loadSettings = useMediaStore((s) => s.loadSettings);

  // 本地草稿：保存前不立即下发。settings 异步加载完成后用 useEffect 同步
  const [draft, setDraft] = useState<MediaSettings | null>(null);
  const [saving, setSaving] = useState(false);

  // settings 异步加载完成后同步一次到 draft（避免渲染期 setState）
  useEffect(() => {
    if (settings && draft === null) setDraft(settings);
  }, [settings, draft]);

  const update = <K extends keyof MediaSettings>(
    key: K,
    value: MediaSettings[K],
  ) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      await saveSettings(draft);
      show(t("media.toast.settingsSaved"), "success");
    } catch {
      show(t("media.toast.settingsSaveFailed"), "error");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    await loadSettings();
    setDraft(settings);
  };

  if (!draft) {
    return (
      <div className="glass-card p-5 text-sm text-mist-400">
        {t("common.loading")}
      </div>
    );
  }

  return (
    <div className="glass-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-display text-sm font-medium text-mist-100">
            {t("media.settings.title")}
          </h3>
          <p className="mt-0.5 text-xs text-mist-400">
            {t("media.settings.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-lg border border-mist-100/[0.08] bg-ink-800/60 px-2.5 py-1.5 text-xs text-mist-300 transition-colors hover:text-mist-100"
          >
            <RotateCcw className="h-3 w-3" />
            {t("media.settings.reset")}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-lg bg-flame px-3 py-1.5 text-xs font-medium text-white shadow-glow transition-all hover:bg-flame-deep disabled:opacity-50"
          >
            <Save className="h-3 w-3" />
            {saving ? t("media.settings.saving") : t("media.settings.save")}
          </button>
        </div>
      </div>

      {/* ---- 总开关：独立一行，醒目 ---- */}
      <button
        onClick={() => update("recording_enabled", !draft.recording_enabled)}
        className={cn(
          "mb-4 flex w-full items-center gap-3 rounded-xl border px-4 py-3 transition-all",
          draft.recording_enabled
            ? "border-lime-neon/30 bg-lime-neon/[0.06]"
            : "border-mist-100/[0.08] bg-ink-800/40",
        )}
      >
        <span
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg",
            draft.recording_enabled
              ? "bg-lime-neon/15 text-lime-neon"
              : "bg-ink-700/60 text-mist-400",
          )}
        >
          <Power className="h-4 w-4" />
        </span>
        <div className="flex-1 text-left">
          <div className="text-sm font-medium text-mist-100">
            {t("media.settings.recordingEnabled")}
          </div>
          <div className="text-xs text-mist-400">
            {draft.recording_enabled
              ? t("media.settings.recordingEnabledOn")
              : t("media.settings.recordingEnabledOff")}
          </div>
        </div>
        <span
          className={cn(
            "h-5 w-9 rounded-full p-0.5 transition-colors",
            draft.recording_enabled ? "bg-lime-neon/40" : "bg-ink-700",
          )}
        >
          <span
            className={cn(
              "block h-4 w-4 rounded-full bg-white transition-transform",
              draft.recording_enabled && "translate-x-4",
            )}
          />
        </span>
      </button>

      {/* ---- 录制参数 ---- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label={t("media.settings.rollbackSeconds")}>
          <input
            type="number"
            min={5}
            max={120}
            value={draft.rollback_seconds}
            onChange={(e) =>
              update("rollback_seconds", Number(e.target.value) || 30)
            }
            className="media-input"
          />
          <p className="mt-1 text-[10px] text-mist-400">
            {t("media.settings.rollbackHint")}
          </p>
        </Field>

        <Field label={t("media.settings.minMultikill")}>
          <input
            type="number"
            min={2}
            max={5}
            value={draft.min_multikill}
            onChange={(e) =>
              update("min_multikill", Number(e.target.value) || 3)
            }
            className="media-input"
          />
          <p className="mt-1 text-[10px] text-mist-400">
            {t("media.settings.minMultikillHint")}
          </p>
        </Field>

        <Field label={t("media.settings.encoder")}>
          <select
            value={draft.encoder}
            onChange={(e) => update("encoder", e.target.value)}
            className="media-input cursor-pointer"
          >
            {ENCODER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.labelKey ? t(o.labelKey) : o.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label={t("media.settings.ffmpegPath")}>
          <input
            type="text"
            value={draft.ffmpeg_path}
            onChange={(e) => update("ffmpeg_path", e.target.value)}
            placeholder="ffmpeg"
            className="media-input font-mono"
          />
        </Field>

        <Field label={t("media.settings.captureAudio")}>
          <ToggleButton
            on={draft.capture_audio}
            onClick={() => update("capture_audio", !draft.capture_audio)}
            onLabel={t("common.yes")}
            offLabel={t("common.no")}
            accent="cyan"
          />
        </Field>

        <Field label={t("media.settings.autoGenerateAi")}>
          <ToggleButton
            on={draft.auto_generate_ai}
            onClick={() =>
              update("auto_generate_ai", !draft.auto_generate_ai)
            }
            onLabel={t("common.yes")}
            offLabel={t("common.no")}
            accent="lime"
          />
        </Field>
      </div>

      {/* ---- 存储与清理：分隔区 ---- */}
      <div className="my-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-mist-100/[0.06]" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-mist-400">
          {t("media.settings.storageSection")}
        </span>
        <span className="h-px flex-1 bg-mist-100/[0.06]" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* 保存路径 */}
        <Field label={t("media.settings.clipsSavePath")}>
          <div className="flex items-center gap-2">
            <FolderOpen className="h-3.5 w-3.5 flex-shrink-0 text-mist-400" />
            <input
              type="text"
              value={draft.clips_save_path}
              onChange={(e) => update("clips_save_path", e.target.value)}
              placeholder={t("media.settings.clipsSavePathPlaceholder")}
              className="media-input font-mono"
            />
          </div>
          <p className="mt-1 text-[10px] text-mist-400">
            {t("media.settings.clipsSavePathHint")}
          </p>
        </Field>

        {/* 自动清理天数 */}
        <Field label={t("media.settings.cleanupDays")}>
          <input
            type="number"
            min={1}
            max={90}
            value={draft.cleanup_days}
            onChange={(e) =>
              update("cleanup_days", Number(e.target.value) || 3)
            }
            className="media-input"
          />
          <p className="mt-1 text-[10px] text-mist-400">
            {t("media.settings.cleanupDaysHint")}
          </p>
        </Field>

        {/* 自动清理开关 */}
        <Field label={t("media.settings.autoCleanupEnabled")}>
          <ToggleButton
            on={draft.auto_cleanup_enabled}
            onClick={() =>
              update("auto_cleanup_enabled", !draft.auto_cleanup_enabled)
            }
            onLabel={t("common.yes")}
            offLabel={t("common.no")}
            accent="flame"
          />
          <p className="mt-1 text-[10px] text-mist-400">
            {t("media.settings.autoCleanupHint")}
          </p>
        </Field>
      </div>

      {/* 内联样式：复用现有输入框风格，避免污染 index.css */}
      <style>{`
        .media-input {
          width: 100%;
          background: rgb(var(--ink-800) / 0.6);
          border: 1px solid var(--card-border);
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          color: rgb(var(--mist-100));
          outline: none;
          transition: border-color 0.2s ease;
        }
        .media-input:focus {
          border-color: rgb(var(--cyan-neon) / 0.4);
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-mist-200">
        {label}
      </label>
      {children}
    </div>
  );
}

/** 复用的开关键，accent 控制开启色：cyan / lime / flame */
function ToggleButton({
  on,
  onClick,
  onLabel,
  offLabel,
  accent,
}: {
  on: boolean;
  onClick: () => void;
  onLabel: string;
  offLabel: string;
  accent: "cyan" | "lime" | "flame";
}) {
  const onCls = {
    cyan: "border-cyan-neon/30 bg-cyan-neon/10 text-cyan-soft",
    lime: "border-lime-neon/30 bg-lime-neon/10 text-lime-soft",
    flame: "border-flame/30 bg-flame/10 text-flame-soft",
  }[accent];
  const dotCls = {
    cyan: "bg-cyan-neon",
    lime: "bg-lime-neon",
    flame: "bg-flame",
  }[accent];
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-all",
        on ? onCls : "border-mist-100/[0.08] bg-ink-800/60 text-mist-400",
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", on ? dotCls : "bg-mist-400")} />
      {on ? onLabel : offLabel}
    </button>
  );
}
