import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";

export default function LanguageSwitch() {
  const { i18n } = useTranslation();
  const lang = useStore((s) => s.lang);
  const setLang = useStore((s) => s.setLang);

  const toggle = () => {
    const next = lang === "zh" ? "en" : "zh";
    setLang(next);
    i18n.changeLanguage(next);
  };

  return (
    <button
      onClick={toggle}
      className="group flex items-center gap-2 rounded-full border border-mist-100/[0.08] bg-ink-700/60 px-3 py-1.5 text-xs text-mist-200 backdrop-blur-glass transition-all hover:border-cyan-neon/40 hover:text-cyan-neon"
      title={lang === "zh" ? "Switch to English" : "切换为中文"}
    >
      <Globe className="h-3.5 w-3.5" />
      <span className={cn("font-mono", lang === "zh" ? "text-cyan-neon" : "text-mist-300")}>中</span>
      <span className="text-mist-400">/</span>
      <span className={cn("font-mono", lang === "en" ? "text-cyan-neon" : "text-mist-300")}>EN</span>
    </button>
  );
}
