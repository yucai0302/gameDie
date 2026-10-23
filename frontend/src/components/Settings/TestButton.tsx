import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Rocket } from "lucide-react";
import { useStore } from "@/store/useStore";
import { useToast } from "@/components/common/Toast";
import { api } from "@/api/client";
import { isValidUrl, cn } from "@/lib/utils";

export default function TestButton() {
  const { t } = useTranslation();
  const config = useStore((s) => s.config);
  const bumpDataVersion = useStore((s) => s.bumpDataVersion);
  const { show } = useToast();
  const [busy, setBusy] = useState(false);

  const onTest = async () => {
    // 关键：必须在用户手势同步上下文里调用 window.open，否则会被浏览器拦截
    const url = config?.redirect_url ?? "";
    if (!isValidUrl(url)) {
      show(t("settings.invalidUrl"), "error");
      return;
    }

    // 1. 立即同步打开新标签页（用户手势内，不被拦截）
    const win = window.open(url, "_blank", "noopener,noreferrer");
    if (!win) {
      // 浏览器拦截了弹窗，提示用户允许
      show(t("settings.testFail") + " (popup blocked)", "error");
      return;
    }

    // 2. 异步上报一次测试死亡事件，让统计数据也更新
    setBusy(true);
    try {
      await api.triggerTestDeath("csgo");
      bumpDataVersion(); // 触发看板重新拉取统计
      show(t("settings.testOk"), "success");
    } catch {
      // 浏览器已打开，仅统计上报失败
      show(t("settings.testOk"), "success");
    } finally {
      setBusy(false);
    }
  };

  const target = config?.redirect_url ?? "—";

  return (
    <div className="rounded-xl border border-flame/20 bg-gradient-to-br from-flame/[0.08] to-transparent p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-base font-semibold text-mist-100">
            {t("settings.testTitle")}
          </h3>
          <p className="mt-1 text-xs text-mist-300">
            {t("settings.testSubtitle")}
          </p>
          <p className="mt-2 font-mono text-[10px] text-flame-soft">
            {target}
          </p>
        </div>
        <button
          onClick={onTest}
          disabled={busy}
          className={cn(
            "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
            busy
              ? "bg-ink-600 text-mist-400"
              : "bg-gradient-to-br from-flame to-flame-deep text-mist-100 shadow-glow hover:scale-[1.02] hover:shadow-glow",
          )}
        >
          <Rocket className={cn("h-4 w-4", !busy && "animate-pulse-flame")} />
          {busy ? t("settings.testing") : t("settings.testBtn")}
        </button>
      </div>
    </div>
  );
}
