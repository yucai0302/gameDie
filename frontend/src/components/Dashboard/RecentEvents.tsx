import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Skull } from "lucide-react";
import { useStore } from "@/store/useStore";
import Card, { CardHeader } from "@/components/common/Card";
import { gameLabel, formatTime, cn } from "@/lib/utils";
import type { DeathStats } from "@/api/types";

interface Props {
  stats: DeathStats | null;
  loading: boolean;
}

interface EventRow {
  id: string;
  game: string;
  timestamp: string;
  isNew?: boolean;
}

export default function RecentEvents({ stats, loading }: Props) {
  const { t } = useTranslation();
  const lang = useStore((s) => s.lang);
  const recentDeaths = useStore((s) => s.recentDeaths);
  const [flashIds, setFlashIds] = useState<Set<string>>(new Set());
  const seenRef = useRef<Set<string>>(new Set());

  // 合并：实时事件流 + stats.recent（去重，按时间倒序）
  const rows: EventRow[] = useMemo(() => {
    const map = new Map<string, EventRow>();
    // 历史事件
    stats?.recent?.forEach((e) => {
      const id = (e as { id?: string }).id ?? `${e.game}-${e.timestamp}`;
      if (!map.has(id)) map.set(id, { id, game: e.game, timestamp: e.timestamp });
    });
    // 实时事件（覆盖同 id）
    recentDeaths.forEach((e) => {
      const id = (e as { id?: string }).id ?? `${e.game}-${e.timestamp}`;
      map.set(id, { id, game: e.game, timestamp: e.timestamp, isNew: true });
    });
    return Array.from(map.values()).sort(
      (a, b) => +new Date(b.timestamp) - +new Date(a.timestamp),
    );
  }, [stats, recentDeaths]);

  // 检测新事件，加入 flash 集合 2 秒后移除
  useEffect(() => {
    rows.forEach((r) => {
      if (r.isNew && !seenRef.current.has(r.id)) {
        seenRef.current.add(r.id);
        setFlashIds((s) => new Set(s).add(r.id));
        setTimeout(() => {
          setFlashIds((s) => {
            const next = new Set(s);
            next.delete(r.id);
            return next;
          });
        }, 2200);
      }
    });
  }, [rows]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader
        title={t("charts.recentEvents")}
        subtitle={t("charts.recentHint")}
        accent="flame"
      />
      <div className="flex-1 overflow-y-auto pr-1" style={{ maxHeight: 320 }}>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-ink-600/50" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-mist-400">
            {t("common.empty")}
          </div>
        ) : (
          <ul className="relative space-y-1.5">
            <span className="absolute bottom-0 left-[15px] top-2 w-px bg-gradient-to-b from-flame/40 via-flame/10 to-transparent" />
            {rows.map((r) => {
              const flash = flashIds.has(r.id);
              return (
                <li
                  key={r.id}
                  className={cn(
                    "relative flex items-center gap-3 rounded-lg px-2 py-2 transition-colors",
                    flash && "animate-flash-row",
                  )}
                >
                  <span
                    className={cn(
                      "relative z-10 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border",
                      flash
                        ? "border-flame bg-flame/30 shadow-glow"
                        : "border-flame/30 bg-ink-900",
                    )}
                  >
                    <Skull
                      className={cn(
                        "h-3 w-3",
                        flash ? "text-flame-soft" : "text-flame/70",
                      )}
                    />
                  </span>
                  <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
                    <span className="truncate text-sm text-mist-100">
                      {gameLabel(r.game, lang)}
                    </span>
                    <span className="data-mono flex-shrink-0 text-xs text-mist-300">
                      {formatTime(r.timestamp, lang)}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Card>
  );
}
