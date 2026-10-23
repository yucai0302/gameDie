"""片段业务服务：接收上传、文件落盘、保留/删除、定期清理。

协调 media_database（持久化）+ 文件系统（视频/资产文件）+ ai_clip_service（AI 资产）。
路由层只做 HTTP 编解码，业务逻辑集中在此。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import media_database
from services import ai_clip_service

logger = logging.getLogger(__name__)


def _video_path(filename: str):
    return media_database.get_clips_dir() / filename


def _asset_path(filename: str):
    return media_database.get_clips_dir() / filename


def receive_clip_upload(
    clip_id: str,
    match_id: str,
    event_type: str,
    label: str,
    severity: int,
    round_number: Optional[int],
    timestamp: str,
    map_name: str,
    video_bytes: bytes,
    duration_seconds: int = 30,
) -> dict:
    """处理 Agent 上传的片段：落盘 → 入库（带规则标题/简介）→ 后台生成字幕/封面。

    返回入库后的片段 dict。任何文件/AI 失败都不阻断入库。
    """
    video_filename = f"{clip_id}.mp4"
    path = _video_path(video_filename)

    # 同一 clip_id 重复上传时先清理旧记录与文件
    if media_database.get_clip(clip_id):
        remove_clip(clip_id)

    try:
        with open(path, "wb") as f:
            f.write(video_bytes)
    except Exception as e:
        logger.warning("片段视频落盘失败 clip=%s: %s", clip_id, e)
        raise

    # 规则标题/简介先填入，后台资产生成会再覆盖
    tmp_clip = {
        "id": clip_id,
        "event_type": event_type,
        "label": label,
        "severity": severity,
        "round_number": round_number,
        "map_name": map_name,
        "duration_seconds": duration_seconds,
    }
    title = ai_clip_service.generate_title(tmp_clip) or label
    intro = ai_clip_service.generate_intro(tmp_clip)

    media_database.insert_clip(
        clip_id=clip_id,
        match_id=match_id,
        event_type=event_type,
        label=label,
        severity=severity,
        round_number=round_number,
        timestamp=timestamp,
        map_name=map_name,
        duration_seconds=duration_seconds,
        video_filename=video_filename,
        ai_title=title,
        ai_intro=intro,
    )

    # 同步生成字幕 + 封面（并刷新标题/简介）。失败静默，不阻断入库。
    # 比赛结束后 Agent 逐个上传，此处耗时 ~1s 可接受；ffmpeg 缺失则快速跳过。
    settings = media_database.load_media_settings()
    if settings.get("auto_generate_ai", True):
        ai_clip_service.generate_assets(clip_id)

    return media_database.get_clip(clip_id)


def mark_kept(clip_id: str, kept: bool) -> Optional[dict]:
    media_database.update_clip(clip_id, kept=kept)
    return media_database.get_clip(clip_id)


def remove_clip(clip_id: str) -> bool:
    """删除片段：DB 记录 + 视频文件 + 资产文件。"""
    clip = media_database.delete_clip(clip_id)
    if not clip:
        return False
    # 删视频
    try:
        vpath = _video_path(clip["video_filename"])
        if os.path.exists(vpath):
            os.remove(vpath)
    except OSError:
        pass
    # 删资产（字幕/封面）
    for asset_type in ("subtitle", "cover"):
        fn = media_database.get_asset(clip_id, asset_type)
        if fn:
            try:
                apath = _asset_path(fn)
                if os.path.exists(apath):
                    os.remove(apath)
            except OSError:
                pass
    return True


def batch_update(clip_ids: List[str], action: str) -> dict:
    """批量操作：keep / unkeep / delete。返回成功数。"""
    ok = 0
    for cid in clip_ids:
        if action == "keep":
            if media_database.get_clip(cid):
                media_database.update_clip(cid, kept=True)
                ok += 1
        elif action == "unkeep":
            if media_database.get_clip(cid):
                media_database.update_clip(cid, kept=False)
                ok += 1
        elif action == "delete":
            if remove_clip(cid):
                ok += 1
    return {"ok": ok, "total": len(clip_ids)}


def cleanup_temp_clips(days_old: int = 3) -> dict:
    """清理超过指定天数且未保留的片段。"""
    cutoff = (datetime.now() - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%S")
    targets = media_database.list_unkept_clip_ids(cutoff)
    deleted = 0
    for t in targets:
        if remove_clip(t["id"]):
            deleted += 1
    return {"deleted": deleted, "scanned": len(targets)}


def regenerate_assets(clip_id: str) -> Optional[dict]:
    """强制重新生成 AI 资产（同步）。"""
    if not media_database.get_clip(clip_id):
        return None
    ai_clip_service.generate_assets(clip_id)
    return media_database.get_clip(clip_id)


def video_file_path(clip_id: str):
    """供路由层 FileResponse 使用，返回视频绝对路径或 None。"""
    clip = media_database.get_clip(clip_id)
    if not clip:
        return None
    p = _video_path(clip["video_filename"])
    return p if p.exists() else None


def asset_file_path(clip_id: str, asset_type: str):
    """返回资产文件绝对路径或 None。"""
    fn = media_database.get_asset(clip_id, asset_type)
    if not fn:
        return None
    p = _asset_path(fn)
    return p if p.exists() else None
