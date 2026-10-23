"""进程状态缓存 + WebSocket 连接管理。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from database import get_default_games


class ConnectionManager:
    """管理所有 WebSocket 客户端连接，并提供广播能力。"""

    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        # 连接后立即发送 hello 消息
        await ws.send_json({"type": "hello", "data": {"msg": "GameDie WebSocket 已连接"}})

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """向所有在线客户端推送一条消息，断开的连接会被清理。"""
        dead: List[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_event(self, event_type: str, data: Any) -> None:
        await self.broadcast({"type": event_type, "data": data})


# 全局单例
manager = ConnectionManager()


class GamesState:
    """缓存 Agent 上报的游戏运行状态。未上报前返回默认列表（全部 running=False）。"""

    def __init__(self) -> None:
        self.games: List[dict] = get_default_games()
        for g in self.games:
            g["running"] = False
        self.current_game: Optional[str] = None
        self.current_game_pid: Optional[int] = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "games": [dict(g) for g in self.games],
            "current_game": self.current_game,
            "current_game_pid": self.current_game_pid,
        }

    def update(
        self,
        games: List[dict],
        current_game: Optional[str],
        current_game_pid: Optional[int] = None,
    ) -> None:
        self.games = [dict(g) for g in games]
        self.current_game = current_game
        self.current_game_pid = current_game_pid


games_state = GamesState()
