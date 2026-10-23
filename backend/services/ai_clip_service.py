"""AI 精彩片段资产生成：标题 / 简介 / 字幕(事件标注) / 封面。

采用「规则生成」策略（与 ai_review.py 的规则层一致），确定性高、无外部依赖。
字幕为 WebVTT 格式（浏览器 <track> 可直接渲染），事件标注贴在片段末尾的高光时刻。
封面用 ffmpeg 抽取一帧关键画面。所有步骤失败均静默降级，不阻断片段入库。

LLM 增强为可选项（后续可读取共享 llm 配置润色标题），Phase A 先用规则版。
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
from typing import Optional

import media_database

logger = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# 常见地图友好名（去 de_ / cs_ 前缀）
_MAP_FRIENDLY = {
    "de_dust2": "沙漠2",
    "de_mirage": "荒漠迷城",
    "de_inferno": "炼狱小镇",
    "de_nuke": "核子危机",
    "de_overpass": "死亡游乐园",
    "de_vertigo": "眩晕大厦",
    "de_ancient": "远古遗迹",
    "de_anubis": "阿努比斯",
    "de_cache": "特工基地",
    "de_train": "列车停放站",
    "cs_office": "办公室",
    "cs_italy": "意大利",
    "cs_assault": "72号仓库",
}


def _map_label(map_name: str) -> str:
    if not map_name:
        return ""
    return _MAP_FRIENDLY.get(map_name, map_name)


def _round_label(round_number) -> str:
    try:
        return f"第{int(round_number)}回合" if round_number is not None else ""
    except (TypeError, ValueError):
        return ""


def generate_title(clip: dict) -> str:
    """规则生成标题。"""
    etype = clip.get("event_type", "")
    label = clip.get("label", "")
    mp = _map_label(clip.get("map_name", ""))
    rnd = _round_label(clip.get("round_number"))
    sev = clip.get("severity", 0)

    if etype == "ace":
        head = "ACE！"
    elif etype == "multi_kill":
        head = f"{label}！" if label else "多杀！"
    elif etype == "death":
        head = "死亡回放"
    else:
        head = label or "精彩片段"

    parts = [head]
    if mp:
        parts.append(mp)
    if rnd:
        parts.append(rnd)
    if etype == "ace":
        parts.append("五杀")
    elif etype == "multi_kill" and sev:
        parts.append(f"{sev}杀")
    return " ".join(parts)


def generate_intro(clip: dict) -> str:
    """规则生成一句话简介。"""
    etype = clip.get("event_type", "")
    rnd = _round_label(clip.get("round_number"))
    mp = _map_label(clip.get("map_name", ""))
    place = f"{mp}{rnd}" if mp and rnd else (mp or rnd)

    if etype == "ace":
        base = f"{place}完成 ACE，连续击杀全部对手，高压下的完美操作。" if place else "连续击杀全部对手，完成 ACE。"
    elif etype == "multi_kill":
        base = f"{place}拿下多杀，连续击杀为团队打开局面。" if place else "连续击杀多名对手。"
    elif etype == "death":
        base = f"{place}阵亡前 30 秒回放，回顾走位与交火细节。" if place else "阵亡前 30 秒回放。"
    else:
        base = "本场精彩瞬间回放。"
    return base


def generate_subtitle(clip: dict) -> Optional[str]:
    """生成 WebVTT 字幕文件名（写入磁盘）。失败返回 None。

    事件标注策略：开头贴比赛上下文，结尾贴高光标签。
    """
    duration = int(clip.get("duration_seconds", 30) or 30)
    label = clip.get("label", "")
    mp = _map_label(clip.get("map_name", ""))
    rnd = _round_label(clip.get("round_number"))
    context = f"{mp} {rnd}".strip()

    clip_id = clip["id"]
    filename = f"{clip_id}.vtt"
    path = media_database.get_clips_dir() / filename

    def _ts(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec - h * 3600 - m * 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    start_cue_end = min(4, duration)
    end_cue_start = max(0, duration - 6)
    end_cue_end = duration

    lines = ["WEBVTT", ""]
    if context:
        lines += [f"{_ts(0)} --> {_ts(start_cue_end)}", context, ""]
    if label:
        lines += [f"{_ts(end_cue_start)} --> {_ts(end_cue_end)}", f"{label}！", ""]

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return filename
    except Exception as e:
        logger.warning("生成字幕失败 clip=%s: %s", clip_id, e)
        return None


def generate_cover(clip: dict, video_path) -> Optional[str]:
    """用 ffmpeg 抽取一帧作为封面，返回封面文件名。失败返回 None。"""
    if not os.path.exists(video_path):
        return None
    settings = media_database.load_media_settings()
    ffmpeg_bin = settings.get("ffmpeg_path") or "ffmpeg"
    clip_id = clip["id"]
    filename = f"{clip_id}.jpg"
    cover_path = media_database.get_clips_dir() / filename

    # 在 3 秒处抽帧（30s 片段里安全位置）；失败则尝试 1 秒
    for offset in ("3", "1", "0"):
        cmd = [
            ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", offset, "-i", str(video_path),
            "-frames:v", "1", "-q:v", "3",
            str(cover_path),
        ]
        try:
            r = subprocess.run(
                cmd, capture_output=True, timeout=15,
                creationflags=_CREATE_NO_WINDOW,
            )
        except Exception as e:
            logger.debug("抽取封面异常 clip=%s: %s", clip_id, e)
            continue
        if r.returncode == 0 and os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
            return filename
    logger.warning("抽取封面最终失败 clip=%s", clip_id)
    return None


def generate_assets(clip_id: str) -> None:
    """为指定片段生成全部 AI 资产：标题 / 简介（写库）+ 字幕 / 封面（写文件 + 写资产表）。

    在后台线程调用，失败不抛异常。
    """
    clip = media_database.get_clip(clip_id)
    if not clip:
        return

    # 标题 / 简介
    title = generate_title(clip) or clip.get("label", "")
    intro = generate_intro(clip)
    media_database.update_clip(clip_id, ai_title=title, ai_intro=intro)

    # 字幕
    sub_file = generate_subtitle({**clip, "ai_title": title})
    if sub_file:
        media_database.insert_asset(clip_id, "subtitle", sub_file)

    # 封面
    video_path = media_database.get_clips_dir() / clip["video_filename"]
    cover_file = generate_cover(clip, video_path)
    if cover_file:
        media_database.insert_asset(clip_id, "cover", cover_file)

    logger.info("片段 AI 资产生成完成: %s (%s)", clip_id, title)


def generate_assets_async(clip_id: str) -> None:
    """后台线程生成资产，立即返回。"""
    t = threading.Thread(
        target=_safe_generate, args=(clip_id,), daemon=True, name="ai-clip-gen"
    )
    t.start()


def _safe_generate(clip_id: str) -> None:
    try:
        generate_assets(clip_id)
    except Exception as e:
        logger.warning("片段资产生成异常 clip=%s: %s", clip_id, e)
