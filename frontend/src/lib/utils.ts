import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNowStrict } from "date-fns";
import { zhCN, enUS } from "date-fns/locale";

/** Tailwind class 合并 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 把秒数格式化为 "X小时Y分钟" / "Xm Ys" */
export function formatDuration(seconds: number, lang: "zh" | "en" = "zh"): string {
  if (!seconds || seconds < 0) return lang === "zh" ? "0 分钟" : "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (lang === "zh") {
    if (h > 0) return `${h} 小时 ${m} 分钟`;
    if (m > 0) return `${m} 分钟`;
    return `${s} 秒`;
  }
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** ISO 时间格式化为友好显示 */
export function formatTime(
  iso: string | null,
  lang: "zh" | "en" = "zh",
  pattern = "HH:mm:ss",
): string {
  if (!iso) return lang === "zh" ? "暂无" : "None";
  try {
    const d = new Date(iso);
    return format(d, pattern, { locale: lang === "zh" ? zhCN : enUS });
  } catch {
    return iso;
  }
}

/** 相对时间："3 分钟前" / "3 minutes ago" */
export function formatRelative(
  iso: string | null,
  lang: "zh" | "en" = "zh",
): string {
  if (!iso) return lang === "zh" ? "暂无" : "None";
  try {
    return formatDistanceToNowStrict(new Date(iso), {
      addSuffix: true,
      locale: lang === "zh" ? zhCN : enUS,
    });
  } catch {
    return iso;
  }
}

/** 简单 UUID 生成（用于前端临时 ID） */
export function uuid(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** URL 简单校验 */
export function isValidUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/** 游戏名映射（id -> 显示名） */
export const GAME_LABELS: Record<string, { zh: string; en: string; color: string }> = {
  csgo: { zh: "CSGO / CS2", en: "CSGO / CS2", color: "#FF4D2E" },
  pubg: { zh: "PUBG", en: "PUBG", color: "#FFB02E" },
  apex: { zh: "Apex 英雄", en: "Apex Legends", color: "#00E5FF" },
  overwatch: { zh: "守望先锋 2", en: "Overwatch 2", color: "#7CFF6B" },
};

export function gameLabel(id: string, lang: "zh" | "en" = "zh"): string {
  return GAME_LABELS[id]?.[lang] ?? id;
}

export function gameColor(id: string): string {
  return GAME_LABELS[id]?.color ?? "#8B8B9A";
}

/** CS2/CSGO 地图名映射（原始名 → 友好显示名） */
const MAP_NAME_MAP: Record<string, string> = {
  de_dust2: "Dust II",
  de_mirage: "Mirage",
  mirage: "Mirage",
  de_inferno: "Inferno",
  inferno: "Inferno",
  de_nuke: "Nuke",
  nuke: "Nuke",
  de_overpass: "Overpass",
  overpass: "Overpass",
  de_vertigo: "Vertigo",
  vertigo: "Vertigo",
  de_ancient: "Ancient",
  ancient: "Ancient",
  de_anubis: "Anubis",
  anubis: "Anubis",
  de_train: "Train",
  train: "Train",
  de_cbble: "Cobblestone",
  de_cache: "Cache",
  de_shortdust2: "Short Dust II",
  de_shortnuke: "Short Nuke",
  de_shortmirage: "Short Mirage",
  de_shortinferno: "Short Inferno",
  de_shortoverpass: "Short Overpass",
  de_shortvertigo: "Short Vertigo",
  cs_office: "Office",
  cs_italy: "Italy",
  cs_assault: "Assault",
  cs_militia: "Militia",
  ar_baggage: "Baggage",
  ar_shoots: "Shoots",
  ar_dizzy: "Dizzy",
  de_lake: "Lake",
  de_safehouse: "Safehouse",
  de_sugarcane: "Sugarcane",
  de_stmarc: "St. Marc",
  de_bank: "Bank",
};

/** 将原始地图名（如 de_dust2）转为友好显示名（如 Dust II） */
export function friendlyMapName(rawName: string): string {
  if (!rawName) return "";
  const key = rawName.toLowerCase().trim();
  return MAP_NAME_MAP[key] ?? rawName;
}

/** 生成比赛显示名：友好地图名 + 开始时间（MM-DD HH:mm） */
export function formatMatchName(
  mapName: string,
  startTime: string | null,
  lang: "zh" | "en" = "zh",
): string {
  const friendly = friendlyMapName(mapName);
  if (!startTime) return friendly || (lang === "zh" ? "未知" : "Unknown");
  try {
    const timeStr = format(new Date(startTime), "MM-dd HH:mm", {
      locale: lang === "zh" ? zhCN : enUS,
    });
    return friendly ? `${friendly} · ${timeStr}` : timeStr;
  } catch {
    return friendly || startTime;
  }
}
