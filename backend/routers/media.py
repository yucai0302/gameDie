"""Media 模块路由：精彩片段库 + 录屏配置 + 录屏状态。

挂载在 /api/media 前缀下（main.py 加一行 include_router）。
WebSocket 事件使用独立前缀：media_clip_ready / media_recording_status，
不与现有 match_event / death 等混淆。

Pydantic 模型内联定义，不修改现有 models.py（保持独立性）。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

import media_database
from services import clip_service
from state import manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------
# 请求模型
# ------------------------------------------------------------------
class KeepRequest(BaseModel):
    kept: bool = True


class BatchRequest(BaseModel):
    clip_ids: List[str]
    action: str  # keep / unkeep / delete


class SettingsUpdate(BaseModel):
    rollback_seconds: Optional[int] = None
    encoder: Optional[str] = None
    capture_audio: Optional[bool] = None
    audio_device: Optional[str] = None
    ffmpeg_path: Optional[str] = None
    auto_generate_ai: Optional[bool] = None
    min_multikill: Optional[int] = None
    recording_enabled: Optional[bool] = None
    clips_save_path: Optional[str] = None
    auto_cleanup_enabled: Optional[bool] = None
    cleanup_days: Optional[int] = None


class RecordingStatusReport(BaseModel):
    recording: bool
    match_id: str = ""


# ------------------------------------------------------------------
# 片段上传（Agent 调用）
# ------------------------------------------------------------------
@router.post("/clips/upload")
async def upload_clip(
    request: Request,
    clip_id: str = Query(...),
    match_id: str = Query(""),
    event_type: str = Query(...),
    label: str = Query(""),
    severity: int = Query(0),
    round_number: int = Query(0),
    timestamp: str = Query(""),
    map_name: str = Query(""),
    duration_seconds: int = Query(30),
):
    """接收 Agent 上传的精彩片段视频（raw body）+ query 元数据。

    落盘后同步生成 AI 标题/简介/字幕/封面，再通过 WebSocket 推送 media_clip_ready。
    """
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty body")

    try:
        clip = clip_service.receive_clip_upload(
            clip_id=clip_id,
            match_id=match_id,
            event_type=event_type,
            label=label,
            severity=severity,
            round_number=round_number or None,
            timestamp=timestamp,
            map_name=map_name,
            video_bytes=body,
            duration_seconds=duration_seconds,
        )
    except Exception as e:
        logger.warning("片段上传处理失败 clip=%s: %s", clip_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    # 推送新片段就绪事件（独立前缀，不与现有事件混淆）
    await manager.broadcast_event("media_clip_ready", clip)
    return clip


# ------------------------------------------------------------------
# 片段查询
# ------------------------------------------------------------------
@router.get("/clips")
def list_clips(
    match_id: str = Query(""),
    event_type: str = Query(""),
    kept_only: bool = Query(False),
):
    return {
        "clips": media_database.list_clips(
            match_id=match_id or None,
            event_type=event_type or None,
            kept_only=kept_only,
        )
    }


@router.get("/matches")
def list_matches():
    """列出有片段的比赛分组。"""
    return {"matches": media_database.list_matches_with_clips()}


@router.get("/clips/{clip_id}")
def get_clip(clip_id: str):
    clip = media_database.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")
    return clip


# ------------------------------------------------------------------
# 片段媒体文件（视频 / 字幕 / 封面）
# ------------------------------------------------------------------
@router.get("/clips/{clip_id}/video")
def get_clip_video(clip_id: str):
    path = clip_service.video_file_path(clip_id)
    if not path:
        raise HTTPException(status_code=404, detail="video not found")
    return FileResponse(str(path), media_type="video/mp4")


@router.get("/clips/{clip_id}/subtitle")
def get_clip_subtitle(clip_id: str):
    path = clip_service.asset_file_path(clip_id, "subtitle")
    if not path:
        raise HTTPException(status_code=404, detail="subtitle not found")
    return FileResponse(str(path), media_type="text/vtt; charset=utf-8")


@router.get("/clips/{clip_id}/cover")
def get_clip_cover(clip_id: str):
    path = clip_service.asset_file_path(clip_id, "cover")
    if not path:
        raise HTTPException(status_code=404, detail="cover not found")
    return FileResponse(str(path), media_type="image/jpeg")


# ------------------------------------------------------------------
# 片段管理
# ------------------------------------------------------------------
@router.put("/clips/{clip_id}/keep")
def keep_clip(clip_id: str, payload: KeepRequest):
    clip = clip_service.mark_kept(clip_id, payload.kept)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")
    return clip


@router.delete("/clips/{clip_id}")
def delete_clip(clip_id: str):
    if not clip_service.remove_clip(clip_id):
        raise HTTPException(status_code=404, detail="clip not found")
    return {"ok": True, "id": clip_id}


@router.post("/clips/batch")
def batch_clips(payload: BatchRequest):
    if payload.action not in ("keep", "unkeep", "delete"):
        raise HTTPException(status_code=400, detail="invalid action")
    return clip_service.batch_update(payload.clip_ids, payload.action)


@router.post("/clips/{clip_id}/regenerate")
def regenerate_clip(clip_id: str):
    clip = clip_service.regenerate_assets(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")
    return clip


@router.post("/cleanup")
def cleanup_clips(days_old: int = Query(3)):
    """清理未保留的旧片段（临时目录）。"""
    return clip_service.cleanup_temp_clips(days_old=days_old)


# ------------------------------------------------------------------
# 录屏配置
# ------------------------------------------------------------------
@router.get("/settings")
def get_settings():
    return media_database.load_media_settings()


@router.put("/settings")
def update_settings(payload: SettingsUpdate):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    return media_database.save_media_settings(patch)


# ------------------------------------------------------------------
# 录屏状态（Agent 上报 + 前端查询）
# ------------------------------------------------------------------
@router.get("/recording/status")
def get_recording_status():
    return media_database.get_recording_status()


@router.post("/recording/status")
async def report_recording_status(payload: RecordingStatusReport):
    status = media_database.set_recording_status(payload.recording, payload.match_id)
    await manager.broadcast_event("media_recording_status", status)
    return status
