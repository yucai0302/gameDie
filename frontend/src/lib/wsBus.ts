/**
 * Media 模块独立 WebSocket 事件总线。
 *
 * 设计原则（功能范畴文档 §7.1 / §7.2）：
 * - Media 模块前端代码自成闭环，不 import 现有 store / api / 业务组件
 * - WebSocket 连接复用根组件 useWebSocket，但 media_* 事件由本总线独立分发
 * - useWebSocket 只新增一行 dispatch，不改动现有事件处理逻辑
 *
 * 事件类型（与后端 routers/media.py 对齐）：
 * - media_clip_ready        新片段就绪（上传完成 + AI 资产生成完毕）
 * - media_recording_status  录屏状态变化（recording / match_id）
 */
import type { Clip, RecordingStatus } from "@/api/mediaTypes";

type MediaClipReadyListener = (clip: Clip) => void;
type MediaRecordingStatusListener = (status: RecordingStatus) => void;

type Listener = MediaClipReadyListener | MediaRecordingStatusListener;

const listeners: Map<string, Set<Listener>> = new Map();

/** 订阅指定 media 事件类型，返回取消订阅函数。 */
export function onMediaEvent(
  type: "media_clip_ready",
  listener: MediaClipReadyListener,
): () => void;
export function onMediaEvent(
  type: "media_recording_status",
  listener: MediaRecordingStatusListener,
): () => void;
export function onMediaEvent(type: string, listener: Listener): () => void {
  let set = listeners.get(type);
  if (!set) {
    set = new Set();
    listeners.set(type, set);
  }
  set.add(listener);
  return () => {
    const s = listeners.get(type);
    if (s) {
      s.delete(listener);
      if (s.size === 0) listeners.delete(type);
    }
  };
}

/**
 * 派发一条 media_* WebSocket 消息。
 *
 * 由根组件 useWebSocket 在收到 `msg.type` 以 `media_` 开头时调用。
 * 非预期类型静默忽略，绝不抛错（保证不影响现有 WS 流）。
 */
export function dispatchMediaEvent(type: string, data: unknown): void {
  const set = listeners.get(type);
  if (!set || set.size === 0) return;
  for (const fn of set) {
    try {
      (fn as (d: unknown) => void)(data);
    } catch {
      // 单个监听器失败不影响其他监听器
    }
  }
}

/** 判断一条 WS 消息是否属于 media 模块（前缀过滤，供 useWebSocket 使用）。 */
export function isMediaEvent(type: string): boolean {
  return typeof type === "string" && type.startsWith("media_");
}
