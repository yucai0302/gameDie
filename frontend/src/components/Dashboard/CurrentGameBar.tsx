import { useTranslation } from "react-i18next";
import { Flame, Gamepad2, Coffee } from "lucide-react";
import { useStore } from "@/store/useStore";
import { gameLabel } from "@/lib/utils";

/** 当前游戏状态条：顶部贴附条幅，运行时显示游戏名 */
export default function CurrentGameBar() {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);
  const gamesStatus = useStore((s) => s.gamesStatus);
  const current = gamesStatus?.current_game;

  return (
    <div
      className={
        "flex items-center justify-between gap-4 rounded-xl border px-4 py-2.5 " +
        (current
          ? "border-flame/30 bg-flame/[0.06] shadow-glow"
          : "border-mist-100/[0.06] bg-ink-800/40")
      }
    >
      <div className="flex items-center gap-3">
        {current ? (
          <>
            <Flame className="h-4 w-4 text-flame animate-pulse-flame" />
            <span className="font-display text-sm font-semibold text-mist-100">
              {gameLabel(current, lang)}
            </span>
            <span className="rounded-full bg-flame/20 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-flame-soft">
              running
            </span>
          </>
        ) : (
          <>
            <Coffee className="h-4 w-4 text-mist-300" />
            <span className="text-sm text-mist-300">{t("overview.idle")}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-2 text-mist-300">
        <Gamepad2 className="h-3.5 w-3.5" />
        <span className="font-mono text-[10px] uppercase tracking-wider">
          {t("overview.current")}
        </span>
      </div>
    </div>
  );
}
