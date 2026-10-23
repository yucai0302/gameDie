"""游戏状态路由：GET /api/games、POST /api/games/status。"""
from __future__ import annotations

from fastapi import APIRouter

from models import GamesListResponse, GamesStatusReport
from state import games_state, manager

router = APIRouter()


@router.get("/games", response_model=GamesListResponse)
def get_games() -> GamesListResponse:
    """返回当前支持的游戏列表与运行状态（来自 Agent 上报的缓存）。"""
    snap = games_state.snapshot()
    return GamesListResponse(**snap)


@router.post("/games/status", response_model=GamesListResponse)
async def report_games_status(payload: GamesStatusReport) -> GamesListResponse:
    """Agent 上报当前游戏运行状态，后端更新内存缓存并广播。"""
    games_state.update(
        games=[g.model_dump() for g in payload.games],
        current_game=payload.current_game,
        current_game_pid=payload.current_game_pid,
    )
    snap = games_state.snapshot()

    await manager.broadcast_event("games_status", snap)

    return GamesListResponse(**snap)
