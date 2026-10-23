import { useTranslation } from "react-i18next";
import { Settings as SettingsIcon } from "lucide-react";
import Card from "@/components/common/Card";
import PresetCards from "@/components/Settings/PresetCards";
import CustomUrlInput from "@/components/Settings/CustomUrlInput";
import AgentSettings from "@/components/Settings/AgentSettings";
import TestButton from "@/components/Settings/TestButton";
import AutoReturnSettings from "@/components/Settings/AutoReturnSettings";

export default function Settings() {
  const { t } = useTranslation();

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-[1100px] space-y-4">
        {/* 标题区 */}
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-neon/20 to-transparent border border-cyan-neon/30">
            <SettingsIcon className="h-4 w-4 text-cyan-neon" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-mist-100">
              {t("nav.settings")}
            </h1>
            <p className="mt-0.5 text-xs text-mist-400">redirect · agent · test</p>
          </div>
        </div>

        {/* 重定向配置 */}
        <Card>
          <div className="mb-4">
            <h2 className="font-display text-lg font-semibold text-mist-100">
              {t("settings.title")}
            </h2>
            <p className="mt-1 text-xs text-mist-400">
              {t("settings.subtitle")}
            </p>
          </div>
          <div className="space-y-5">
            <PresetCards />
            <CustomUrlInput />
          </div>
        </Card>

        {/* 自动返回游戏 Overlay */}
        <AutoReturnSettings />

        {/* Agent 参数 */}
        <AgentSettings />

        {/* 测试触发 */}
        <TestButton />
      </div>
    </div>
  );
}
