import { useTranslation } from "react-i18next";
import { Check, Globe, Play, Video } from "lucide-react";
import { useStore } from "@/store/useStore";
import { useToast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { Preset } from "@/api/types";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  douyin: Play,
  bilibili: Video,
  youtube: Play,
  default: Globe,
};

export default function PresetCards() {
  const { t } = useTranslation();
  const config = useStore((s) => s.config);
  const updateConfig = useStore((s) => s.updateConfig);
  const { show } = useToast();

  const presets: Preset[] = config?.presets ?? [];
  const current = config?.redirect_url ?? "";

  const onSelect = async (url: string) => {
    if (url === current) return;
    try {
      await updateConfig({ redirect_url: url });
      show(t("toast.configSaved"), "success");
    } catch {
      show(t("toast.saveFailed"), "error");
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-display text-base font-semibold text-mist-100">
            {t("settings.presets")}
          </h3>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {presets.map((p) => {
          const Icon = ICON_MAP[p.icon] ?? ICON_MAP.default;
          const selected = p.url === current;
          return (
            <button
              key={p.url}
              onClick={() => onSelect(p.url)}
              className={cn(
                "group relative flex flex-col gap-3 overflow-hidden rounded-xl border p-4 text-left transition-all",
                selected
                  ? "border-flame bg-flame/[0.06] shadow-glow"
                  : "border-mist-100/[0.08] bg-ink-700/40 hover:border-mist-100/[0.15] hover:bg-ink-700/70",
              )}
            >
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg",
                    selected
                      ? "bg-flame/20 text-flame-soft"
                      : "bg-ink-600 text-mist-300",
                  )}
                >
                  <Icon className="h-4 w-4" />
                </span>
                {selected && (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-flame text-mist-100">
                    <Check className="h-3 w-3" />
                  </span>
                )}
              </div>
              <div>
                <div className="font-display text-sm font-semibold text-mist-100">
                  {p.name}
                </div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-mist-400">
                  {p.url}
                </div>
              </div>
              {/* 装饰光晕 */}
              {selected && (
                <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-flame/20 blur-2xl" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
