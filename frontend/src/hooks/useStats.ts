import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { useStore } from "@/store/useStore";
import type { Overview, DeathStats, WatchStats } from "@/api/types";

interface StatsBundle {
  overview: Overview | null;
  deaths: DeathStats | null;
  watch: WatchStats | null;
  loading: boolean;
  error: Error | null;
  reload: () => void;
}

/**
 * 统计数据 hook：响应 period / gameFilter / dataVersion 变化重新拉取。
 */
export function useStats(): StatsBundle {
  const period = useStore((s) => s.period);
  const gameFilter = useStore((s) => s.gameFilter);
  const dataVersion = useStore((s) => s.dataVersion);

  const [overview, setOverview] = useState<Overview | null>(null);
  const [deaths, setDeaths] = useState<DeathStats | null>(null);
  const [watch, setWatch] = useState<WatchStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, d, w] = await Promise.all([
        api.getOverview(period),
        api.getDeathStats(period, gameFilter),
        api.getWatchStats(period),
      ]);
      setOverview(ov);
      setDeaths(d);
      setWatch(w);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
    // 监听 period / gameFilter / dataVersion 变化
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, gameFilter, dataVersion]);

  return { overview, deaths, watch, loading, error, reload };
}
