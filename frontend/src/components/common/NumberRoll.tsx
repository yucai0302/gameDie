import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface NumberRollProps {
  value: number;
  duration?: number;
  className?: string;
  format?: (n: number) => string;
}

/** 数字滚动动画：当 value 变化时从旧值平滑过渡到新值 */
export default function NumberRoll({
  value,
  duration = 600,
  className,
  format,
}: NumberRollProps) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    const to = value;
    if (from === to) return;

    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - t, 3);
      const cur = Math.round(from + (to - from) * eased);
      setDisplay(cur);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = to;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      fromRef.current = to;
    };
  }, [value, duration]);

  const text = format ? format(display) : display.toLocaleString();
  return <span className={cn("data-mono", className)}>{text}</span>;
}
