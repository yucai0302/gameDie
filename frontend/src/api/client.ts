// 后端 HTTP 客户端封装
import type {
  AppConfig,
  DeathResponse,
  GamesStatus,
  Overview,
  Period,
  DeathStats,
  WatchStats,
  DeathEvent,
  MatchListResponse,
  TimelineResponse,
  MatchReviewResponse,
  GearConfig,
  GearConfigUpdate,
  GearRecommendationResponse,
  ProductListResponse,
  PerfLatestResponse,
  PerfMetricItem,
  AgentsListResponse,
  AgentTestResult,
} from "./types";

export const API_BASE = "http://localhost:8000";
export const WS_URL = "ws://localhost:8000/ws";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // 配置
  getConfig: () => request<AppConfig>("/api/config"),
  updateConfig: (patch: Partial<AppConfig>) =>
    request<AppConfig>("/api/config", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  // 游戏状态
  getGamesStatus: () => request<GamesStatus>("/api/games"),

  // 事件
  reportDeath: (event: DeathEvent) =>
    request<DeathResponse>("/api/death", {
      method: "POST",
      body: JSON.stringify(event),
    }),

  // 统计
  getOverview: (period: Period) =>
    request<Overview>(`/api/stats/overview?period=${period}`),
  getDeathStats: (period: Period, game: string = "all") =>
    request<DeathStats>(`/api/stats/deaths?period=${period}&game=${game}`),
  getWatchStats: (period: Period) =>
    request<WatchStats>(`/api/stats/watch?period=${period}`),

  // 测试触发：直接调用 /api/death 模拟一次死亡
  triggerTestDeath: async (game: string): Promise<DeathResponse> => {
    return request<DeathResponse>("/api/death", {
      method: "POST",
      body: JSON.stringify({
        game,
        timestamp: new Date().toISOString(),
        metadata: { source: "test" },
      }),
    });
  },

  // 比赛列表
  getMatches: () => request<MatchListResponse>("/api/matches"),

  // 时间轴（不传 match_id 返回当前比赛）
  getTimeline: (matchId?: string) =>
    request<TimelineResponse>(`/api/timeline${matchId ? `?match_id=${matchId}` : ""}`),

  // AI 复盘（获取缓存的，不存在则现场生成）
  getMatchReview: (matchId: string) =>
    request<MatchReviewResponse>(`/api/matches/${matchId}/review`),

  // AI 复盘（强制重新生成）
  generateMatchReview: (matchId: string) =>
    request<MatchReviewResponse>(`/api/matches/${matchId}/review`, {
      method: "POST",
    }),

  // 外设配置
  getGearConfig: () => request<GearConfig>("/api/gear/config"),
  updateGearConfig: (config: GearConfigUpdate) =>
    request<GearConfig>("/api/gear/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),
  getGearRecommendation: () =>
    request<GearRecommendationResponse>("/api/gear/recommend", {
      method: "POST",
    }),
  getGearProducts: (category?: string) =>
    request<ProductListResponse>(`/api/gear/products${category ? `?category=${category}` : ""}`),

  // 性能监控
  getPerfLatest: () => request<PerfLatestResponse>("/api/gear/perf/latest"),
  getPerfHistory: (metricType: string, limit = 60) =>
    request<PerfMetricItem[]>(`/api/gear/perf/history?metric_type=${metricType}&limit=${limit}`),

  // AI Agent
  getAgents: () => request<AgentsListResponse>("/api/agents"),
  testLLM: () => request<AgentTestResult>("/api/agents/test", { method: "POST" }),
};
