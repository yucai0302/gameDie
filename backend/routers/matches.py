"""比赛 / 时间轴 / AI 复盘路由。"""
from __future__ import annotations

from fastapi import APIRouter

import database
from models import (
    MatchEndReport,
    MatchEventItem,
    MatchEventReport,
    MatchEventReportResponse,
    MatchInfo,
    MatchListResponse,
    MatchStartReport,
    MatchStartResponse,
    MatchReviewResponse,
    GenerateReviewResponse,
    TimelineResponse,
)
from state import manager

router = APIRouter()


@router.post("/match/start", response_model=MatchStartResponse)
async def match_start(payload: MatchStartReport) -> MatchStartResponse:
    """Agent 上报比赛开始，后端创建比赛记录。"""
    match_id = database.insert_match(
        map_name=payload.map_name,
        mode=payload.mode,
        player_name=payload.player_name,
        player_steamid=payload.player_steamid,
    )
    await manager.broadcast_event("match_start", {"match_id": match_id, "map": payload.map_name})
    return MatchStartResponse(match_id=match_id)


@router.post("/match/end")
async def match_end(payload: MatchEndReport) -> dict:
    """Agent 上报比赛结束。"""
    database.update_match(
        payload.match_id,
        status="ended",
        end_time=database.now_iso(),
        score_ct=payload.score_ct,
        score_t=payload.score_t,
        rounds_played=payload.rounds_played,
        kills=payload.kills,
        deaths=payload.deaths,
        assists=payload.assists,
        mvps=payload.mvps,
        score=payload.score,
    )
    await manager.broadcast_event("match_end", {"match_id": payload.match_id})
    return {"ok": True, "match_id": payload.match_id}


@router.post("/match/event", response_model=MatchEventReportResponse)
async def match_event(payload: MatchEventReport) -> MatchEventReportResponse:
    """Agent 上报比赛事件（回合、击杀、死亡等）。"""
    event_id = database.insert_match_event(
        match_id=payload.match_id,
        event_type=payload.event_type,
        timestamp=payload.timestamp,
        round_number=payload.round_number,
        data=payload.data,
    )
    # 实时推送时间轴事件
    await manager.broadcast_event("match_event", {
        "id": event_id,
        "match_id": payload.match_id,
        "event_type": payload.event_type,
        "round_number": payload.round_number,
        "timestamp": payload.timestamp,
        "data": payload.data,
    })
    return MatchEventReportResponse(event_id=event_id, match_id=payload.match_id)


@router.get("/matches", response_model=MatchListResponse)
def list_matches() -> MatchListResponse:
    """列出最近的比赛。"""
    matches_raw = database.list_matches(limit=20)
    matches = [MatchInfo(**m) for m in matches_raw]
    current = database.get_current_match()
    current_id = current["id"] if current else None
    return MatchListResponse(matches=matches, current_match_id=current_id)


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(match_id: str = "") -> TimelineResponse:
    """获取一场比赛的时间轴事件。

    如果不传 match_id，返回当前进行中的比赛。
    """
    if not match_id:
        current = database.get_current_match()
        if current is None:
            return TimelineResponse(match=None, events=[])
        match_id = current["id"]

    match_raw = database.get_match(match_id)
    match = MatchInfo(**match_raw) if match_raw else None

    events_raw = database.get_match_events(match_id)
    events = [MatchEventItem(**e) for e in events_raw]

    return TimelineResponse(match=match, events=events)


@router.get("/matches/{match_id}/review", response_model=MatchReviewResponse)
def get_review(match_id: str) -> MatchReviewResponse:
    """获取比赛的 AI 复盘（已缓存的）。"""
    cached = database.get_match_review(match_id)
    if cached is None:
        # 没有缓存则现场生成
        from ai_review import generate_review
        review_dict = generate_review(match_id)
        cached = database.get_match_review(match_id)
        if cached is None:
            cached = {"match_id": match_id, "review": review_dict, "generated_at": database.now_iso()}

    from models import AIReview, ReviewSection
    review_data = cached["review"]
    sections = [ReviewSection(**s) for s in review_data.get("sections", [])]
    review = AIReview(
        mvp=review_data.get("mvp", ""),
        biggest_mistake=review_data.get("biggest_mistake", ""),
        best_play=review_data.get("best_play", ""),
        death_analysis=review_data.get("death_analysis", ""),
        economy_analysis=review_data.get("economy_analysis", ""),
        ai_commentary=review_data.get("ai_commentary", ""),
        sections=sections,
    )
    return MatchReviewResponse(
        match_id=match_id,
        review=review,
        generated_at=cached["generated_at"],
    )


@router.post("/matches/{match_id}/review", response_model=GenerateReviewResponse)
def generate_review_endpoint(match_id: str) -> GenerateReviewResponse:
    """强制重新生成比赛的 AI 复盘。"""
    from ai_review import generate_review
    review_dict = generate_review(match_id)
    cached = database.get_match_review(match_id)
    generated_at = cached["generated_at"] if cached else database.now_iso()

    from models import AIReview, ReviewSection
    sections = [ReviewSection(**s) for s in review_dict.get("sections", [])]
    review = AIReview(
        mvp=review_dict.get("mvp", ""),
        biggest_mistake=review_dict.get("biggest_mistake", ""),
        best_play=review_dict.get("best_play", ""),
        death_analysis=review_dict.get("death_analysis", ""),
        economy_analysis=review_dict.get("economy_analysis", ""),
        ai_commentary=review_dict.get("ai_commentary", ""),
        sections=sections,
    )
    return GenerateReviewResponse(
        match_id=match_id,
        review=review,
        generated_at=generated_at,
    )
