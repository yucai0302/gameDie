import { useEffect, useRef } from "react";
import { WS_URL } from "@/api/client";
import { useStore } from "@/store/useStore";
import type { WSMessage } from "@/api/types";
import { dispatchMediaEvent, isMediaEvent } from "@/lib/wsBus";

/**
 * WebSocket 连接 hook：自动重连，将消息分发给 store。
 * 在根组件挂载一次即可。
 */
export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const closedManually = useRef(false);

  const setWsConnected = useStore((s) => s.setWsConnected);
  const pushDeath = useStore((s) => s.pushDeath);
  const bumpDataVersion = useStore((s) => s.bumpDataVersion);
  const loadGamesStatus = useStore((s) => s.loadGamesStatus);
  const pushMatchEvent = useStore((s) => s.pushMatchEvent);
  const setMatchLive = useStore((s) => s.setMatchLive);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as WSMessage;
          // Media 模块事件独立分发（独立前缀 media_*，不进入现有 switch）
          if (isMediaEvent(msg.type)) {
            dispatchMediaEvent(msg.type, (msg as { data: unknown }).data);
            return;
          }
          switch (msg.type) {
            case "death":
              pushDeath(msg.data);
              bumpDataVersion();
              break;
            case "watch":
            case "games_status":
              bumpDataVersion();
              if (msg.type === "games_status") {
                loadGamesStatus();
              }
              break;
            case "match_start":
              setMatchLive(true);
              bumpDataVersion();
              break;
            case "match_end":
              setMatchLive(false);
              bumpDataVersion();
              break;
            case "match_event":
              pushMatchEvent(msg.data);
              break;
            case "hello":
              break;
          }
        } catch {
          // 忽略非 JSON 消息
        }
      };

      ws.onerror = () => {
        setWsConnected(false);
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (!closedManually.current) {
          reconnectTimer.current = window.setTimeout(connect, 5000);
        }
      };
    };

    connect();

    return () => {
      closedManually.current = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      wsRef.current?.close();
    };
  }, [setWsConnected, pushDeath, bumpDataVersion, loadGamesStatus, pushMatchEvent, setMatchLive]);
}
