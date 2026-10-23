import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Crosshair,
  Skull,
  Swords,
  CircleDot,
  Flag,
  Map as MapIcon,
  Trophy,
  Clock,
} from "lucide-react";
import { api } from "@/api/client";
import { useStore } from "@/store/useStore";
import Card, { CardHeader } from "@/components/common/Card";
import { formatTime, formatRelative, formatMatchName, friendlyMapName, cn } from "@/lib/utils";
import type { MatchInfo, MatchEvent, MatchListResponse } from "@/api/types";

// 事件类型 → 图标 + 颜色映射
const EVENT_META: Record<
  string,
  { icon: typeof Crosshair; color: string; bg: string; border: string; label: string }
> = {
  match_start: { icon: Flag, color: "text-cyan-neon", bg: "bg-cyan-neon/10", border: "border-cyan-neon/30", label: "比赛开始" },
  match_end: { icon: Trophy, color: "text-lime-neon", bg: "bg-lime-neon/10", border: "border-lime-neon/30", label: "比赛结束" },
  round_start: { icon: CircleDot, color: "text-mist-200", bg: "bg-ink-700", border: "border-mist-100/10", label: "回合开始" },
  round_end: { icon: Flag, color: "text-mist-200", bg: "bg-ink-700", border: "border-mist-100/10", label: "回合结束" },
  kill: { icon: Crosshair, color: "text-flame", bg: "bg-flame/10", border: "border-flame/30", label: "击杀" },
  death: { icon: Skull, color: "text-flame-soft", bg: "bg-flame/10", border: "border-flame/30", label: "死亡" },
};

function getEventLabel(type: string, data: Record<string, unknown>): string {
  if (type === "round_end") {
    const win = data.win_team as string;
    if (win === "CT") return "CT 赢";
    if (win === "T") return "T 赢";
    return "回合结束";
  }
  if (type === "kill") {
    const kills = data.kills as number;
    const weapon = data.weapon_name as string | undefined;
    const killLabel = kills >= 5 ? "ACE!" : kills >= 3 ? `${kills}杀` : "击杀";
    return weapon ? `${killLabel} · ${weapon}` : killLabel;
  }
  if (type === "death") {
    const weapon = data.active_weapon_name as string | undefined;
    return weapon ? `死亡 · 持 ${weapon}` : "死亡";
  }
  if (type === "round_start") {
    const money = data.money as number | undefined;
    const weapon = data.active_weapon_name as string | undefined;
    const moneyLabel = money != null ? `起手 $${money}` : "回合开始";
    return weapon ? `${moneyLabel} · ${weapon}` : moneyLabel;
  }
  return EVENT_META[type]?.label ?? type;
}

export default function Timeline() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const matchEvents = useStore((s) => s.matchEvents);
  const matchLive = useStore((s) => s.matchLive);
  const dataVersion = useStore((s) => s.dataVersion);
  const lang = useStore((s) => s.lang);

  const [timeline, setTimeline] = useState<{ match: MatchInfo | null; events: MatchEvent[] }>({
    match: null,
    events: [],
  });
  const [matches, setMatches] = useState<MatchListResponse | null>(null);
  const [selectedMatchId, setSelectedMatchId] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // 拉取比赛列表
  useEffect(() => {
    api.getMatches().then((data) => {
      setMatches(data);
      // 如果没有选中的比赛，选第一个（或当前进行中的）
      if (!selectedMatchId) {
        const id = data.current_match_id || data.matches[0]?.id;
        if (id) setSelectedMatchId(id);
      }
    }).catch(() => {});
  }, [dataVersion]);

  // 拉取时间轴
  useEffect(() => {
    if (!selectedMatchId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api.getTimeline(selectedMatchId).then((data) => {
      setTimeline(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [selectedMatchId, dataVersion]);

  // 合并实时事件（仅当查看当前比赛时）
  const displayEvents = useMemo(() => {
    if (!timeline.events.length && matchLive && !selectedMatchId) {
      return matchEvents;
    }
    // 如果查看的是当前进行中的比赛，合并实时事件
    const currentMatchId = matches?.current_match_id;
    if (currentMatchId && selectedMatchId === currentMatchId) {
      // 用 DB 事件 + 实时事件（去重）；实时事件最新，放在前面（DESC 顺序）
      const ids = new Set(timeline.events.map((e) => e.id));
      const live = matchEvents.filter((e) => !ids.has(e.id));
      return [...live, ...timeline.events];
    }
    return timeline.events;
  }, [timeline.events, matchEvents, matchLive, selectedMatchId, matches]);

  const match = timeline.match;
  const isCurrentMatch = matches?.current_match_id === selectedMatchId;

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1440px] space-y-4">
        {/* 标题区 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-neon/20 to-transparent border border-cyan-neon/30">
              <Clock className="h-4 w-4 text-cyan-neon" />
            </span>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
                {t("timeline.title")}
              </h1>
              <p className="mt-0.5 text-xs text-mist-400">
                {t("timeline.subtitle")}
              </p>
            </div>
          </div>
          {isCurrentMatch && (
            <div className="flex items-center gap-2 rounded-full border border-lime-neon/30 bg-lime-neon/10 px-3 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-lime-neon animate-pulse" />
              <span className="font-mono text-[10px] uppercase tracking-wider text-lime-neon">
                live
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* 左侧：比赛信息 + 时间轴 */}
          <div className="lg:col-span-8 space-y-4">
            {/* 比赛信息卡 */}
            {match ? (
              <Card hover>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-ink-700 border border-mist-100/10">
                      <MapIcon className="h-5 w-5 text-cyan-neon" />
                    </span>
                    <div>
                      <div className="font-display text-lg font-bold text-mist-100">
                        {friendlyMapName(match.map_name) || "未知地图"}
                      </div>
                      <div className="text-xs text-mist-400">
                        {match.mode || "competitive"} · {formatRelative(match.start_time, lang)}
                      </div>
                    </div>
                  </div>
                  {/* 比分 */}
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <div className="font-mono text-2xl font-bold text-cyan-neon">
                        {match.score_ct}
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-mist-400">CT</div>
                    </div>
                    <span className="text-mist-400">:</span>
                    <div className="text-center">
                      <div className="font-mono text-2xl font-bold text-flame">
                        {match.score_t}
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-mist-400">T</div>
                    </div>
                  </div>
                </div>

                {/* KDA */}
                <div className="mt-4 grid grid-cols-4 gap-3">
                  <Stat label="K" value={match.kills} accent="text-lime-neon" />
                  <Stat label="D" value={match.deaths} accent="text-flame" />
                  <Stat label="A" value={match.assists} accent="text-cyan-neon" />
                  <Stat label="MVP" value={match.mvps} accent="text-mist-100" />
                </div>

                {/* 跳转复盘按钮 */}
                {match.status === "ended" && (
                  <button
                    onClick={() => navigate(`/review/${match.id}`)}
                    className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-neon/30 bg-cyan-neon/10 px-4 py-2 text-sm font-medium text-cyan-neon transition-all hover:bg-cyan-neon/20"
                  >
                    <Swords className="h-4 w-4" />
                    {t("timeline.viewReview")}
                  </button>
                )}
              </Card>
            ) : (
              <Card className="flex h-48 items-center justify-center">
                <span className="text-sm text-mist-400">
                  {loading ? t("common.loading") : t("timeline.noMatch")}
                </span>
              </Card>
            )}

            {/* 时间轴 */}
            <Card className="flex flex-col">
              <CardHeader
                title={t("timeline.eventTimeline")}
                subtitle={t("timeline.eventHint")}
                accent="cyan"
              />
              <div className="flex-1 overflow-y-auto pr-1" style={{ maxHeight: 480 }}>
                {loading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="h-14 animate-pulse rounded-lg bg-ink-600/50" />
                    ))}
                  </div>
                ) : displayEvents.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-xs text-mist-400">
                    {t("common.empty")}
                  </div>
                ) : (
                  <ul className="relative space-y-2">
                    {/* 垂直时间线 */}
                    <span className="absolute bottom-0 left-[19px] top-2 w-px bg-gradient-to-b from-cyan-neon/40 via-cyan-neon/10 to-transparent" />
                    {displayEvents.map((event) => {
                      const meta = EVENT_META[event.event_type] ?? EVENT_META.round_start;
                      const Icon = meta.icon;
                      const label = getEventLabel(event.event_type, event.data);
                      const rn = event.round_number;
                      return (
                        <li
                          key={event.id}
                          className="relative flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-ink-700/50"
                        >
                          <span
                            className={cn(
                              "relative z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border",
                              meta.bg,
                              meta.border,
                            )}
                          >
                            <Icon className={cn("h-4 w-4", meta.color)} />
                          </span>
                          <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className={cn("text-sm font-medium", meta.color)}>
                                {label}
                              </span>
                              {rn != null && rn > 0 && (
                                <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] font-mono text-mist-300">
                                  R{rn}
                                </span>
                              )}
                            </div>
                            <span className="data-mono flex-shrink-0 text-xs text-mist-400">
                              {formatTime(event.timestamp, lang, "HH:mm:ss")}
                            </span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </Card>
          </div>

          {/* 右侧：比赛历史 */}
          <div className="lg:col-span-4">
            <Card className="flex flex-col">
              <CardHeader
                title={t("timeline.matchHistory")}
                subtitle={t("timeline.matchHistoryHint")}
                accent="flame"
              />
              <div className="flex-1 overflow-y-auto pr-1" style={{ maxHeight: 560 }}>
                {loading && !matches ? (
                  <div className="space-y-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div key={i} className="h-16 animate-pulse rounded-lg bg-ink-600/50" />
                    ))}
                  </div>
                ) : !matches?.matches.length ? (
                  <div className="flex h-full items-center justify-center text-xs text-mist-400">
                    {t("common.empty")}
                  </div>
                ) : (
                  <ul className="space-y-2">
                    {matches.matches.map((m) => {
                      const active = m.id === selectedMatchId;
                      const live = m.id === matches.current_match_id;
                      return (
                        <li key={m.id}>
                          <button
                            onClick={() => setSelectedMatchId(m.id)}
                            className={cn(
                              "w-full rounded-lg border px-3 py-2.5 text-left transition-all",
                              active
                                ? "border-cyan-neon/40 bg-cyan-neon/10"
                                : "border-mist-100/[0.08] bg-ink-800/40 hover:border-mist-100/[0.15] hover:bg-ink-700/50",
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-mist-100">
                                  {m.map_name || "未知"}
                                </span>
                                {live && (
                                  <span className="rounded bg-lime-neon/20 px-1.5 py-0.5 text-[9px] font-mono uppercase text-lime-neon">
                                    live
                                  </span>
                                )}
                                {m.status === "ended" && (
                                  <span className="rounded bg-mist-400/20 px-1.5 py-0.5 text-[9px] font-mono uppercase text-mist-300">
                                    ended
                                  </span>
                                )}
                              </div>
                              <span className="font-mono text-xs text-mist-400">
                                {formatRelative(m.start_time, lang)}
                              </span>
                            </div>
                            <div className="mt-1.5 flex items-center gap-3 text-xs">
                              <span className="text-mist-300">
                                {m.score_ct} : {m.score_t}
                              </span>
                              <span className="text-mist-400">·</span>
                              <span className="text-lime-neon">{m.kills}K</span>
                              <span className="text-flame">{m.deaths}D</span>
                              {m.mvps > 0 && (
                                <span className="text-mist-100">{m.mvps}MVP</span>
                              )}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent: string }) {
  return (
    <div className="rounded-lg bg-ink-800/60 border border-mist-100/[0.08] px-3 py-2 text-center">
      <div className={cn("font-mono text-xl font-bold", accent)}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-mist-400">{label}</div>
    </div>
  );
}
