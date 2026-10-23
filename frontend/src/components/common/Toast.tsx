import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";
interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastCtx {
  show: (message: string, type?: ToastType) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}

let _id = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const show = useCallback((message: string, type: ToastType = "info") => {
    const id = ++_id;
    setItems((cur) => [...cur, { id, type, message }]);
    setTimeout(() => {
      setItems((cur) => cur.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const dismiss = (id: number) =>
    setItems((cur) => cur.filter((t) => t.id !== id));

  return (
    <Ctx.Provider value={{ show }}>
      {children}
      <div className="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "glass-card pointer-events-auto flex min-w-[240px] items-center gap-3 px-4 py-3 animate-slide-in-top",
              t.type === "success" && "border-lime-neon/30",
              t.type === "error" && "border-flame/40",
              t.type === "info" && "border-cyan-neon/30",
            )}
          >
            {t.type === "success" && (
              <CheckCircle2 className="h-4 w-4 text-lime-neon" />
            )}
            {t.type === "error" && (
              <AlertCircle className="h-4 w-4 text-flame" />
            )}
            {t.type === "info" && <Info className="h-4 w-4 text-cyan-neon" />}
            <span className="flex-1 text-sm text-mist-100">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="text-mist-300 transition-colors hover:text-mist-100"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
