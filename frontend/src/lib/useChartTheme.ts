import { useEffect, useState } from "react";
import { useStore } from "@/store/useStore";

/**
 * recharts 图表主题色 hook。
 *
 * recharts 的 stroke/contentStyle 等需要 JS 字符串值，无法直接用 Tailwind 类。
 * 这里从 :root 的 CSS 变量读取当前主题颜色，主题切换时自动刷新，
 * 让图表在深色/浅色模式下都正确显示。
 */
export interface ChartTheme {
  /** 网格线 */
  grid: string;
  /** 坐标轴/刻度文字 */
  axis: string;
  /** tooltip 背景 */
  tooltipBg: string;
  /** tooltip 边框（火焰色半透明） */
  tooltipBorder: string;
  /** tooltip 正文文字 */
  tooltipText: string;
  /** tooltip 标签文字 */
  tooltipLabel: string;
}

function read(): ChartTheme {
  const cs = getComputedStyle(document.documentElement);
  // --mist-400: "140 140 155" → "rgb(140 140 155)"
  const rgb = (name: string) => `rgb(${cs.getPropertyValue(name).trim().replace(/\s+/g, " ")})`;
  const rgba = (name: string, a: number) =>
    `rgb(${cs.getPropertyValue(name).trim().replace(/\s+/g, " ")} / ${a})`;
  return {
    grid: rgba("--mist-400", 0.12),
    axis: rgb("--mist-400"),
    tooltipBg: rgba("--ink-700", 0.95),
    tooltipBorder: rgba("--flame", 0.3),
    tooltipText: rgb("--mist-100"),
    tooltipLabel: rgb("--mist-300"),
  };
}

export function useChartTheme(): ChartTheme {
  const theme = useStore((s) => s.theme);
  const [c, setC] = useState<ChartTheme>(() => read());
  useEffect(() => {
    setC(read());
  }, [theme]);
  return c;
}
