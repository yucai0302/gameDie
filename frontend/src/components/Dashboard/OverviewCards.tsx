import { useTranslation } from "react-i18next";
import { Skull, Clock, Gamepad2, Zap } from "lucide-react";
import { useStore } from "@/store/useStore";
import { gameLabel, formatDuration, formatRelative } from "@/lib/utils";
import NumberRoll from "@/components/common/NumberRoll";
import Card from "@/components/common/Card";
import type { Overview } from "@/api/types";
import type { ReactNode } from "react";

interface Props {
  overview: Overview | null;
  loading: boolean;
}

export default function OverviewCards({ overview, loading }: Props) {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* 死亡次数 */}
      <StatCard
        icon={<Skull className="h-4 w-4" />}
        accent="flame"
        label={t("overview.deaths")}
        loading={loading}
        value={
          <NumberRoll
            value={overview?.deaths_total ?? 0}
            className="text-3xl font-bold text-mist-100"
          />
        }
        delta={overview?.deaths_delta}
        deltaGoodIfNegative
      />

      {/* 观看时长 */}
      <StatCard
        icon={<Clock className="h-4 w-4" />}
        accent="cyan"
        label={t("overview.watch")}
        loading={loading}
        value={
          <span className="data-mono text-2xl font-bold text-mist-100">
            {overview ? formatDuration(overview.watch_seconds, lang) : "—"}
          </span>
        }
        delta={overview?.watch_delta}
        deltaGoodIfPositive
        deltaFormat={(s) => formatDuration(s, lang)}
      />

      {/* 当前游戏 */}
      <StatCard
        icon={<Gamepad2 className="h-4 w-4" />}
        accent="lime"
        label={t("overview.current")}
        loading={loading}
        value={
          <span className="font-display text-xl font-bold text-mist-100">
            {overview?.current_game
              ? gameLabel(overview.current_game, lang)
              : t("overview.idle")}
          </span>
        }
      />

      {/* 最近阵亡 */}
      <StatCard
        icon={<Zap className="h-4 w-4" />}
        accent="flame"
        label={t("overview.lastDeath")}
        loading={loading}
        value={
          <span className="font-mono text-sm font-medium text-mist-200">
            {overview?.last_death_at
              ? formatRelative(overview.last_death_at, lang)
              : t("overview.noData")}
          </span>
        }
      />
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  delta,
  deltaGoodIfPositive,
  deltaGoodIfNegative,
  deltaFormat,
  accent,
  loading,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  delta?: number;
  deltaGoodIfPositive?: boolean;
  deltaGoodIfNegative?: boolean;
  deltaFormat?: (n: number) => string;
  accent: "flame" | "cyan" | "lime";
  loading: boolean;
}) {
  const { t } = useTranslation();

  const accentColor =
    accent === "flame"
      ? "text-flame"
      : accent === "cyan"
        ? "text-cyan-neon"
        : "text-lime-neon";

  const accentBg =
    accent === "flame"
      ? "bg-flame/10 border-flame/20"
      : accent === "cyan"
        ? "bg-cyan-neon/10 border-cyan-neon/20"
        : "bg-lime-neon/10 border-lime-neon/20";

  let deltaColor = "";
  if (delta !== undefined && delta !== 0) {
    const isPositive = delta > 0;
    const isGood = deltaGoodIfPositive ? isPositive : deltaGoodIfNegative ? !isPositive : false;
    deltaColor = isGood ? "text-lime-neon" : "text-flame-soft";
  }

  return (
    <Card hover className="overflow-hidden">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`flex h-7 w-7 items-center justify-center rounded-lg border ${accentBg}`}>
            <span className={accentColor}>{icon}</span>
          </span>
          <span className="text-xs font-medium text-mist-300">{label}</span>
        </div>
        {delta !== undefined && delta !== 0 && (
          <span className={`font-mono text-[10px] ${deltaColor}`}>
            {delta > 0 ? "▲" : "▼"} {deltaFormat ? deltaFormat(Math.abs(delta)) : Math.abs(delta)}
            <span className="ml-1 text-mist-400">{t("overview.vsPrev")}</span>
          </span>
        )}
      </div>
      <div className="mt-3 h-9 flex items-center">
        {loading && !value ? (
          <div className="h-6 w-24 animate-pulse rounded bg-ink-600" />
        ) : (
          value
        )}
      </div>
    </Card>
  );
}
