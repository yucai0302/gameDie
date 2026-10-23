import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import { useTranslation } from "react-i18next";
import { useStore } from "@/store/useStore";
import Card, { CardHeader } from "@/components/common/Card";
import { useChartTheme } from "@/lib/useChartTheme";
import type { DeathStats } from "@/api/types";

interface Props {
  stats: DeathStats | null;
  loading: boolean;
}

export default function DeathTrendChart({ stats, loading }: Props) {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);
  const ct = useChartTheme();

  // timeline 通常按天，by_hour 按小时；为了视觉丰富，timeline 优先
  const data = useMemo(() => {
    if (!stats) return [];
    if (stats.timeline && stats.timeline.length > 1) {
      return stats.timeline.map((d) => ({
        label: d.date.slice(5), // MM-DD
        value: d.count,
      }));
    }
    if (stats.by_hour && stats.by_hour.length > 0) {
      return stats.by_hour.map((d) => ({
        label: `${String(d.hour).padStart(2, "0")}:00`,
        value: d.count,
      }));
    }
    return [];
  }, [stats]);

  return (
    <Card className="h-full">
      <CardHeader
        title={t("charts.deathTrend")}
        subtitle={t("charts.deathTrendHint")}
        accent="flame"
      />
      <div className="h-64 w-full">
        {loading ? (
          <div className="h-full w-full animate-pulse rounded-lg bg-ink-600/50" />
        ) : data.length === 0 ? (
          <Empty />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FF4D2E" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#FF4D2E" stopOpacity={0.2} />
                </linearGradient>
                <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#FFB02E" />
                  <stop offset="100%" stopColor="#FF4D2E" />
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
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(255,77,46,0.08)" }}
                contentStyle={{
                  background: ct.tooltipBg,
                  border: `1px solid ${ct.tooltipBorder}`,
                  borderRadius: 8,
                  fontSize: 12,
                  color: ct.tooltipText,
                }}
                labelStyle={{ color: ct.tooltipLabel }}
                formatter={(v: number) => [`${v} ${lang === "zh" ? "次" : "deaths"}`, ""]}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={18}>
                {data.map((_, i) => (
                  <Cell key={i} fill="url(#barGrad)" />
                ))}
              </Bar>
              <Line
                type="monotone"
                dataKey="value"
                stroke="url(#lineGrad)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#FF4D2E" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function Empty() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full items-center justify-center text-xs text-mist-400">
      {t("common.empty")}
    </div>
  );
}
