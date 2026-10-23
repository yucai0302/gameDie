"""事件上报路由：POST /api/death、POST /api/watch。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter

import database
from models import (
    DeathReportRequest,
    DeathReportResponse,
    WatchReportRequest,
    WatchReportResponse,
)
from state import manager

router = APIRouter()


@router.post("/death", response_model=DeathReportResponse)
async def report_death(payload: DeathReportRequest) -> DeathReportResponse:
    """上报一次死亡事件，并返回 watch_session_id 用于后续上报观看时长。"""
    watch_session_id = str(uuid.uuid4())
    event_id = database.insert_death(
        game=payload.game,
        ts_raw=payload.timestamp,
        metadata=payload.metadata,
        watch_session_id=watch_session_id,
    )

    # 实时推送
    await manager.broadcast_event(
        "death",
        {
            "event_id": event_id,
            "game": payload.game,
            "timestamp": payload.timestamp,
            "metadata": payload.metadata,
            "watch_session_id": watch_session_id,
        },
    )

    return DeathReportResponse(event_id=event_id, watch_session_id=watch_session_id)


@router.post("/watch", response_model=WatchReportResponse)
async def report_watch(payload: WatchReportRequest) -> WatchReportResponse:
    """上报一次观看会话（Agent 关闭浏览器/页面时调用）。"""
    # 通过 session_id 关联死亡记录，补全 game 字段
    death = database.get_death_by_watch_session(payload.session_id)
    game = death["game"] if death else ""

    database.insert_watch_session(
        session_id=payload.session_id,
        game=game,
        start_time=payload.start_time,
        end_time=payload.end_time,
        duration_seconds=payload.duration_seconds,
        url=payload.url,
    )

    await manager.broadcast_event(
        "watch",
        {
            "session_id": payload.session_id,
            "game": game,
            "url": payload.url,
            "start_time": payload.start_time,
            "end_time": payload.end_time,
            "duration_seconds": payload.duration_seconds,
        },
    )

    return WatchReportResponse(ok=True)
