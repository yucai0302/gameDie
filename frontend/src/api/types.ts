// 后端 API 类型定义（与 backend/models.py 对齐）

export type Period = "today" | "yesterday" | "week" | "month" | "all";

export interface Preset {
  name: string;
  url: string;
  icon: string;
}

export interface AgentConfig {
  polling_interval: number;
  screenshot_enabled: boolean;
}

export interface LLMConfig {
  api_key: string;
  model: string;
  base_url: string;
}

export interface AgentToggle {
  enabled: boolean;
}

export interface OverlayConfig {
  auto_return_enabled: boolean;
  auto_return_seconds: number;
  auto_return_on_respawn: boolean;
}

export interface AppConfig {
  redirect_url: string;
  presets: Preset[];
  agent: AgentConfig;
  llm: LLMConfig;
  ai_agents: Record<string, AgentToggle>;
  overlay: OverlayConfig;
}

export interface GameInfo {
  id: string;
  name: string;
  process_names: string[];
  running: boolean;
}

export interface GamesStatus {
  games: GameInfo[];
  current_game: string | null;
  current_game_pid: number | null;
}

export interface DeathEvent {
  id?: string;
  game: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface DeathResponse {
  event_id: string;
  watch_session_id: string;
}

export interface WatchReport {
  session_id: string;
  game?: string;
  url: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
}

export interface DeathStats {
  period: Period;
  total: number;
  by_game: Record<string, number>;
  timeline: { date: string; count: number }[];
  by_hour: { hour: number; count: number }[];
  recent: (DeathEvent & { id: string })[];
}

export interface WatchStats {
  period: Period;
  total_seconds: number;
  total_formatted: string;
  by_url: { url: string; name: string; seconds: number }[];
  timeline: { date: string; seconds: number }[];
  sessions: WatchReport[];
}

export interface Overview {
  period: Period;
  deaths_total: number;
  deaths_delta: number;
  watch_seconds: number;
  watch_delta: number;
  current_game: string | null;
  last_death_at: string | null;
}

// WebSocket 消息
export type WSMessage =
  | { type: "hello"; data: { server: string; time: string } }
  | { type: "death"; data: DeathEvent & { id?: string } }
  | { type: "watch"; data: WatchReport }
  | { type: "games_status"; data: GamesStatus }
  | { type: "match_start"; data: { match_id: string; map: string } }
  | { type: "match_end"; data: { match_id: string } }
  | { type: "match_event"; data: MatchEvent };

// ---------------- 比赛 / 时间轴 / AI 复盘 ----------------
export interface MatchEvent {
  id: string;
  match_id: string;
  event_type: "match_start" | "match_end" | "round_start" | "round_end" | "kill" | "death";
  round_number: number | null;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface MatchInfo {
  id: string;
  game: string;
  map_name: string;
  mode: string;
  status: "live" | "ended";
  start_time: string;
  end_time: string | null;
  score_ct: number;
  score_t: number;
  rounds_played: number;
  player_name: string;
  player_steamid: string;
  kills: number;
  deaths: number;
  assists: number;
  mvps: number;
  score: number;
  metadata: Record<string, unknown>;
}

export interface MatchListResponse {
  matches: MatchInfo[];
  current_match_id: string | null;
}

export interface TimelineResponse {
  match: MatchInfo | null;
  events: MatchEvent[];
}

export interface ReviewSection {
  title: string;
  content: string;
  tag: string;
  icon: string;
}

export interface AIReview {
  mvp: string;
  biggest_mistake: string;
  best_play: string;
  death_analysis: string;
  economy_analysis: string;
  weapon_analysis: string;
  purchase_advice: string;
  ai_commentary: string;
  sections: ReviewSection[];
}

export interface MatchReviewResponse {
  match_id: string;
  review: AIReview;
  generated_at: string;
}

// ---------------- 外设配置 + AI 推荐 ----------------
export interface GearConfig {
  game: string;
  mouse_dpi: number;
  mouse_polling_rate: number;
  sensitivity: number;
  edpi: number;
  keyboard_polling_rate: number;
  keyboard_actuation: number;
  volume: number;
  playstyle: string;
  rank: string;
  updated_at: string;
}

export interface GearConfigUpdate {
  game?: string;
  mouse_dpi?: number;
  mouse_polling_rate?: number;
  sensitivity?: number;
  keyboard_polling_rate?: number;
  keyboard_actuation?: number;
  volume?: number;
  playstyle?: string;
  rank?: string;
}

export interface GearRecommendationItem {
  label: string;
  current: string;
  recommended: string;
  reason: string;
  icon: string;
}

export interface GearRecommendationResponse {
  config: GearConfig;
  recommendations: GearRecommendationItem[];
  summary: string;
  edpi_analysis: string;
}

export interface ProductItem {
  id: string;
  name: string;
  brand: string;
  category: string;
  price: string;
  tag: string;
  image: string;
  url: string;
  desc: string;
}

export interface ProductListResponse {
  products: ProductItem[];
}

// ---------------- 性能监控 ----------------
export interface PerfMetricData {
  value: number;
  detail: Record<string, unknown>;
  ts: string;
}

export interface PerfLatestResponse {
  latency: PerfMetricData | null;
  fps: PerfMetricData | null;
  stutter: PerfMetricData | null;
}

export interface PerfMetricItem {
  id: string;
  metric_type: string;
  value: number;
  detail: Record<string, unknown>;
  ts: string;
}

// ---------------- AI Agent ----------------
export interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface AgentsListResponse {
  agents: AgentInfo[];
  llm_configured: boolean;
}

export interface AgentTestResult {
  ok: boolean;
  message: string;
}
