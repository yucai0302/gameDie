"""Media 模块独立数据库。

与现有 ``database.py`` 完全隔离：使用独立的 SQLite 文件 ``backend/data/media.db``，
独立的表结构（clips / clip_assets / media_settings / recording_status），独立 init。

独立性约束（功能范畴文档 §7.2 / §7.4）：
- 不在 database.py 里加表，不改现有 schema
- 删除本文件 + 移除 main.py 一行 init 即可恢复现有后端
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR

# 独立 DB 与片段存储目录
MEDIA_DB_PATH = DATA_DIR / "media.db"
CLIPS_DIR = DATA_DIR / "clips"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    """独立的 SQLite 连接上下文。"""
    _ensure_dirs()
    conn = sqlite3.connect(str(MEDIA_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL DEFAULT '',
    event_type TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '',
    severity INTEGER NOT NULL DEFAULT 0,
    round_number INTEGER,
    timestamp TEXT NOT NULL DEFAULT '',
    map_name TEXT NOT NULL DEFAULT '',
    duration_seconds INTEGER NOT NULL DEFAULT 30,
    video_filename TEXT NOT NULL DEFAULT '',
    kept INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ready',
    ai_title TEXT NOT NULL DEFAULT '',
    ai_intro TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clips_match ON clips(match_id);
CREATE INDEX IF NOT EXISTS idx_clips_event ON clips(event_type);
CREATE INDEX IF NOT EXISTS idx_clips_kept ON clips(kept);
CREATE INDEX IF NOT EXISTS idx_clips_created ON clips(created_at);

CREATE TABLE IF NOT EXISTS clip_assets (
    id TEXT PRIMARY KEY,
    clip_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,          -- subtitle / cover
    filename TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (clip_id) REFERENCES clips(id)
);
CREATE INDEX IF NOT EXISTS idx_assets_clip ON clip_assets(clip_id);

CREATE TABLE IF NOT EXISTS media_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    rollback_seconds INTEGER NOT NULL DEFAULT 30,
    encoder TEXT NOT NULL DEFAULT 'auto',
    capture_audio INTEGER NOT NULL DEFAULT 0,
    audio_device TEXT NOT NULL DEFAULT '',
    ffmpeg_path TEXT NOT NULL DEFAULT 'ffmpeg',
    auto_generate_ai INTEGER NOT NULL DEFAULT 1,
    min_multikill INTEGER NOT NULL DEFAULT 3,
    recording_enabled INTEGER NOT NULL DEFAULT 1,
    clips_save_path TEXT NOT NULL DEFAULT '',
    auto_cleanup_enabled INTEGER NOT NULL DEFAULT 1,
    cleanup_days INTEGER NOT NULL DEFAULT 3,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recording_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    recording INTEGER NOT NULL DEFAULT 0,
    match_id TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""


# 默认录屏配置
DEFAULT_SETTINGS = {
    "rollback_seconds": 30,
    "encoder": "auto",
    "capture_audio": False,
    "audio_device": "",
    "ffmpeg_path": "ffmpeg",
    "auto_generate_ai": True,
    "min_multikill": 3,
    "recording_enabled": True,
    "clips_save_path": "",
    "auto_cleanup_enabled": True,
    "cleanup_days": 3,
}


def _migrate_settings(conn) -> None:
    """为已存在的 media_settings 表补齐新增列（兼容旧 media.db）。

    CREATE TABLE IF NOT EXISTS 不会给已存在的表加列，因此对老库需显式 ALTER。
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(media_settings)")}
    additions = [
        ("recording_enabled", "INTEGER NOT NULL DEFAULT 1"),
        ("clips_save_path", "TEXT NOT NULL DEFAULT ''"),
        ("auto_cleanup_enabled", "INTEGER NOT NULL DEFAULT 1"),
        ("cleanup_days", "INTEGER NOT NULL DEFAULT 3"),
    ]
    for name, decl in additions:
        if name not in cols:
            conn.execute(f"ALTER TABLE media_settings ADD COLUMN {name} {decl}")


def init_media_db() -> None:
    """启动时调用：建表 + 迁移 + 写入默认配置。"""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # 兼容老库：给 media_settings 补齐新增列
        _migrate_settings(conn)
        row = conn.execute("SELECT 1 FROM media_settings WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO media_settings(id, rollback_seconds, encoder, "
                "capture_audio, audio_device, ffmpeg_path, auto_generate_ai, "
                "min_multikill, recording_enabled, clips_save_path, "
                "auto_cleanup_enabled, cleanup_days, updated_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    DEFAULT_SETTINGS["rollback_seconds"],
                    DEFAULT_SETTINGS["encoder"],
                    int(DEFAULT_SETTINGS["capture_audio"]),
                    DEFAULT_SETTINGS["audio_device"],
                    DEFAULT_SETTINGS["ffmpeg_path"],
                    int(DEFAULT_SETTINGS["auto_generate_ai"]),
                    DEFAULT_SETTINGS["min_multikill"],
                    int(DEFAULT_SETTINGS["recording_enabled"]),
                    DEFAULT_SETTINGS["clips_save_path"],
                    int(DEFAULT_SETTINGS["auto_cleanup_enabled"]),
                    DEFAULT_SETTINGS["cleanup_days"],
                    now_iso(),
                ),
            )
        row = conn.execute("SELECT 1 FROM recording_status WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO recording_status(id, recording, match_id, updated_at) "
                "VALUES (1, 0, '', ?)",
                (now_iso(),),
            )


# ------------------------------------------------------------------
# 时间工具
# ------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ------------------------------------------------------------------
# 片段 CRUD
# ------------------------------------------------------------------
def insert_clip(
    clip_id: str,
    match_id: str,
    event_type: str,
    label: str,
    severity: int,
    round_number: Optional[int],
    timestamp: str,
    map_name: str,
    duration_seconds: int,
    video_filename: str,
    ai_title: str = "",
    ai_intro: str = "",
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO clips(id, match_id, event_type, label, severity, "
            "round_number, timestamp, map_name, duration_seconds, video_filename, "
            "kept, status, ai_title, ai_intro, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'ready', ?, ?, ?)",
            (
                clip_id, match_id, event_type, label, severity,
                round_number, timestamp, map_name, duration_seconds,
                video_filename, ai_title, ai_intro, now_iso(),
            ),
        )


def _row_to_clip(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "match_id": row["match_id"],
        "event_type": row["event_type"],
        "label": row["label"],
        "severity": row["severity"],
        "round_number": row["round_number"],
        "timestamp": row["timestamp"],
        "map_name": row["map_name"],
        "duration_seconds": row["duration_seconds"],
        "video_filename": row["video_filename"],
        "kept": bool(row["kept"]),
        "status": row["status"],
        "ai_title": row["ai_title"],
        "ai_intro": row["ai_intro"],
        "created_at": row["created_at"],
    }


def get_clip(clip_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
    return _row_to_clip(row) if row else None


def list_clips(
    match_id: Optional[str] = None,
    event_type: Optional[str] = None,
    kept_only: bool = False,
    limit: int = 200,
) -> List[dict]:
    sql = "SELECT * FROM clips WHERE 1=1"
    params: List[Any] = []
    if match_id:
        sql += " AND match_id = ?"
        params.append(match_id)
    if event_type:
        sql += " AND event_type = ?"
        params.append(event_type)
    if kept_only:
        sql += " AND kept = 1"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_clip(r) for r in rows]


def list_matches_with_clips() -> List[dict]:
    """列出有片段的比赛（按比赛分组统计）。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT match_id, COUNT(*) AS cnt, MAX(created_at) AS latest "
            "FROM clips GROUP BY match_id ORDER BY latest DESC"
        ).fetchall()
    return [
        {
            "match_id": r["match_id"],
            "clip_count": r["cnt"],
            "latest_at": r["latest"],
        }
        for r in rows
    ]


def update_clip(clip_id: str, **fields) -> None:
    if not fields:
        return
    allowed = {"kept", "status", "ai_title", "ai_intro"}
    sets = []
    params: List[Any] = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "kept":
            v = 1 if v else 0
        sets.append(f"{k} = ?")
        params.append(v)
    if not sets:
        return
    params.append(clip_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE clips SET {', '.join(sets)} WHERE id = ?", params)


def delete_clip(clip_id: str) -> Optional[dict]:
    """删除片段记录，返回被删片段（含文件名，供 service 删文件）。"""
    clip = get_clip(clip_id)
    if not clip:
        return None
    with get_conn() as conn:
        conn.execute("DELETE FROM clip_assets WHERE clip_id = ?", (clip_id,))
        conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
    return clip


def list_unkept_clip_ids(before_iso: Optional[str] = None) -> List[dict]:
    """列出未保留的片段（用于定期清理）。"""
    sql = "SELECT id, video_filename FROM clips WHERE kept = 0"
    params: List[Any] = []
    if before_iso:
        sql += " AND created_at < ?"
        params.append(before_iso)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{"id": r["id"], "video_filename": r["video_filename"]} for r in rows]


# ------------------------------------------------------------------
# 片段资产（字幕 / 封面）
# ------------------------------------------------------------------
def insert_asset(clip_id: str, asset_type: str, filename: str) -> None:
    with get_conn() as conn:
        # 同类资产覆盖：先删旧
        conn.execute(
            "DELETE FROM clip_assets WHERE clip_id = ? AND asset_type = ?",
            (clip_id, asset_type),
        )
        conn.execute(
            "INSERT INTO clip_assets(id, clip_id, asset_type, filename, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, clip_id, asset_type, filename, now_iso()),
        )


def get_asset(clip_id: str, asset_type: str) -> Optional[str]:
    """返回资产的文件名，无则 None。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT filename FROM clip_assets WHERE clip_id = ? AND asset_type = ?",
            (clip_id, asset_type),
        ).fetchone()
    return row["filename"] if row else None


# ------------------------------------------------------------------
# 录屏配置
# ------------------------------------------------------------------
def load_media_settings() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM media_settings WHERE id = 1").fetchone()
    if not row:
        return dict(DEFAULT_SETTINGS)
    return {
        "rollback_seconds": row["rollback_seconds"],
        "encoder": row["encoder"],
        "capture_audio": bool(row["capture_audio"]),
        "audio_device": row["audio_device"],
        "ffmpeg_path": row["ffmpeg_path"],
        "auto_generate_ai": bool(row["auto_generate_ai"]),
        "min_multikill": row["min_multikill"],
        "recording_enabled": bool(row["recording_enabled"]),
        "clips_save_path": row["clips_save_path"],
        "auto_cleanup_enabled": bool(row["auto_cleanup_enabled"]),
        "cleanup_days": row["cleanup_days"],
    }


def save_media_settings(patch: dict) -> dict:
    allowed = {
        "rollback_seconds", "encoder", "capture_audio", "audio_device",
        "ffmpeg_path", "auto_generate_ai", "min_multikill",
        "recording_enabled", "clips_save_path",
        "auto_cleanup_enabled", "cleanup_days",
    }
    sets = []
    params: List[Any] = []
    for k, v in patch.items():
        if k not in allowed:
            continue
        if k in ("capture_audio", "auto_generate_ai", "recording_enabled", "auto_cleanup_enabled"):
            v = 1 if v else 0
        sets.append(f"{k} = ?")
        params.append(v)
    if sets:
        sets.append("updated_at = ?")
        params.append(now_iso())
        # WHERE id = 1 是字面量（media_settings 单行表），无需占位符
        with get_conn() as conn:
            conn.execute(
                f"UPDATE media_settings SET {', '.join(sets)} WHERE id = 1", params
            )
    return load_media_settings()


def get_clips_dir() -> Path:
    """返回当前配置的片段保存目录。

    - settings.clips_save_path 非空 → 用自定义路径
    - 否则回退到默认 CLIPS_DIR（backend/data/clips）

    返回前确保目录存在。每次调用读一次 DB —— 片段读写频率低，可接受。
    """
    try:
        settings = load_media_settings()
        custom = (settings.get("clips_save_path") or "").strip()
    except Exception:
        custom = ""
    p = Path(custom) if custom else CLIPS_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


# ------------------------------------------------------------------
# 录屏状态
# ------------------------------------------------------------------
def set_recording_status(recording: bool, match_id: str = "") -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE recording_status SET recording = ?, match_id = ?, updated_at = ? "
            "WHERE id = 1",
            (1 if recording else 0, match_id, now_iso()),
        )
    return get_recording_status()


def get_recording_status() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM recording_status WHERE id = 1").fetchone()
    if not row:
        return {"recording": False, "match_id": "", "updated_at": ""}
    return {
        "recording": bool(row["recording"]),
        "match_id": row["match_id"],
        "updated_at": row["updated_at"],
    }
