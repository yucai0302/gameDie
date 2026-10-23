import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Gauge,
  Camera,
  Brain,
  Mouse,
  Skull,
  Bot,
  Eye,
  EyeOff,
  Loader2,
  Check,
  X,
  Zap,
} from "lucide-react";
import { useStore } from "@/store/useStore";
import { api } from "@/api/client";
import { useToast } from "@/components/common/Toast";
import Card from "@/components/common/Card";
import { cn } from "@/lib/utils";
import type { AgentInfo } from "@/api/types";

// agent_id -> 图标（未来新增 Agent 在此补一个图标即可，缺省用 Bot）
const AGENT_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  review: Brain,
  gear_advisor: Mouse,
  death_analyst: Skull,
};

export default function AgentSettings() {
  const { t } = useTranslation();
  const config = useStore((s) => s.config);
  const updateConfig = useStore((s) => s.updateConfig);
  const { show } = useToast();
  const agent = config?.agent;

  // 共享 LLM 配置的本地输入态
  const llm = config?.llm;
  const [apiKey, setApiKey] = useState(llm?.api_key ?? "");
  const [model, setModel] = useState(llm?.model ?? "");
  const [baseUrl, setBaseUrl] = useState(llm?.base_url ?? "");
  const [showKey, setShowKey] = useState(false);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const [agents, setAgents] = useState<AgentInfo[]>([]);

  // 配置加载后同步本地输入
  useEffect(() => {
    setApiKey(llm?.api_key ?? "");
    setModel(llm?.model ?? "");
    setBaseUrl(llm?.base_url ?? "");
  }, [llm?.api_key, llm?.model, llm?.base_url]);

  const loadAgents = async () => {
    try {
      const res = await api.getAgents();
      setAgents(res.agents);
    } catch {
      // 后端不可用时不报错
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  // 保存共享 LLM 配置
  const onSaveLLM = async () => {
    setBusy(true);
    try {
      await updateConfig({
        llm: { api_key: apiKey, model, base_url: baseUrl },
      });
      show(t("settings.agentSaved"), "success");
    } catch {
      show(t("toast.saveFailed"), "error");
    } finally {
      setBusy(false);
    }
  };

  // 测试共享 LLM 连通性（先保存再测试）
  const onTestLLM = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await updateConfig({
        llm: { api_key: apiKey, model, base_url: baseUrl },
      });
      const res = await api.testLLM();
      setTestResult({ ok: res.ok, msg: res.message });
    } catch (e) {
      setTestResult({ ok: false, msg: String(e) });
    } finally {
      setTesting(false);
    }
  };

  // 切换单个 Agent 启用状态
  const onToggleAgent = async (agentId: string, enabled: boolean) => {
    try {
      await updateConfig({
        ai_agents: { [agentId]: { enabled } },
      });
      loadAgents();
    } catch {
      show(t("toast.saveFailed"), "error");
    }
  };

  return (
    <Card>
      {/* 共享模型配置 */}
      <div className="mb-4">
        <h3 className="font-display text-base font-semibold text-mist-100">
          {t("settings.aiAgentsTitle")}
        </h3>
        <p className="mt-1 text-xs text-mist-400">
          {t("settings.aiAgentsSubtitle")}
        </p>
      </div>

      <div className="space-y-2.5">
        {/* API Key */}
        <div>
          <label className="mb-1 block text-[11px] text-mist-300">
            {t("settings.agentApiKey")}
            <span className="ml-1 text-flame-soft">*</span>
          </label>
          <div className="flex items-center gap-2 rounded-lg border border-mist-100/[0.08] bg-ink-700/40 px-3 py-1.5 focus-within:border-cyan-neon/40">
            <input
              type={showKey ? "text" : "password"}
              value={apiKey}
              placeholder={t("settings.agentApiKeyPlaceholder")}
              onChange={(e) => setApiKey(e.target.value)}
              className="flex-1 bg-transparent text-sm text-mist-100 placeholder:text-mist-400"
            />
            <button
              onClick={() => setShowKey((v) => !v)}
              className="text-mist-400 hover:text-mist-200"
              type="button"
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* 模型名称 */}
        <div>
          <label className="mb-1 block text-[11px] text-mist-300">
            {t("settings.agentModel")}
            <span className="ml-1 text-flame-soft">*</span>
          </label>
          <div className="flex items-center rounded-lg border border-mist-100/[0.08] bg-ink-700/40 px-3 py-1.5 focus-within:border-cyan-neon/40">
            <input
              type="text"
              value={model}
              placeholder={t("settings.agentModelPlaceholder")}
              onChange={(e) => setModel(e.target.value)}
              className="flex-1 bg-transparent text-sm text-mist-100 placeholder:text-mist-400"
            />
          </div>
        </div>

        {/* Base URL */}
        <div>
          <label className="mb-1 block text-[11px] text-mist-300">
            {t("settings.agentBaseUrl")}
          </label>
          <div className="flex items-center rounded-lg border border-mist-100/[0.08] bg-ink-700/40 px-3 py-1.5 focus-within:border-cyan-neon/40">
            <input
              type="text"
              value={baseUrl}
              placeholder={t("settings.agentBaseUrlPlaceholder")}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="flex-1 bg-transparent text-sm text-mist-100 placeholder:text-mist-400"
            />
          </div>
        </div>
      </div>

      {/* 保存 + 测试 */}
      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={onSaveLLM}
          disabled={busy}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
            busy
              ? "bg-ink-600 text-mist-400"
              : "bg-cyan-neon/20 text-cyan-neon hover:bg-cyan-neon/30",
          )}
        >
          {busy ? t("settings.agentSaving") : t("settings.agentSave")}
        </button>
        <button
          onClick={onTestLLM}
          disabled={testing || !apiKey.trim() || !model.trim()}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
            testing || !apiKey.trim() || !model.trim()
              ? "bg-ink-600 text-mist-400"
              : "bg-flame/15 text-flame hover:bg-flame/25",
          )}
        >
          {testing ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Zap className="h-3.5 w-3.5" />
          )}
          {testing ? t("settings.agentTesting") : t("settings.agentTest")}
        </button>
        {testResult && (
          <span
            className={cn(
              "flex items-center gap-1 text-xs",
              testResult.ok ? "text-lime-neon" : "text-flame-soft",
            )}
          >
            {testResult.ok ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <X className="h-3.5 w-3.5" />
            )}
            <span className="max-w-[220px] truncate" title={testResult.msg}>
              {testResult.ok ? t("settings.agentTestOk") : testResult.msg}
            </span>
          </span>
        )}
      </div>

      {/* Agent 开关列表 */}
      <div className="mt-5 space-y-2">
        <h4 className="font-display text-sm font-semibold text-mist-100">
          {t("settings.agentListTitle")}
        </h4>
        {agents.map((a) => {
          const Icon = AGENT_ICON[a.agent_id] ?? Bot;
          return (
            <div
              key={a.agent_id}
              className="flex items-center justify-between gap-3 rounded-lg border border-mist-100/[0.08] bg-ink-700/40 p-3"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-neon/10 text-cyan-neon">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-sm font-medium text-mist-100">{a.name}</div>
                  <div className="text-xs text-mist-400">{a.description}</div>
                </div>
              </div>
              <button
                onClick={() => onToggleAgent(a.agent_id, !a.enabled)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-2.5 py-1 text-xs font-medium transition-all",
                  a.enabled
                    ? "bg-lime-neon/15 text-lime-neon"
                    : "bg-ink-600 text-mist-400",
                )}
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full",
                    a.enabled ? "bg-lime-neon" : "bg-mist-400",
                  )}
                />
                {a.enabled ? t("settings.enabled") : t("settings.disabled")}
              </button>
            </div>
          );
        })}
        {agents.length === 0 && (
          <p className="text-xs text-mist-400">{t("common.loading")}</p>
        )}
      </div>

      {/* 桌面 Agent 运行参数（只读） */}
      <div className="mt-5 border-t border-mist-100/[0.06] pt-4">
        <div className="mb-3">
          <h3 className="font-display text-base font-semibold text-mist-100">
            {t("settings.agentTitle")}
          </h3>
          <p className="mt-1 text-xs text-mist-400">
            {t("settings.agentSubtitle")}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="flex items-center gap-3 rounded-lg border border-mist-100/[0.06] bg-ink-700/40 p-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-neon/10 text-cyan-neon">
              <Gauge className="h-4 w-4" />
            </span>
            <div>
              <div className="text-xs text-mist-300">
                {t("settings.pollingInterval")}
              </div>
              <div className="data-mono text-sm text-mist-100">
                {agent?.polling_interval ?? 2.0}s
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-mist-100/[0.06] bg-ink-700/40 p-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-flame/10 text-flame">
              <Camera className="h-4 w-4" />
            </span>
            <div>
              <div className="text-xs text-mist-300">{t("settings.screenshot")}</div>
              <div className="text-sm">
                <span
                  className={
                    agent?.screenshot_enabled ? "text-lime-neon" : "text-mist-400"
                  }
                >
                  {agent?.screenshot_enabled
                    ? t("settings.enabled")
                    : t("settings.disabled")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
