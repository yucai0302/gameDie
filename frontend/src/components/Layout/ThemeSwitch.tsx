import { Sun, Moon } from "lucide-react";
import { useStore } from "@/store/useStore";
import { useTranslation } from "react-i18next";

export default function ThemeSwitch() {
  const theme = useStore((s) => s.theme);
  const toggleTheme = useStore((s) => s.toggleTheme);
  const { t } = useTranslation();

  return (
    <button
      onClick={toggleTheme}
      className="group flex items-center justify-center rounded-full border border-mist-100/[0.08] bg-ink-700/60 p-1.5 text-mist-200 backdrop-blur-glass transition-all hover:border-cyan-neon/40 hover:text-cyan-neon"
      title={theme === "dark" ? t("theme.light") : t("theme.dark")}
    >
      {theme === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </button>
  );
}
