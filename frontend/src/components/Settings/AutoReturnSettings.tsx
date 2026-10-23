import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Timer, Zap, Clock } from "lucide-react";
import { useStore } from "@/store/useStore";
import { useToast } from "@/components/common/Toast";
import Card from "@/components/common/Card";
import { cn } from "@/lib/utils";

const PRESETS = [10, 30, 60];

export default function AutoReturnSettings() {
  const { t } = useTranslation();
  const config = useStore((s) => s.config);
  const updateConfig = useStore((s) => s.updateConfig);
  const { show } = useToast();

  const overlay = config?.overlay;
  const enabled = overlay?.auto_return_enabled ?? false;
  const seconds = overlay?.auto_return_seconds ?? 30;
  const onRespawn = overlay?.auto_return_on_respawn ?? true;

  const [custom, setCustom] = useState<string>(
    !PRESETS.includes(seconds) ? String(seconds) : "",
  );

  /** 提交 overlay 配置（始终携带全部字段，避免覆盖） */
  const submit = async (patch: Partial<typeof overlay>) => {
    try {
      await updateConfig({
        overlay: {
          auto_return_enabled: patch.auto_return_enabled ?? enabled,
          auto_return_seconds: patch.auto_return_seconds ?? seconds,
          auto_return_on_respawn: patch.auto_return_on_respawn ?? onRespawn,
        },
      });
      return true;
    } catch {
      show(t("toast.saveFailed"), "error");
      return false;
    }
  };

  const onToggle = async (v: boolean) => {
    if (await submit({ auto_return_enabled: v }))
      show(v ? t("overlay.enabledOn") : t("overlay.enabledOff"), "success");
  };

  const onToggleRespawn = async (v: boolean) => {
    if (await submit({ auto_return_on_respawn: v }))
      show(v ? t("overlay.respawnOn") : t("overlay.respawnOff"), "success");
  };

  const onPickPreset = async (v: number) => {
    setCustom("");
    await submit({ auto_return_seconds: v });
  };

  const onCustomApply = async () => {
    const v = parseInt(custom, 10);
    if (isNaN(v) || v < 1 || v > 600) {
      show(t("overlay.invalidSeconds"), "error");
      return;
    }
    if (await submit({ auto_return_seconds: v }))
      show(t("toast.configSaved"), "success");
  };

  return (
    <Card>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="flex items-center gap-2 font-display text-base font-semibold text-mist-100">
            <Timer className="h-4 w-4 text-flame" />
            {t("overlay.settingsTitle")}
          </h3>
          <p className="mt-1 text-xs text-mist-400">{t("overlay.settingsSubtitle")}</p>
        </div>
        {/* 总开关 */}
        <button
          onClick={() => onToggle(!enabled)}
          className={cn(
            "flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
            enabled
              ? "bg-lime-neon/15 text-lime-neon"
              : "bg-ink-600 text-mist-400",
          )}
        >
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              enabled ? "bg-lime-neon" : "bg-mist-400",
            )}
          />
          {enabled ? t("settings.enabled") : t("settings.disabled")}
        </button>
      </div>

      {/* 复活自动返回开关 */}
      <div
        className={cn(
          "mb-4 rounded-lg border p-3 transition-all",
          onRespawn && enabled
            ? "border-flame/20 bg-flame/[0.06]"
            : "border-mist-100/[0.06] bg-ink-700/30",
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <Zap
              className={cn(
                "mt-0.5 h-4 w-4 shrink-0",
                onRespawn && enabled ? "text-flame" : "text-mist-400",
              )}
            />
            <div>
              <p className="text-sm font-medium text-mist-100">
                {t("overlay.respawnTitle")}
              </p>
              <p className="mt-0.5 text-[11px] text-mist-400">
                {t("overlay.respawnHint")}
              </p>
            </div>
          </div>
          <button
            onClick={() => onToggleRespawn(!onRespawn)}
            disabled={!enabled}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-medium transition-all disabled:opacity-40",
              onRespawn
                ? "bg-flame/15 text-flame"
                : "bg-ink-600 text-mist-400",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                onRespawn ? "bg-flame" : "bg-mist-400",
              )}
            />
            {onRespawn ? t("settings.enabled") : t("settings.disabled")}
          </button>
        </div>
      </div>

      {/* 兜底超时时长 */}
      <div>
        <label className="mb-2 flex items-center gap-1.5 text-[11px] text-mist-300">
          <Clock className="h-3 w-3" />
          {t("overlay.durationLabel")}
        </label>
        <div className="flex flex-wrap items-center gap-2">
          {PRESETS.map((p) => (
            <button
              key={p}
              onClick={() => onPickPreset(p)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
                seconds === p && PRESETS.includes(seconds)
                  ? "bg-cyan-neon/20 text-cyan-neon ring-1 ring-cyan-neon/40"
                  : "bg-ink-700/40 text-mist-300 hover:bg-ink-600",
              )}
            >
              {p}s
            </button>
          ))}
          {/* 自定义输入 */}
          <div className="flex items-center gap-1.5 rounded-lg border border-mist-100/[0.08] bg-ink-700/40 px-2 py-1 focus-within:border-cyan-neon/40">
            <input
              type="number"
              min={1}
              max={600}
              value={custom}
              placeholder={t("overlay.customPlaceholder")}
              onChange={(e) => setCustom(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onCustomApply()}
              className="w-16 bg-transparent text-xs text-mist-100 placeholder:text-mist-400"
            />
            <button
              onClick={onCustomApply}
              className="text-[11px] text-cyan-neon hover:text-cyan-soft"
            >
              {t("settings.apply")}
            </button>
          </div>
        </div>
        <p className="mt-2 text-[10px] text-mist-400">
          {t("overlay.currentDuration", { n: seconds })}
        </p>
      </div>
    </Card>
  );
}
