import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useTranslation } from "react-i18next";
import { useStore } from "@/store/useStore";
import Card, { CardHeader } from "@/components/common/Card";
import { formatDuration } from "@/lib/utils";
import { useChartTheme } from "@/lib/useChartTheme";
import type { WatchStats } from "@/api/types";

interface Props {
  stats: WatchStats | null;
  loading: boolean;
}

export default function WatchDurationChart({ stats, loading }: Props) {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);
  const ct = useChartTheme();

  const data = useMemo(() => {
    if (!stats) return [];
    return stats.timeline.map((d) => ({
      label: d.date.slice(5),
      seconds: d.seconds,
    }));
  }, [stats]);

  return (
    <Card className="h-full">
      <CardHeader
        title={t("charts.watchDuration")}
        subtitle={t("charts.watchHint")}
        accent="cyan"
        right={
          stats && (
            <span className="data-mono text-xs text-cyan-neon">
              {formatDuration(stats.total_seconds, lang)}
            </span>
          )
        }
      />
      <div className="h-64 w-full">
        {loading ? (
          <div className="h-full w-full animate-pulse rounded-lg bg-ink-600/50" />
        ) : data.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center text-xs text-mist-400">
            {t("common.empty")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="watchGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00E5FF" stopOpacity={0.7} />
                  <stop offset="100%" stopColor="#00E5FF" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={ct.grid} vertical={false} />
              <XAxis
                dataKey="label"
                stroke={ct.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke={ct.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => formatDuration(Number(v), lang)}
                width={60}
              />
              <Tooltip
                cursor={{ stroke: "rgba(0,229,255,0.4)", strokeWidth: 1 }}
                contentStyle={{
                  background: ct.tooltipBg,
                  border: `1px solid ${ct.tooltipBorder}`,
                  borderRadius: 8,
                  fontSize: 12,
                  color: ct.tooltipText,
                }}
                labelStyle={{ color: ct.tooltipLabel }}
                formatter={(v: number) => [
                  formatDuration(Number(v), lang),
                  t("overview.watch"),
                ]}
              />
              <Area
                type="monotone"
                dataKey="seconds"
                stroke="#00E5FF"
                strokeWidth={2}
                fill="url(#watchGrad)"
                activeDot={{ r: 4, fill: "#00E5FF" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
