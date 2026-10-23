import { useTranslation } from "react-i18next";
import { useStats } from "@/hooks/useStats";
import CurrentGameBar from "@/components/Dashboard/CurrentGameBar";
import PeriodSelector from "@/components/Dashboard/PeriodSelector";
import OverviewCards from "@/components/Dashboard/OverviewCards";
import DeathTrendChart from "@/components/Dashboard/DeathTrendChart";
import GameDistribution from "@/components/Dashboard/GameDistribution";
import WatchDurationChart from "@/components/Dashboard/WatchDurationChart";
import RecentEvents from "@/components/Dashboard/RecentEvents";

export default function Dashboard() {
  const { t } = useTranslation();
  const { overview, deaths, watch, loading } = useStats();

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1440px] space-y-4">
        {/* 顶部状态条 */}
        <CurrentGameBar />

        {/* 周期选择 + 标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
              {t("nav.dashboard")}
            </h1>
            <p className="mt-0.5 text-xs text-mist-400">
              death · watch · stats
            </p>
          </div>
          <PeriodSelector />
        </div>

        {/* 概览卡片 */}
        <OverviewCards overview={overview} loading={loading} />

        {/* 死亡趋势 + 游戏分布 */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <DeathTrendChart stats={deaths} loading={loading} />
          </div>
          <div className="lg:col-span-4">
            <GameDistribution stats={deaths} loading={loading} />
          </div>
        </div>

        {/* 观看时长 + 最近事件 */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <WatchDurationChart stats={watch} loading={loading} />
          </div>
          <div className="lg:col-span-5">
            <RecentEvents stats={deaths} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
