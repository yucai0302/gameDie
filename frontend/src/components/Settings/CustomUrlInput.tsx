import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link2, AlertCircle } from "lucide-react";
import { useStore } from "@/store/useStore";
import { useToast } from "@/components/common/Toast";
import { isValidUrl, cn } from "@/lib/utils";

export default function CustomUrlInput() {
  const { t } = useTranslation();
  const config = useStore((s) => s.config);
  const updateConfig = useStore((s) => s.updateConfig);
  const { show } = useToast();

  const [value, setValue] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const current = config?.redirect_url ?? "";

  const onApply = async () => {
    const url = value.trim();
    if (!isValidUrl(url)) {
      setError(true);
      return;
    }
    setError(false);
    setBusy(true);
    try {
      await updateConfig({ redirect_url: url });
      setValue("");
      show(t("settings.applied"), "success");
    } catch {
      show(t("toast.saveFailed"), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-display text-base font-semibold text-mist-100">
          {t("settings.custom")}
        </h3>
      </div>
      <div
        className={cn(
          "flex items-center gap-2 rounded-xl border bg-ink-700/40 px-3 py-2 transition-all",
          error
            ? "border-flame/60"
            : "border-mist-100/[0.08] focus-within:border-cyan-neon/40",
        )}
      >
        <Link2 className="h-4 w-4 text-mist-300" />
        <input
          type="text"
          value={value}
          placeholder={t("settings.customPlaceholder")}
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(false);
          }}
          onKeyDown={(e) => e.key === "Enter" && onApply()}
          className="flex-1 bg-transparent text-sm text-mist-100 placeholder:text-mist-400"
        />
        <button
          onClick={onApply}
          disabled={busy || !value.trim()}
          className={cn(
            "rounded-lg px-3 py-1 text-xs font-medium transition-all",
            busy || !value.trim()
              ? "bg-ink-600 text-mist-400"
              : "bg-cyan-neon/20 text-cyan-neon hover:bg-cyan-neon/30",
          )}
        >
          {t("settings.apply")}
        </button>
      </div>
      {error && (
        <p className="mt-2 flex items-center gap-1 text-xs text-flame-soft">
          <AlertCircle className="h-3 w-3" />
          {t("settings.invalidUrl")}
        </p>
      )}
      <p className="mt-2 text-xs text-mist-400">
        <span className="text-mist-300">{t("settings.custom")}:</span>{" "}
        <span className="font-mono">{current}</span>
      </p>
    </div>
  );
}
