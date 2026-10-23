import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import {
  Crown,
  Star,
  AlertTriangle,
  Skull,
  DollarSign,
  Brain,
  RefreshCw,
  Map as MapIcon,
  TrendingUp,
  ArrowLeft,
  Crosshair,
  ShoppingBag,
} from "lucide-react";
import { api } from "@/api/client";
import { useStore } from "@/store/useStore";
import Card from "@/components/common/Card";
import { formatRelative, friendlyMapName, cn } from "@/lib/utils";
import type { MatchReviewResponse, MatchInfo } from "@/api/types";

// section 图标映射
const SECTION_ICONS: Record<string, typeof Crown> = {
  crown: Crown,
  star: Star,
  alert: AlertTriangle,
  skull: Skull,
  dollar: DollarSign,
  brain: Brain,
  crosshair: Crosshair,
  shopping: ShoppingBag,
};

// section 颜色映射
const SECTION_COLORS: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  mvp: { border: "border-lime-neon/20", bg: "bg-lime-neon/5", text: "text-lime-neon", dot: "bg-lime-neon" },
  best_play: { border: "border-cyan-neon/20", bg: "bg-cyan-neon/5", text: "text-cyan-neon", dot: "bg-cyan-neon" },
  mistake: { border: "border-flame/20", bg: "bg-flame/5", text: "text-flame-soft", dot: "bg-flame" },
  death_analysis: { border: "border-flame/20", bg: "bg-flame/5", text: "text-flame-soft", dot: "bg-flame" },
  weapon_analysis: { border: "border-cyan-neon/20", bg: "bg-cyan-neon/5", text: "text-cyan-neon", dot: "bg-cyan-neon" },
  economy: { border: "border-cyan-neon/20", bg: "bg-cyan-neon/5", text: "text-cyan-neon", dot: "bg-cyan-neon" },
  purchase_advice: { border: "border-lime-neon/20", bg: "bg-lime-neon/5", text: "text-lime-neon", dot: "bg-lime-neon" },
  summary: { border: "border-mist-100/10", bg: "bg-ink-800/60", text: "text-mist-100", dot: "bg-mist-300" },
};

export default function Review() {
  const { t } = useTranslation();
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const lang = useStore((s) => s.lang);

  const [review, setReview] = useState<MatchReviewResponse | null>(null);
  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    if (!matchId) return;
    setLoading(true);
    Promise.all([
      api.getMatchReview(matchId),
      api.getTimeline(matchId),
    ]).then(([reviewData, timelineData]) => {
      setReview(reviewData);
      setMatch(timelineData.match);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [matchId]);

  const handleRegenerate = async () => {
    if (!matchId) return;
    setRegenerating(true);
    try {
      const data = await api.generateMatchReview(matchId);
      setReview(data);
    } catch {
      // ignore
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-[1000px] space-y-4">
          <div className="h-10 animate-pulse rounded-lg bg-ink-600/50" />
          <div className="h-32 animate-pulse rounded-xl bg-ink-600/50" />
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-ink-600/50" />
          ))}
        </div>
      </div>
    );
  }

  if (!review || !match) {
    return (
      <div className="flex h-full items-center justify-center">
        <span className="text-sm text-mist-400">{t("review.noData")}</span>
      </div>
    );
  }

  const sections = review.review.sections || [];
  const kd = match.deaths > 0 ? (match.kills / match.deaths).toFixed(2) : match.kills.toString();

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1000px] space-y-4">
        {/* 标题区 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-mist-100/10 bg-ink-800/60 text-mist-300 transition-all hover:border-cyan-neon/30 hover:text-cyan-neon"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-flame/20 to-transparent border border-flame/30">
              <Brain className="h-4 w-4 text-flame" />
            </span>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
                {t("review.title")}
              </h1>
              <p className="mt-0.5 text-xs text-mist-400">
                {t("review.subtitle")}
              </p>
            </div>
          </div>
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="flex items-center gap-2 rounded-lg border border-mist-100/10 bg-ink-800/60 px-3 py-1.5 text-xs font-medium text-mist-300 transition-all hover:border-cyan-neon/30 hover:text-cyan-neon disabled:opacity-50"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", regenerating && "animate-spin")} />
            {regenerating ? t("review.regenerating") : t("review.regenerate")}
          </button>
        </div>

        {/* 比赛概览 */}
        <Card hover>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-ink-700 border border-mist-100/10">
                <MapIcon className="h-6 w-6 text-cyan-neon" />
              </span>
              <div>
                <div className="font-display text-xl font-bold text-mist-100">
                  {match.map_name || "未知地图"}
                </div>
                <div className="text-xs text-mist-400">
                  {match.player_name || "玩家"} · {formatRelative(match.start_time, lang)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              {/* 比分 */}
              <div className="flex items-center gap-3">
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
          </div>

          {/* KDA + K/D */}
          <div className="mt-4 grid grid-cols-5 gap-3">
            <ReviewStat label="K" value={match.kills} accent="text-lime-neon" />
            <ReviewStat label="D" value={match.deaths} accent="text-flame" />
            <ReviewStat label="A" value={match.assists} accent="text-cyan-neon" />
            <ReviewStat label="MVP" value={match.mvps} accent="text-mist-100" />
            <div className="rounded-lg bg-gradient-to-br from-flame/10 to-transparent border border-flame/20 px-3 py-2 text-center">
              <div className="font-mono text-xl font-bold text-flame-soft">{kd}</div>
              <div className="flex items-center justify-center gap-1 text-[10px] uppercase tracking-wider text-mist-400">
                <TrendingUp className="h-2.5 w-2.5" />
                K/D
              </div>
            </div>
          </div>
        </Card>

        {/* AI 复盘 sections */}
        {sections.map((section, idx) => {
          const Icon = SECTION_ICONS[section.icon] ?? Brain;
          const colors = SECTION_COLORS[section.tag] ?? SECTION_COLORS.summary;
          return (
            <Card key={idx} className={cn("border", colors.border, colors.bg)}>
              <div className="flex items-start gap-3">
                <span className={cn("flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border", colors.border, colors.bg)}>
                  <Icon className={cn("h-4 w-4", colors.text)} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={cn("h-1.5 w-1.5 rounded-full", colors.dot)} />
                    <h3 className="font-display text-sm font-semibold tracking-wide text-mist-100">
                      {section.title}
                    </h3>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-mist-200">
                    {section.content}
                  </p>
                </div>
              </div>
            </Card>
          );
        })}

        {/* 生成时间 */}
        <div className="text-center text-xs text-mist-400">
          {t("review.generatedAt")}: {formatRelative(review.generated_at, lang)}
        </div>
      </div>
    </div>
  );
}

function ReviewStat({ label, value, accent }: { label: string; value: number; accent: string }) {
  return (
    <div className="rounded-lg bg-ink-800/60 border border-mist-100/[0.08] px-3 py-2 text-center">
      <div className={cn("font-mono text-xl font-bold", accent)}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-mist-400">{label}</div>
    </div>
  );
}
