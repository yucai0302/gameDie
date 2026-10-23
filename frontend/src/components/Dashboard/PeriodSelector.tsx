import { useTranslation } from "react-i18next";
import { useStore } from "@/store/useStore";
import type { Period } from "@/api/types";
import { cn } from "@/lib/utils";

const PERIODS: Period[] = ["today", "yesterday", "week", "month", "all"];

export default function PeriodSelector() {
  const { t } = useTranslation();
  const period = useStore((s) => s.period);
  const setPeriod = useStore((s) => s.setPeriod);

  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-mist-100/[0.08] bg-ink-800/60 p-1">
      {PERIODS.map((p) => (
        <button
          key={p}
          onClick={() => setPeriod(p)}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-medium transition-all",
            period === p
              ? "bg-flame/20 text-flame-soft shadow-[inset_0_0_0_1px_rgba(255,77,46,0.4)]"
              : "text-mist-300 hover:text-mist-100",
          )}
        >
          {t(`period.${p}`)}
        </button>
      ))}
    </div>
  );
}
