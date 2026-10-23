import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Mouse,
  Keyboard,
  Volume2,
  Sparkles,
  RefreshCw,
  TrendingUp,
  ShoppingCart,
  ArrowRight,
  Brain,
  Target,
  Wifi,
  Gauge,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { api } from "@/api/client";
import Card, { CardHeader } from "@/components/common/Card";
import { cn } from "@/lib/utils";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import type {
  GearConfig as GearConfigType,
  GearRecommendationResponse,
  ProductItem,
  GearRecommendationItem,
  PerfLatestResponse,
  PerfMetricItem,
} from "@/api/types";

// 段位选项
const RANK_OPTIONS = [
  { value: "silver", label: "白银", en: "Silver" },
  { value: "gold", label: "黄金", en: "Gold" },
  { value: "dmg", label: "大师", en: "DMG" },
  { value: "le", label: "传奇", en: "LE" },
  { value: "global", label: "大地球", en: "Global" },
];

// 打法风格选项
const PLAYSTYLE_OPTIONS = [
  { value: "aggressive", label: "突破手", en: "Aggressive", desc: "快速突破，高灵敏度" },
  { value: "balanced", label: "均衡", en: "Balanced", desc: "攻守兼备" },
  { value: "defensive", label: "防守/狙击", en: "Defensive", desc: "精准瞄头，低灵敏度" },
  { value: "support", label: "辅助", en: "Support", desc: "道具配合" },
];

// 推荐项图标
const REC_ICONS: Record<string, typeof Mouse> = {
  mouse: Mouse,
  refresh: RefreshCw,
  volume: Volume2,
  keyboard: Keyboard,
};

export default function GearConfig() {
  const { t } = useTranslation();
  const [config, setConfig] = useState<GearConfigType | null>(null);
  const [recommendation, setRecommendation] = useState<GearRecommendationResponse | null>(null);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [recommending, setRecommending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>("");
  const [perf, setPerf] = useState<PerfLatestResponse | null>(null);
  const [countdown, setCountdown] = useState(10); // 倒计时秒数
  const [refreshing, setRefreshing] = useState(false); // 刷新中闪烁
  const [perfHistory, setPerfHistory] = useState<Record<string, PerfMetricItem[]>>({
    latency: [],
    fps: [],
    stutter: [],
  });

  // 加载数据
  const loadAll = useCallback(async () => {
    try {
      const [cfg, prods, perfData, hLat, hFps, hStu] = await Promise.all([
        api.getGearConfig(),
        api.getGearProducts(),
        api.getPerfLatest(),
        api.getPerfHistory("latency", 30),
        api.getPerfHistory("fps", 30),
        api.getPerfHistory("stutter", 30),
      ]);
      setConfig(cfg);
      setProducts(prods.products);
      setPerf(perfData);
      setPerfHistory({ latency: hLat, fps: hFps, stutter: hStu });
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  // 刷新性能历史
  const refreshPerfHistory = useCallback(async () => {
    try {
      const [hLat, hFps, hStu] = await Promise.all([
        api.getPerfHistory("latency", 30),
        api.getPerfHistory("fps", 30),
        api.getPerfHistory("stutter", 30),
      ]);
      setPerfHistory({ latency: hLat, fps: hFps, stutter: hStu });
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadAll();
    // 每秒倒计时
    const tickTimer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) return 10;
        return prev - 1;
      });
    }, 1000);
    // 性能数据每 10 秒刷新
    const perfTimer = setInterval(async () => {
      setRefreshing(true);
      try {
        const d = await api.getPerfLatest();
        setPerf(d);
        await refreshPerfHistory();
      } catch {
        // ignore
      } finally {
        setTimeout(() => setRefreshing(false), 800);
      }
    }, 10000);
    return () => {
      clearInterval(tickTimer);
      clearInterval(perfTimer);
    };
  }, [loadAll]);

  // 更新单个字段
  const updateField = async (field: string, value: number | string) => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await api.updateGearConfig({ [field]: value });
      setConfig(updated);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  // AI 推荐
  const handleRecommend = async () => {
    setRecommending(true);
    try {
      const result = await api.getGearRecommendation();
      setRecommendation(result);
      setConfig(result.config);
    } catch {
      // ignore
    } finally {
      setRecommending(false);
    }
  };

  // 筛选商品
  const filteredProducts = activeCategory
    ? products.filter((p) => p.category === activeCategory)
    : products;

  if (loading || !config) {
    return (
      <div className="h-full overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-[1200px] space-y-4">
          <div className="h-10 animate-pulse rounded-lg bg-ink-600/50" />
          <div className="h-48 animate-pulse rounded-xl bg-ink-600/50" />
          <div className="h-32 animate-pulse rounded-xl bg-ink-600/50" />
        </div>
      </div>
    );
  }

  const edpi = Math.round(config.mouse_dpi * config.sensitivity * 10) / 10;

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1200px] space-y-4">
        {/* 标题 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-neon/20 to-transparent border border-cyan-neon/30">
              <Target className="h-4 w-4 text-cyan-neon" />
            </span>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
                {t("gear.title")}
              </h1>
              <p className="mt-0.5 text-xs text-mist-400">
                {t("gear.subtitle")}
              </p>
            </div>
          </div>
          <button
            onClick={handleRecommend}
            disabled={recommending}
            className="flex items-center gap-2 rounded-lg border border-cyan-neon/30 bg-cyan-neon/10 px-4 py-2 text-sm font-medium text-cyan-neon transition-all hover:bg-cyan-neon/20 disabled:opacity-50"
          >
            <Sparkles className={cn("h-4 w-4", recommending && "animate-pulse")} />
            {recommending ? t("gear.analyzing") : t("gear.aiRecommend")}
          </button>
        </div>

        {/* 性能监控（置顶） */}
        <div>
          <div className="mb-3 flex items-center gap-2">
            <Gauge className="h-4 w-4 text-cyan-neon" />
            <h2 className="font-display text-lg font-bold text-mist-100">
              {t("gear.perfMonitor")}
            </h2>
            <span className="text-xs text-mist-400">{t("gear.perfHint")}</span>
            {/* 实时检测指示器 */}
            <div className="ml-auto flex items-center gap-2">
              <span className="flex items-center gap-1.5 rounded-full border border-lime-neon/30 bg-lime-neon/10 px-2.5 py-1 text-xs font-medium text-lime-neon">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-lime-neon opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-lime-neon" />
                </span>
                LIVE
              </span>
              {/* 倒计时进度条 */}
              <span className="flex items-center gap-1.5 text-xs text-mist-400">
                <svg className="h-4 w-4 -rotate-90" viewBox="0 0 16 16">
                  <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-mist-700" />
                  <circle
                    cx="8" cy="8" r="6"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    className="text-cyan-neon transition-all duration-1000 ease-linear"
                    strokeDasharray={`${(countdown / 10) * 37.7} 37.7`}
                  />
                </svg>
                {countdown}s
              </span>
            </div>
          </div>
          <div className={cn("grid grid-cols-1 gap-3 sm:grid-cols-3 transition-opacity", refreshing && "opacity-60")}>
            {/* 网络延迟 */}
            <PerfCard
              icon={Wifi}
              label={t("gear.latency")}
              value={perf?.latency?.value}
              unit="ms"
              accent="cyan"
              thresholds={[50, 100]}
              goodLabel={t("gear.latencyGood")}
              warnLabel={t("gear.latencyWarn")}
              badLabel={t("gear.latencyBad")}
              ts={perf?.latency?.ts}
              historyData={perfHistory.latency}
              detail={perf?.latency?.detail}
            />
            {/* 游戏帧率 */}
            <PerfCard
              icon={Gauge}
              label={t("gear.fps")}
              value={perf?.fps?.value}
              unit="fps"
              accent="lime"
              thresholds={[60, 30]}
              goodLabel={t("gear.fpsGood")}
              warnLabel={t("gear.fpsWarn")}
              badLabel={t("gear.fpsBad")}
              ts={perf?.fps?.ts}
              reverse
              historyData={perfHistory.fps}
            />
            {/* 卡顿率 */}
            <PerfCard
              icon={AlertTriangle}
              label={t("gear.stutter")}
              value={perf?.stutter?.value}
              unit="%"
              accent="flame"
              thresholds={[5, 15]}
              goodLabel={t("gear.stutterGood")}
              warnLabel={t("gear.stutterWarn")}
              badLabel={t("gear.stutterBad")}
              ts={perf?.stutter?.ts}
              historyData={perfHistory.stutter}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          {/* 左侧：配置输入 */}
          <div className="lg:col-span-7 space-y-4">
            {/* 鼠标配置 */}
            <Card hover>
              <CardHeader title={t("gear.mouseConfig")} subtitle={t("gear.mouseHint")} accent="cyan" />
              <div className="mt-4 space-y-4">
                {/* DPI */}
                <ConfigSlider
                  label="DPI"
                  value={config.mouse_dpi}
                  min={100}
                  max={32000}
                  step={50}
                  unit=""
                  onChange={(v) => updateField("mouse_dpi", v)}
                  saving={saving}
                />
                {/* 灵敏度 */}
                <ConfigSlider
                  label={t("gear.sensitivity")}
                  value={config.sensitivity}
                  min={0.1}
                  max={10}
                  step={0.05}
                  unit=""
                  onChange={(v) => updateField("sensitivity", v)}
                  saving={saving}
                />
                {/* 回报率 */}
                <ConfigSelect
                  label={t("gear.pollingRate")}
                  value={config.mouse_polling_rate}
                  options={[
                    { value: 125, label: "125 Hz" },
                    { value: 250, label: "250 Hz" },
                    { value: 500, label: "500 Hz" },
                    { value: 1000, label: "1000 Hz" },
                    { value: 2000, label: "2000 Hz" },
                    { value: 4000, label: "4000 Hz" },
                    { value: 8000, label: "8000 Hz" },
                  ]}
                  onChange={(v) => updateField("mouse_polling_rate", v)}
                />
                {/* eDPI 显示 */}
                <div className="flex items-center justify-between rounded-lg border border-cyan-neon/20 bg-cyan-neon/5 px-4 py-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-cyan-neon" />
                    <span className="text-sm font-medium text-mist-200">eDPI</span>
                  </div>
                  <span className="font-mono text-xl font-bold text-cyan-neon">
                    {edpi}
                  </span>
                </div>
              </div>
            </Card>

            {/* 键盘配置 */}
            <Card hover>
              <CardHeader title={t("gear.keyboardConfig")} subtitle={t("gear.keyboardHint")} accent="flame" />
              <div className="mt-4 space-y-4">
                <ConfigSelect
                  label={t("gear.pollingRate")}
                  value={config.keyboard_polling_rate}
                  options={[
                    { value: 125, label: "125 Hz" },
                    { value: 250, label: "250 Hz" },
                    { value: 500, label: "500 Hz" },
                    { value: 1000, label: "1000 Hz" },
                    { value: 2000, label: "2000 Hz" },
                    { value: 4000, label: "4000 Hz" },
                    { value: 8000, label: "8000 Hz" },
                  ]}
                  onChange={(v) => updateField("keyboard_polling_rate", v)}
                />
                <ConfigSlider
                  label={t("gear.actuation")}
                  value={config.keyboard_actuation}
                  min={0.1}
                  max={4.0}
                  step={0.1}
                  unit="mm"
                  onChange={(v) => updateField("keyboard_actuation", v)}
                  saving={saving}
                />
              </div>
            </Card>

            {/* 音量配置 */}
            <Card hover>
              <CardHeader title={t("gear.volumeConfig")} subtitle={t("gear.volumeHint")} accent="lime" />
              <div className="mt-4">
                <ConfigSlider
                  label={t("gear.volume")}
                  value={config.volume}
                  min={0}
                  max={100}
                  step={1}
                  unit="%"
                  onChange={(v) => updateField("volume", v)}
                  saving={saving}
                />
                <p className="mt-2 text-xs text-mist-400">
                  {t("gear.volumeNote")}
                </p>
              </div>
            </Card>

            {/* 打法 & 段位 */}
            <Card hover>
              <CardHeader title={t("gear.playstyleRank")} subtitle={t("gear.playstyleHint")} accent="cyan" />
              <div className="mt-4 space-y-4">
                {/* 打法风格 */}
                <div>
                  <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-mist-400">
                    {t("gear.playstyle")}
                  </label>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {PLAYSTYLE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => updateField("playstyle", opt.value)}
                        className={cn(
                          "rounded-lg border px-3 py-2 text-center transition-all",
                          config.playstyle === opt.value
                            ? "border-cyan-neon/40 bg-cyan-neon/10"
                            : "border-mist-100/[0.08] bg-ink-800/40 hover:border-mist-100/[0.15]",
                        )}
                      >
                        <div className="text-sm font-medium text-mist-100">{opt.label}</div>
                        <div className="text-[10px] text-mist-400">{opt.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>
                {/* 段位 */}
                <div>
                  <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-mist-400">
                    {t("gear.rank")}
                  </label>
                  <div className="grid grid-cols-5 gap-2">
                    {RANK_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => updateField("rank", opt.value)}
                        className={cn(
                          "rounded-lg border px-2 py-2 text-center transition-all",
                          config.rank === opt.value
                            ? "border-flame/40 bg-flame/10"
                            : "border-mist-100/[0.08] bg-ink-800/40 hover:border-mist-100/[0.15]",
                        )}
                      >
                        <div className="text-xs font-medium text-mist-100">{opt.label}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* 右侧：AI 推荐 */}
          <div className="lg:col-span-5 space-y-4">
            {recommendation ? (
              <>
                {/* eDPI 分析 */}
                <Card className="border border-cyan-neon/20 bg-cyan-neon/5">
                  <div className="flex items-center gap-2">
                    <Brain className="h-4 w-4 text-cyan-neon" />
                    <h3 className="font-display text-sm font-semibold text-cyan-neon">
                      {t("gear.edpiAnalysis")}
                    </h3>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-mist-200">
                    {recommendation.edpi_analysis}
                  </p>
                </Card>

                {/* 推荐项 */}
                <Card>
                  <CardHeader title={t("gear.recommendations")} subtitle={recommendation.summary} accent="cyan" />
                  <div className="mt-3 space-y-3">
                    {recommendation.recommendations.length === 0 ? (
                      <div className="flex items-center justify-center py-8 text-sm text-mist-400">
                        {t("gear.noRecommendation")}
                      </div>
                    ) : (
                      recommendation.recommendations.map((rec, idx) => (
                        <RecommendationCard key={idx} rec={rec} />
                      ))
                    )}
                  </div>
                </Card>
              </>
            ) : (
              <Card className="flex h-full min-h-[300px] items-center justify-center">
                <div className="text-center">
                  <Sparkles className="mx-auto h-8 w-8 text-mist-400/50" />
                  <p className="mt-3 text-sm text-mist-400">{t("gear.recommendHint")}</p>
                  <button
                    onClick={handleRecommend}
                    disabled={recommending}
                    className="mt-4 flex items-center gap-2 rounded-lg border border-cyan-neon/30 bg-cyan-neon/10 px-4 py-2 text-sm font-medium text-cyan-neon transition-all hover:bg-cyan-neon/20 disabled:opacity-50"
                  >
                    <Sparkles className={cn("h-4 w-4", recommending && "animate-pulse")} />
                    {recommending ? t("gear.analyzing") : t("gear.aiRecommend")}
                  </button>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* 推荐商品 */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-flame" />
              <h2 className="font-display text-lg font-bold text-mist-100">
                {t("gear.products")}
              </h2>
            </div>
            {/* 分类筛选 */}
            <div className="flex items-center gap-1.5">
              {[
                { value: "", label: t("gear.all") },
                { value: "mouse", label: t("gear.catMouse") },
                { value: "keyboard", label: t("gear.catKeyboard") },
                { value: "headset", label: t("gear.catHeadset") },
                { value: "mousepad", label: t("gear.catMousepad") },
              ].map((cat) => (
                <button
                  key={cat.value}
                  onClick={() => setActiveCategory(cat.value)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium transition-all",
                    activeCategory === cat.value
                      ? "bg-cyan-neon/20 text-cyan-neon"
                      : "text-mist-400 hover:text-mist-200",
                  )}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {filteredProducts.map((product) => (
              <ProductCard key={product.id} product={product} viewDetailLabel={t("gear.viewDetail")} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- 性能监控卡片 ----
function PerfCard({
  icon: Icon,
  label,
  value,
  unit,
  accent,
  thresholds,
  goodLabel,
  warnLabel,
  badLabel,
  ts,
  reverse = false,
  historyData = [],
  detail,
}: {
  icon: typeof Wifi;
  label: string;
  value: number | undefined;
  unit: string;
  accent: "cyan" | "lime" | "flame";
  thresholds: [number, number];
  goodLabel: string;
  warnLabel: string;
  badLabel: string;
  ts: string | undefined;
  reverse?: boolean;
  historyData?: PerfMetricItem[];
  detail?: Record<string, unknown>;
}) {
  const { t: tPerf } = useTranslation();
  // 判断状态：good / warn / bad
  let status: "good" | "warn" | "bad" = "bad";
  if (value !== undefined) {
    if (reverse) {
      // FPS：越高越好
      if (value >= thresholds[0]) status = "good";
      else if (value >= thresholds[1]) status = "warn";
      else status = "bad";
    } else {
      // 延迟/卡顿：越低越好
      if (value <= thresholds[0]) status = "good";
      else if (value <= thresholds[1]) status = "warn";
      else status = "bad";
    }
  }

  const accentMap = {
    cyan: { text: "text-cyan-neon", bg: "bg-cyan-neon/10", border: "border-cyan-neon/20", stroke: "#22d3ee" },
    lime: { text: "text-lime-neon", bg: "bg-lime-neon/10", border: "border-lime-neon/20", stroke: "#a3e635" },
    flame: { text: "text-flame", bg: "bg-flame/10", border: "border-flame/20", stroke: "#f97316" },
  };
  const statusColor = {
    good: "text-lime-neon",
    warn: "text-yellow-400",
    bad: "text-flame",
  };
  const statusLabel = {
    good: goodLabel,
    warn: warnLabel,
    bad: badLabel,
  };

  const a = accentMap[accent];

  // 加速器信息
  const accelerator = detail?.accelerator as string | undefined;
  const serverIp = detail?.server_ip as string | undefined;

  // 折线图数据
  const chartData = historyData.map((item, idx) => ({ idx, v: item.value }));
  const hasChart = chartData.length >= 2;

  return (
    <div className={cn("rounded-xl border p-4", a.border, a.bg)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg", a.bg, "border", a.border)}>
            <Icon className={cn("h-4 w-4", a.text)} />
          </span>
          <span className="text-sm font-medium text-mist-200">{label}</span>
        </div>
        {value !== undefined && (
          <span className={cn("h-2 w-2 rounded-full", statusColor[status].replace("text-", "bg-"))} />
        )}
      </div>
      <div className="mt-2 flex items-end justify-between">
        <div className="flex items-end gap-1">
          <span className={cn("font-mono text-3xl font-bold", value !== undefined ? statusColor[status] : "text-mist-400")}>
            {value !== undefined ? value : "--"}
          </span>
          <span className="mb-1 text-xs text-mist-400">{unit}</span>
        </div>
        {/* 迷你折线图 */}
        {hasChart && (
          <div className="h-10 w-20">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 1, right: 1, bottom: 1, left: 1 }}>
                <YAxis domain={["dataMin", "dataMax"]} hide />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={a.stroke}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      <div className="mt-1 text-xs text-mist-400">
        {value !== undefined ? statusLabel[status] : tPerf("gear.perfNoData")}
      </div>
      {/* 加速器状态 & 服务器 IP */}
      {(accelerator || serverIp) && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-mist-100/[0.06] pt-2">
          {accelerator && (
            <span className="flex items-center gap-1 rounded-full border border-cyan-neon/30 bg-cyan-neon/10 px-2 py-0.5 text-[10px] font-medium text-cyan-neon">
              <Zap className="h-2.5 w-2.5" />
              {accelerator}
            </span>
          )}
          {serverIp && (
            <span className="flex items-center gap-1 rounded-full border border-mist-100/[0.1] bg-ink-900/50 px-2 py-0.5 text-[10px] font-mono text-mist-400">
              {tPerf("gear.serverIp")}: {serverIp}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ---- 配置滑块组件 ----
function ConfigSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  saving,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
  saving: boolean;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <label className="text-xs font-medium uppercase tracking-wider text-mist-400">
          {label}
        </label>
        <span className={cn("font-mono text-sm font-bold text-mist-100", saving && "opacity-50")}>
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="slider-cyan w-full"
      />
    </div>
  );
}

// ---- 配置下拉选择组件 ----
function ConfigSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: number;
  options: { value: number; label: string }[];
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-mist-400">
        {label}
      </label>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded-md border px-2.5 py-1 text-xs font-medium transition-all",
              value === opt.value
                ? "border-cyan-neon/40 bg-cyan-neon/10 text-cyan-neon"
                : "border-mist-100/[0.08] bg-ink-800/40 text-mist-400 hover:border-mist-100/[0.15]",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---- 推荐卡片组件 ----
function RecommendationCard({ rec }: { rec: GearRecommendationItem }) {
  const Icon = REC_ICONS[rec.icon] ?? Target;
  return (
    <div className="rounded-lg border border-mist-100/[0.08] bg-ink-800/60 p-3">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-neon/10 border border-cyan-neon/20">
          <Icon className="h-3.5 w-3.5 text-cyan-neon" />
        </span>
        <span className="text-sm font-medium text-mist-100">{rec.label}</span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs">
        <span className="rounded bg-flame/10 px-2 py-0.5 font-mono text-flame-soft">
          {rec.current}
        </span>
        <ArrowRight className="h-3 w-3 text-mist-400" />
        <span className="rounded bg-lime-neon/10 px-2 py-0.5 font-mono text-lime-neon">
          {rec.recommended}
        </span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-mist-300">{rec.reason}</p>
    </div>
  );
}

// ---- 商品卡片组件 ----
function ProductCard({ product, viewDetailLabel }: { product: ProductItem; viewDetailLabel: string }) {
  return (
    <div className="group overflow-hidden rounded-xl border border-mist-100/[0.08] bg-ink-800/60 transition-all hover:border-cyan-neon/20 hover:bg-ink-700/50">
      {/* 商品图片 */}
      <div className="relative aspect-square overflow-hidden bg-ink-900">
        <img
          src={product.image}
          alt={product.name}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
        {product.tag && (
          <span className="absolute left-2 top-2 rounded-full bg-flame/90 px-2 py-0.5 text-[10px] font-bold text-mist-100 backdrop-blur">
            {product.tag}
          </span>
        )}
      </div>
      {/* 商品信息 */}
      <div className="p-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-wider text-mist-400">
            {product.brand}
          </span>
          <span className="font-mono text-sm font-bold text-flame-soft">
            {product.price}
          </span>
        </div>
        <h4 className="mt-1 truncate text-sm font-medium text-mist-100">
          {product.name}
        </h4>
        <p className="mt-1 line-clamp-2 text-xs text-mist-400">{product.desc}</p>
        <button className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-mist-100/[0.08] bg-ink-900/50 py-1.5 text-xs font-medium text-mist-300 transition-all hover:border-cyan-neon/30 hover:text-cyan-neon">
          {viewDetailLabel}
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
