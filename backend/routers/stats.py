"""统计路由：GET /api/stats/deaths、/api/stats/watch、/api/stats/overview。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

import database
from models import (
    DeathsStatsResponse,
    OverviewResponse,
    WatchStatsResponse,
)
from state import games_state

router = APIRouter()

_VALID_PERIODS = {"today", "yesterday", "week", "month", "all"}


def _resolve_period(period: str) -> str:
    return period if period in _VALID_PERIODS else "today"


@router.get("/stats/deaths", response_model=DeathsStatsResponse)
def stats_deaths(
    period: str = Query("today"),
    game: str = Query("all"),
) -> DeathsStatsResponse:
    period = _resolve_period(period)
    data = database.get_death_stats(period=period, game=game)
    return DeathsStatsResponse(**data)


@router.get("/stats/watch", response_model=WatchStatsResponse)
def stats_watch(period: str = Query("today")) -> WatchStatsResponse:
    period = _resolve_period(period)
    data = database.get_watch_stats(period=period)
    return WatchStatsResponse(**data)


@router.get("/stats/overview", response_model=OverviewResponse)
def stats_overview(
    period: str = Query("today"),
) -> OverviewResponse:
    period = _resolve_period(period)
    current_game = games_state.current_game
    data = database.get_overview_stats(period=period, current_game=current_game)
    return OverviewResponse(**data)
