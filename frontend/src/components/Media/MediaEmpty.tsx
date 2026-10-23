import { useTranslation } from "react-i18next";
import { Film } from "lucide-react";

/**
 * Media 库空状态：无片段时展示。
 */
export default function MediaEmpty() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-mist-100/[0.06] bg-ink-800/40">
        <Film className="h-7 w-7 text-mist-400" />
      </div>
      <p className="mt-4 font-display text-sm font-medium text-mist-200">
        {t("media.empty.title")}
      </p>
      <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-mist-400">
        {t("media.empty.hint")}
      </p>
    </div>
  );
}
