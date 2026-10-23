import { useTranslation } from "react-i18next";
import { useMediaStore } from "@/store/mediaStore";
import { cn } from "@/lib/utils";

/**
 * 片段筛选器：按比赛 / 事件类型 / 仅保留 过滤。
 *
 * 独立组件，仅依赖 mediaStore，不 import 现有业务组件。
 */
const EVENT_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "", labelKey: "media.filters.allEvents" },
  { value: "ace", labelKey: "media.filters.ace" },
  { value: "multi_kill", labelKey: "media.filters.multiKill" },
  { value: "death", labelKey: "media.filters.death" },
];

export default function ClipFilters() {
  const { t } = useTranslation();
  const matches = useMediaStore((s) => s.matches);
  const filterMatchId = useMediaStore((s) => s.filterMatchId);
  const filterEventType = useMediaStore((s) => s.filterEventType);
  const filterKeptOnly = useMediaStore((s) => s.filterKeptOnly);
  const setFilter = useMediaStore((s) => s.setFilter);

  const chipBase =
    "px-3 py-1.5 rounded-full text-xs font-medium transition-all border";

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* 比赛筛选 */}
      <select
        value={filterMatchId}
        onChange={(e) => setFilter({ filterMatchId: e.target.value })}
        className={cn(
          chipBase,
          "bg-ink-800/60 border-mist-100/[0.08] text-mist-200",
          "focus:border-cyan-neon/40 outline-none cursor-pointer",
        )}
      >
        <option value="">{t("media.filters.allMatches")}</option>
        {matches.map((m) => (
          <option key={m.match_id} value={m.match_id}>
            {m.match_id.slice(0, 8)} · {m.clip_count}
          </option>
        ))}
      </select>

      {/* 事件类型筛选 */}
      <div className="flex items-center gap-1 rounded-full border border-mist-100/[0.08] bg-ink-800/60 p-1">
        {EVENT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilter({ filterEventType: opt.value })}
            className={cn(
              "px-3 py-1 rounded-full text-xs font-medium transition-all",
              filterEventType === opt.value
                ? "bg-flame/15 text-flame-soft"
                : "text-mist-300 hover:text-mist-100",
            )}
          >
            {t(opt.labelKey)}
          </button>
        ))}
      </div>

      {/* 仅保留 */}
      <button
        onClick={() => setFilter({ filterKeptOnly: !filterKeptOnly })}
        className={cn(
          chipBase,
          filterKeptOnly
            ? "bg-lime-neon/15 border-lime-neon/30 text-lime-soft"
            : "bg-ink-800/60 border-mist-100/[0.08] text-mist-300 hover:text-mist-100",
        )}
      >
        {t("media.filters.keptOnly")}
      </button>
    </div>
  );
}
