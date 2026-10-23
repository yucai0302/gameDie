import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Radio, Activity, Clock, Target, Film } from "lucide-react";
import { useStore } from "@/store/useStore";
import LanguageSwitch from "./LanguageSwitch";
import ThemeSwitch from "./ThemeSwitch";
import { cn } from "@/lib/utils";

export default function TopNav() {
  const { t } = useTranslation();
  const wsConnected = useStore((s) => s.wsConnected);
  const gamesStatus = useStore((s) => s.gamesStatus);

  const currentGame = gamesStatus?.current_game ?? null;

  const navItem = ({ isActive }: { isActive: boolean }) =>
    cn(
      "relative px-4 py-1.5 text-sm font-medium transition-all",
      isActive
        ? "text-mist-100"
        : "text-mist-300 hover:text-mist-100",
    );

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-mist-100/[0.06] bg-ink-900/70 px-6 backdrop-blur-glass">
      {/* 左侧：LOGO */}
      <div className="flex items-center gap-3">
        <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-ink-700 to-ink-900 shadow-glow">
          <svg viewBox="0 0 32 32" className="h-5 w-5">
            <defs>
              <linearGradient id="navCyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00E5FF"/>
                <stop offset="100%" stopColor="#00B8CC"/>
              </linearGradient>
              <linearGradient id="navFlameGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF4D2E"/>
                <stop offset="100%" stopColor="#CC3D24"/>
              </linearGradient>
              <filter id="navGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <circle cx="16" cy="16" r="10" fill="none" stroke="url(#navCyanGrad)" strokeWidth="1" opacity="0.4"/>
            <circle cx="16" cy="16" r="7" fill="none" stroke="url(#navCyanGrad)" strokeWidth="0.8" opacity="0.3"/>
            <line x1="16" y1="2" x2="16" y2="6" stroke="url(#navCyanGrad)" strokeWidth="1" strokeLinecap="round" filter="url(#navGlow)"/>
            <line x1="16" y1="26" x2="16" y2="30" stroke="url(#navCyanGrad)" strokeWidth="1" strokeLinecap="round" filter="url(#navGlow)"/>
            <line x1="2" y1="16" x2="6" y2="16" stroke="url(#navCyanGrad)" strokeWidth="1" strokeLinecap="round" filter="url(#navGlow)"/>
            <line x1="26" y1="16" x2="30" y2="16" stroke="url(#navCyanGrad)" strokeWidth="1" strokeLinecap="round" filter="url(#navGlow)"/>
            <path d="M16 10 C14 10 12 12 12 15 C12 18 14 20.5 16 21.5 C18 20.5 20 18 20 15 C20 12 18 10 16 10 Z"
                  fill="url(#navFlameGrad)" filter="url(#navGlow)" className="animate-pulse-flame"/>
            <ellipse cx="14.5" cy="14" rx="1" ry="1.3" fill="#0A0A0F"/>
            <ellipse cx="17.5" cy="14" rx="1" ry="1.3" fill="#0A0A0F"/>
            <path d="M14.5 17.5 L14.5 18.5 M16 17.5 L16 18.5 M17.5 17.5 L17.5 18.5" stroke="#0A0A0F" strokeWidth="0.8" strokeLinecap="round"/>
            <circle cx="16" cy="16" r="1" fill="#00E5FF" filter="url(#navGlow)"/>
          </svg>
        </div>
        <div className="flex flex-col leading-none">
          <span className="font-display text-sm font-bold tracking-tight text-mist-100">
            GameDie
          </span>
          <span className="text-[10px] font-mono text-mist-400">
            death · watch · stats
          </span>
        </div>
      </div>

      {/* 中间：页签 */}
      <nav className="flex items-center gap-1 rounded-full border border-mist-100/[0.08] bg-ink-800/60 p-1">
        <NavLink to="/dashboard" className={navItem}>
          {({ isActive }) => (
            <span className="relative flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" />
              {t("nav.dashboard")}
              {isActive && (
                <span className="absolute -bottom-1.5 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-flame shadow-glow" />
              )}
            </span>
          )}
        </NavLink>
        <NavLink to="/timeline" className={navItem}>
          {({ isActive }) => (
            <span className="relative flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              {t("nav.timeline")}
              {isActive && (
                <span className="absolute -bottom-1.5 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-cyan-neon shadow-glow-cyan" />
              )}
            </span>
          )}
        </NavLink>
        <NavLink to="/settings" className={navItem}>
          {({ isActive }) => (
            <span className="relative flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5" />
              {t("nav.settings")}
              {isActive && (
                <span className="absolute -bottom-1.5 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-cyan-neon shadow-glow-cyan" />
              )}
            </span>
          )}
        </NavLink>
        <NavLink to="/gear" className={navItem}>
          {({ isActive }) => (
            <span className="relative flex items-center gap-1.5">
              <Target className="h-3.5 w-3.5" />
              {t("nav.gear")}
              {isActive && (
                <span className="absolute -bottom-1.5 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-cyan-neon shadow-glow-cyan" />
              )}
            </span>
          )}
        </NavLink>
        <NavLink to="/media" className={navItem}>
          {({ isActive }) => (
            <span className="relative flex items-center gap-1.5">
              <Film className="h-3.5 w-3.5" />
              {t("nav.media")}
              {isActive && (
                <span className="absolute -bottom-1.5 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-flame shadow-glow" />
              )}
            </span>
          )}
        </NavLink>
      </nav>

      {/* 右侧：连接状态 + 主题 + 语言 */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-full border border-mist-100/[0.08] bg-ink-800/60 px-3 py-1.5">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              wsConnected ? "bg-lime-neon shadow-[0_0_8px_rgb(var(--lime-neon)/0.6)]" : "bg-mist-400",
            )}
          />
          <span className="font-mono text-[10px] uppercase tracking-wider text-mist-300">
            {wsConnected ? "live" : "offline"}
          </span>
        </div>
        {currentGame && (
          <div className="hidden items-center gap-2 rounded-full border border-flame/30 bg-flame/10 px-3 py-1.5 sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-flame animate-pulse-flame" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-flame-soft">
              {currentGame}
            </span>
          </div>
        )}
        <ThemeSwitch />
        <LanguageSwitch />
      </div>
    </header>
  );
}
