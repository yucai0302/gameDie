// 全局状态管理
import { create } from "zustand";
import type {
  AppConfig,
  DeathEvent,
  GamesStatus,
  Period,
  MatchEvent,
} from "@/api/types";
import { api } from "@/api/client";

type Lang = "zh" | "en";
type Theme = "dark" | "light";

interface AppState {
  // 偏好
  lang: Lang;
  setLang: (lang: Lang) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;

  // 看板筛选
  period: Period;
  setPeriod: (period: Period) => void;
  gameFilter: string;
  setGameFilter: (game: string) => void;

  // 数据
  config: AppConfig | null;
  loadConfig: () => Promise<void>;
  updateConfig: (patch: Partial<AppConfig>) => Promise<void>;

  gamesStatus: GamesStatus | null;
  loadGamesStatus: () => Promise<void>;

  // 实时事件流（最近 50 条，新事件在头部）
  recentDeaths: (DeathEvent & { id?: string })[];
  pushDeath: (event: DeathEvent & { id?: string }) => void;

  // 连接状态
  wsConnected: boolean;
  setWsConnected: (v: boolean) => void;

  // 数据版本号：每次收到 WS 事件 +1，触发组件重新拉取统计
  dataVersion: number;
  bumpDataVersion: () => void;

  // 比赛事件流（实时时间轴）
  matchEvents: MatchEvent[];
  pushMatchEvent: (event: MatchEvent) => void;
  clearMatchEvents: () => void;

  // 当前是否有进行中的比赛
  matchLive: boolean;
  setMatchLive: (v: boolean) => void;
}

const DEFAULT_CONFIG: AppConfig = {
  redirect_url: "https://www.douyin.com",
  presets: [
    { name: "抖音", url: "https://www.douyin.com", icon: "douyin" },
    { name: "哔哩哔哩", url: "https://www.bilibili.com", icon: "bilibili" },
    { name: "YouTube", url: "https://www.youtube.com", icon: "youtube" },
  ],
  agent: { polling_interval: 2.0, screenshot_enabled: false },
  llm: { api_key: "", model: "", base_url: "" },
  ai_agents: {
    review: { enabled: false },
    gear_advisor: { enabled: false },
    death_analyst: { enabled: false },
  },
  overlay: {
    auto_return_enabled: false,
    auto_return_seconds: 30,
    auto_return_on_respawn: true,
  },
};

export const useStore = create<AppState>((set, get) => ({
  lang: (localStorage.getItem("lang") as Lang) || "zh",
  setLang: (lang) => {
    localStorage.setItem("lang", lang);
    set({ lang });
  },

  theme: (localStorage.getItem("theme") as Theme) || "dark",
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
    set({ theme });
  },
  toggleTheme: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    get().setTheme(next);
  },

  period: "today",
  setPeriod: (period) => set({ period }),
  gameFilter: "all",
  setGameFilter: (gameFilter) => set({ gameFilter }),

  config: null,
  loadConfig: async () => {
    try {
      const cfg = await api.getConfig();
      set({ config: cfg });
    } catch {
      set({ config: DEFAULT_CONFIG });
    }
  },
  updateConfig: async (patch) => {
    const updated = await api.updateConfig(patch);
    set({ config: updated });
  },

  gamesStatus: null,
  loadGamesStatus: async () => {
    try {
      const status = await api.getGamesStatus();
      set({ gamesStatus: status });
    } catch {
      // 后端不可用时不报错
    }
  },

  recentDeaths: [],
  pushDeath: (event) => {
    const cur = get().recentDeaths;
    set({ recentDeaths: [event, ...cur].slice(0, 50) });
  },

  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),

  dataVersion: 0,
  bumpDataVersion: () =>
    set((s) => ({ dataVersion: s.dataVersion + 1 })),

  matchEvents: [],
  pushMatchEvent: (event) => {
    const cur = get().matchEvents;
    set({ matchEvents: [...cur, event].slice(-200) });
  },
  clearMatchEvents: () => set({ matchEvents: [] }),

  matchLive: false,
  setMatchLive: (v) => {
    if (!v) {
      set({ matchLive: false });
    } else {
      set({ matchLive: true, matchEvents: [] });
    }
  },
}));
