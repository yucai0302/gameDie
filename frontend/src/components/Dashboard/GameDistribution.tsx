import { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useTranslation } from "react-i18next";
import { useStore } from "@/store/useStore";
import Card, { CardHeader } from "@/components/common/Card";
import { gameLabel } from "@/lib/utils";
import { useChartTheme } from "@/lib/useChartTheme";
import type { DeathStats } from "@/api/types";

interface Props {
  stats: DeathStats | null;
  loading: boolean;
}

const PALETTE = ["#FF4D2E", "#FFB02E", "#00E5FF", "#7CFF6B", "#B07CFF"];

export default function GameDistribution({ stats, loading }: Props) {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);
  const ct = useChartTheme();

  const data = useMemo(() => {
    if (!stats) return [];
    return Object.entries(stats.by_game)
      .filter(([, v]) => v > 0)
      .map(([k, v], i) => ({
        name: gameLabel(k, lang),
        value: v,
        color: PALETTE[i % PALETTE.length],
      }));
  }, [stats, lang]);

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <Card className="h-full">
      <CardHeader
        title={t("charts.gameDist")}
        subtitle={t("charts.gameDistHint")}
        accent="flame"
      />
      <div className="flex h-64 items-center">
        {loading ? (
          <div className="h-full w-full animate-pulse rounded-lg bg-ink-600/50" />
        ) : data.length === 0 ? (
          <div className="flex h-full w-full items-center justify-center text-xs text-mist-400">
            {t("common.empty")}
          </div>
        ) : (
          <>
            <div className="relative h-full flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="62%"
                    outerRadius="85%"
                    paddingAngle={2}
                    stroke="none"
                  >
                    {data.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: ct.tooltipBg,
                      border: `1px solid ${ct.tooltipBorder}`,
                      borderRadius: 8,
                      fontSize: 12,
                      color: ct.tooltipText,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="data-mono text-2xl font-bold text-mist-100">
                  {total}
                </span>
                <span className="text-[10px] uppercase tracking-wider text-mist-400">
                  {t("overview.deaths")}
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-2 pl-2">
              {data.map((d, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: d.color, boxShadow: `0 0 6px ${d.color}` }}
                  />
                  <span className="flex-1 text-xs text-mist-200">{d.name}</span>
                  <span className="data-mono text-xs text-mist-100">{d.value}</span>
                  <span className="data-mono text-[10px] text-mist-400">
                    {total > 0 ? Math.round((d.value / total) * 100) : 0}%
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
