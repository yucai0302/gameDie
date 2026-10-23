"""Pydantic 请求 / 响应模型定义。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------- 配置 ----------------
class Preset(BaseModel):
    name: str
    url: str
    icon: str


class AgentConfig(BaseModel):
    polling_interval: float = 2.0
    screenshot_enabled: bool = False


class LLMConfig(BaseModel):
    """共享 LLM 模型配置（所有 AI Agent 共用一套）。"""
    api_key: str = ""
    model: str = ""
    base_url: str = ""


class AgentToggle(BaseModel):
    """单个 AI Agent 的启用开关。"""
    enabled: bool = False


class OverlayConfig(BaseModel):
    """自动返回游戏配置。"""
    auto_return_enabled: bool = False
    auto_return_seconds: int = 30
    auto_return_on_respawn: bool = True


class AppConfig(BaseModel):
    redirect_url: str = "https://www.douyin.com"
    presets: List[Preset] = Field(default_factory=list)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ai_agents: Dict[str, AgentToggle] = Field(default_factory=dict)
    overlay: OverlayConfig = Field(default_factory=OverlayConfig)


class LLMConfigUpdate(BaseModel):
    """共享 LLM 配置的部分更新。"""
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


class AgentToggleUpdate(BaseModel):
    """单个 Agent 开关的部分更新。"""
    enabled: Optional[bool] = None


class OverlayConfigUpdate(BaseModel):
    """自动返回配置的部分更新。"""
    auto_return_enabled: Optional[bool] = None
    auto_return_seconds: Optional[int] = None
    auto_return_on_respawn: Optional[bool] = None


class ConfigUpdateRequest(BaseModel):
    """允许部分字段更新。"""
    redirect_url: Optional[str] = None
    presets: Optional[List[Preset]] = None
    agent: Optional[AgentConfig] = None
    llm: Optional[LLMConfigUpdate] = None
    ai_agents: Optional[Dict[str, AgentToggleUpdate]] = None
    overlay: Optional[OverlayConfigUpdate] = None


# ---------------- 死亡事件 ----------------
class DeathReportRequest(BaseModel):
    game: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeathReportResponse(BaseModel):
    event_id: str
    watch_session_id: str


# ---------------- 观看时长 ----------------
class WatchReportRequest(BaseModel):
    session_id: str
    start_time: str
    end_time: str
    duration_seconds: int
    url: str = ""


class WatchReportResponse(BaseModel):
    ok: bool = True


# ---------------- 游戏 ----------------
class GameInfo(BaseModel):
    id: str
    name: str
    process_names: List[str]
    running: bool = False


class GamesListResponse(BaseModel):
    games: List[GameInfo]
    current_game: Optional[str] = None
    current_game_pid: Optional[int] = None


class GamesStatusReport(BaseModel):
    games: List[GameInfo]
    current_game: Optional[str] = None
    current_game_pid: Optional[int] = None


# ---------------- 统计 ----------------
class TimelinePoint(BaseModel):
    date: str
    count: int = 0


class HourPoint(BaseModel):
    hour: int
    count: int = 0


class RecentDeath(BaseModel):
    id: str
    game: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeathsStatsResponse(BaseModel):
    period: str
    total: int
    by_game: Dict[str, int]
    timeline: List[TimelinePoint]
    by_hour: List[HourPoint]
    recent: List[RecentDeath]


class WatchByUrlPoint(BaseModel):
    url: str
    name: str
    seconds: int


class WatchTimelinePoint(BaseModel):
    date: str
    seconds: int


class WatchSessionItem(BaseModel):
    session_id: str
    duration_seconds: int
    url: str
    start_time: str
    end_time: str


class WatchStatsResponse(BaseModel):
    period: str
    total_seconds: int
    total_formatted: str
    by_url: List[WatchByUrlPoint]
    timeline: List[WatchTimelinePoint]
    sessions: List[WatchSessionItem]


class OverviewResponse(BaseModel):
    period: str
    deaths_total: int
    deaths_delta: int
    watch_seconds: int
    watch_delta: int
    current_game: Optional[str] = None
    last_death_at: Optional[str] = None


# ---------------- 比赛 / 时间轴 / AI 复盘 ----------------
class MatchEventItem(BaseModel):
    id: str
    match_id: str
    event_type: str
    round_number: Optional[int] = None
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)


class MatchInfo(BaseModel):
    id: str
    game: str = "csgo"
    map_name: str = ""
    mode: str = ""
    status: str = "live"
    start_time: str
    end_time: Optional[str] = None
    score_ct: int = 0
    score_t: int = 0
    rounds_played: int = 0
    player_name: str = ""
    player_steamid: str = ""
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    mvps: int = 0
    score: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MatchListResponse(BaseModel):
    matches: List[MatchInfo]
    current_match_id: Optional[str] = None


class TimelineResponse(BaseModel):
    match: Optional[MatchInfo] = None
    events: List[MatchEventItem] = []


class ReviewSection(BaseModel):
    title: str
    content: str
    tag: str = ""  # mvp / mistake / best_play / death_analysis / weapon_analysis / economy / purchase_advice / summary
    icon: str = ""  # 前端图标 key


class AIReview(BaseModel):
    mvp: str = ""
    biggest_mistake: str = ""
    best_play: str = ""
    death_analysis: str = ""
    economy_analysis: str = ""
    weapon_analysis: str = ""
    purchase_advice: str = ""
    ai_commentary: str = ""
    sections: List[ReviewSection] = Field(default_factory=list)


class MatchReviewResponse(BaseModel):
    match_id: str
    review: AIReview
    generated_at: str


class GenerateReviewResponse(BaseModel):
    match_id: str
    review: AIReview
    generated_at: str


# Agent 上报比赛事件
class MatchEventReport(BaseModel):
    match_id: str
    event_type: str
    timestamp: str
    round_number: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class MatchEventReportResponse(BaseModel):
    event_id: str
    match_id: str


class MatchStartReport(BaseModel):
    map_name: str = ""
    mode: str = ""
    player_name: str = ""
    player_steamid: str = ""


class MatchStartResponse(BaseModel):
    match_id: str


class MatchEndReport(BaseModel):
    match_id: str
    score_ct: int = 0
    score_t: int = 0
    rounds_played: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    mvps: int = 0
    score: int = 0


# ---------------- 外设配置 + AI 推荐 ----------------
class GearConfig(BaseModel):
    game: str = "csgo"
    mouse_dpi: int = 800
    mouse_polling_rate: int = 1000
    sensitivity: float = 2.0
    edpi: float = 1600.0
    keyboard_polling_rate: int = 1000
    keyboard_actuation: float = 2.0
    volume: int = 50
    playstyle: str = "balanced"
    rank: str = "gold"
    updated_at: str = ""


class GearConfigUpdate(BaseModel):
    game: Optional[str] = None
    mouse_dpi: Optional[int] = None
    mouse_polling_rate: Optional[int] = None
    sensitivity: Optional[float] = None
    keyboard_polling_rate: Optional[int] = None
    keyboard_actuation: Optional[float] = None
    volume: Optional[int] = None
    playstyle: Optional[str] = None
    rank: Optional[str] = None


class GearRecommendationItem(BaseModel):
    label: str
    current: str
    recommended: str
    reason: str
    icon: str = ""


class GearRecommendationResponse(BaseModel):
    config: GearConfig
    recommendations: List[GearRecommendationItem]
    summary: str
    edpi_analysis: str


class ProductItem(BaseModel):
    id: str
    name: str
    brand: str
    category: str  # mouse / keyboard / headset / mousepad
    price: str
    tag: str = ""  # 推荐标签：热门 / 性价比 / 职业选手同款
    image: str = ""
    url: str = ""
    desc: str = ""


class ProductListResponse(BaseModel):
    products: List[ProductItem]


class VolumeReport(BaseModel):
    volume: int


# ---------------- 性能监控 ----------------
class PerfMetricReport(BaseModel):
    metric_type: str  # latency / fps / stutter
    value: float
    detail: Dict[str, Any] = Field(default_factory=dict)


class PerfMetricItem(BaseModel):
    id: str
    metric_type: str
    value: float
    detail: Dict[str, Any] = Field(default_factory=dict)
    ts: str


class PerfLatestResponse(BaseModel):
    latency: Optional[Dict[str, Any]] = None
    fps: Optional[Dict[str, Any]] = None
    stutter: Optional[Dict[str, Any]] = None
