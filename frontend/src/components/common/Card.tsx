import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: "flame" | "cyan" | "none";
  hover?: boolean;
}

/** 通用毛玻璃卡片 */
const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, glow = "none", hover = false, children, ...rest }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "glass-card p-5",
          glow === "flame" && "shadow-glow",
          glow === "cyan" && "shadow-glow-cyan",
          hover && "transition-all duration-300 hover:-translate-y-0.5",
          className,
        )}
        {...rest}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";

export default Card;

/** 卡片头部：标题 + 副标题 + 右侧操作 */
export function CardHeader({
  title,
  subtitle,
  right,
  accent = "flame",
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  accent?: "flame" | "cyan" | "lime";
}) {
  const dotColor =
    accent === "flame"
      ? "bg-flame"
      : accent === "cyan"
        ? "bg-cyan-neon"
        : "bg-lime-neon";
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={cn("h-1.5 w-1.5 rounded-full", dotColor)} />
          <h3 className="truncate font-display text-sm font-medium tracking-wide text-mist-100">
            {title}
          </h3>
        </div>
        {subtitle && (
          <p className="mt-1 text-xs text-mist-300">{subtitle}</p>
        )}
      </div>
      {right}
    </div>
  );
}
