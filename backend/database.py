"""SQLite 连接、建表、CRUD 与聚合统计查询。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from dateutil import tz

from config import (
    CONFIG_KEY,
    DATA_DIR,
    DB_PATH,
    DEFAULT_CONFIG,
    DEFAULT_GAMES,
    TIMEZONE,
)

_SH_TZ = tz.gettz(TIMEZONE)


# ------------------------------------------------------------------
# 连接管理
# ------------------------------------------------------------------
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    """获取一个 SQLite 连接上下文，自动提交并关闭。"""
    _ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------
# 建表
# ------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS deaths (
    id TEXT PRIMARY KEY,
    game TEXT NOT NULL,
    ts TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    watch_session_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deaths_ts ON deaths(ts);
CREATE INDEX IF NOT EXISTS idx_deaths_game ON deaths(game);

CREATE TABLE IF NOT EXISTS watch_sessions (
    session_id TEXT PRIMARY KEY,
    game TEXT,
    url TEXT,
    start_time TEXT,
    end_time TEXT,
    duration_seconds INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_watch_start ON watch_sessions(start_time);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

-- 比赛记录
CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    game TEXT NOT NULL DEFAULT 'csgo',
    map_name TEXT,
    mode TEXT,
    status TEXT NOT NULL DEFAULT 'live',
    start_time TEXT NOT NULL,
    end_time TEXT,
    score_ct INTEGER DEFAULT 0,
    score_t INTEGER DEFAULT 0,
    rounds_played INTEGER DEFAULT 0,
    player_name TEXT,
    player_steamid TEXT,
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    mvps INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_matches_start ON matches(start_time);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);

-- 比赛事件（时间轴）
CREATE TABLE IF NOT EXISTS match_events (
    id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    round_number INTEGER,
    timestamp TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(id)
);
CREATE INDEX IF NOT EXISTS idx_events_match ON match_events(match_id);
CREATE INDEX IF NOT EXISTS idx_events_ts ON match_events(timestamp);

-- AI 复盘
CREATE TABLE IF NOT EXISTS match_reviews (
    match_id TEXT PRIMARY KEY,
    review_json TEXT NOT NULL DEFAULT '{}',
    generated_at TEXT NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(id)
);

-- 外设配置
CREATE TABLE IF NOT EXISTS gear_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    game TEXT NOT NULL DEFAULT 'csgo',
    mouse_dpi INTEGER DEFAULT 800,
    mouse_polling_rate INTEGER DEFAULT 1000,
    sensitivity REAL DEFAULT 2.0,
    edpi REAL DEFAULT 1600.0,
    keyboard_polling_rate INTEGER DEFAULT 1000,
    keyboard_actuation REAL DEFAULT 2.0,
    volume INTEGER DEFAULT 50,
    playstyle TEXT DEFAULT 'balanced',
    rank TEXT DEFAULT 'gold',
    updated_at TEXT NOT NULL
);

-- 性能监控指标（网络延迟/帧率/卡顿）
CREATE TABLE IF NOT EXISTS perf_metrics (
    id TEXT PRIMARY KEY,
    metric_type TEXT NOT NULL,
    value REAL NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    ts TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_perf_ts ON perf_metrics(ts);
CREATE INDEX IF NOT EXISTS idx_perf_type ON perf_metrics(metric_type);
"""


def init_db() -> None:
    """启动时调用：建表 + 写入默认配置。"""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # 写入默认配置（若不存在）
        row = conn.execute("SELECT 1 FROM config WHERE key = ?", (CONFIG_KEY,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO config(key, value_json) VALUES (?, ?)",
                (CONFIG_KEY, json.dumps(DEFAULT_CONFIG, ensure_ascii=False)),
            )


# ------------------------------------------------------------------
# 时间工具
# ------------------------------------------------------------------
def now_iso() -> str:
    return _fmt(datetime.now(_SH_TZ))


def _fmt(dt: datetime) -> str:
    """统一格式化为 Asia/Shanghai 的 ISO 字符串。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_SH_TZ)
    dt = dt.astimezone(_SH_TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def normalize_ts(raw: str) -> str:
    """解析任意合法时间字符串，统一转为 Asia/Shanghai ISO。"""
    if not raw:
        return now_iso()
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        from dateutil import parser as _parser
        dt = _parser.parse(raw)
    return _fmt(dt)


def compute_period_range(period: str) -> Tuple[str, str, Optional[str], Optional[str], Optional[List[str]]]:
    """根据周期返回 (start_iso, end_iso, prev_start, prev_end, date_buckets)。

    date_buckets 为需要填充的时间轴日期列表；为 None 表示用实际数据。
    """
    today = datetime.now(_SH_TZ).date()
    midnight = datetime.combine(today, datetime.min.time(), tzinfo=_SH_TZ)
    end_of_day = midnight + timedelta(days=1) - timedelta(seconds=1)

    def day_range(d):
        s = datetime.combine(d, datetime.min.time(), tzinfo=_SH_TZ)
        e = s + timedelta(days=1) - timedelta(seconds=1)
        return s, e

    if period == "today":
        s, e = midnight, end_of_day
        ps, pe = day_range(today - timedelta(days=1))
        return _fmt(s), _fmt(e), _fmt(ps), _fmt(pe), [_fmt(s)[:10]]
    if period == "yesterday":
        y = today - timedelta(days=1)
        s, e = day_range(y)
        ps, pe = day_range(today - timedelta(days=2))
        return _fmt(s), _fmt(e), _fmt(ps), _fmt(pe), [_fmt(s)[:10]]
    if period == "week":
        start = midnight - timedelta(days=6)
        prev_start = start - timedelta(days=7)
        prev_end = start - timedelta(seconds=1)
        buckets = [(start.date() + timedelta(days=i)).isoformat() for i in range(7)]
        return _fmt(start), _fmt(end_of_day), _fmt(prev_start), _fmt(prev_end), buckets
    if period == "month":
        start = midnight - timedelta(days=29)
        prev_start = start - timedelta(days=30)
        prev_end = start - timedelta(seconds=1)
        buckets = [(start.date() + timedelta(days=i)).isoformat() for i in range(30)]
        return _fmt(start), _fmt(end_of_day), _fmt(prev_start), _fmt(prev_end), buckets
    # all
    return "0000-01-01T00:00:00+0800", "9999-12-31T23:59:59+0800", None, None, None


# ------------------------------------------------------------------
# 配置 CRUD
# ------------------------------------------------------------------
def load_config() -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value_json FROM config WHERE key = ?", (CONFIG_KEY,)
        ).fetchone()
    if row is None:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    return json.loads(row["value_json"])


def save_config(config: dict) -> dict:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO config(key, value_json) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json",
            (CONFIG_KEY, json.dumps(config, ensure_ascii=False)),
        )
    return config


# ------------------------------------------------------------------
# 死亡事件
# ------------------------------------------------------------------
def insert_death(game: str, ts_raw: str, metadata: dict, watch_session_id: str) -> str:
    event_id = uuid.uuid4().hex
    ts = normalize_ts(ts_raw)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO deaths(id, game, ts, metadata_json, watch_session_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event_id,
                game,
                ts,
                json.dumps(metadata, ensure_ascii=False),
                watch_session_id,
                now_iso(),
            ),
        )
    return event_id


def get_last_death_ts() -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ts FROM deaths ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    return row["ts"] if row else None


def get_death_by_watch_session(session_id: str) -> Optional[dict]:
    """根据 watch_session_id 查询对应的死亡记录，用于补全观看会话的 game 字段。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, game, ts, metadata_json, watch_session_id FROM deaths "
            "WHERE watch_session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "game": row["game"],
        "timestamp": row["ts"],
        "metadata": json.loads(row["metadata_json"] or "{}"),
        "watch_session_id": row["watch_session_id"],
    }


# ------------------------------------------------------------------
# 观看时长
# ------------------------------------------------------------------
def insert_watch_session(
    session_id: str,
    game: str,
    start_time: str,
    end_time: str,
    duration_seconds: int,
    url: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO watch_sessions(session_id, game, url, start_time, end_time, "
            "duration_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "game=excluded.game, url=excluded.url, start_time=excluded.start_time, "
            "end_time=excluded.end_time, duration_seconds=excluded.duration_seconds",
            (
                session_id,
                game,
                url,
                normalize_ts(start_time),
                normalize_ts(end_time),
                int(duration_seconds),
                now_iso(),
            ),
        )


# ------------------------------------------------------------------
# 死亡统计
# ------------------------------------------------------------------
def get_death_stats(period: str, game: str) -> dict:
    start, end, _ps, _pe, buckets = compute_period_range(period)
    game_clause = "" if game == "all" else " AND game = ?"
    params: List[Any] = [start, end]
    if game != "all":
        params.append(game)

    with get_conn() as conn:
        # 总数
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM deaths WHERE ts >= ? AND ts <= ?{game_clause}",
            params,
        ).fetchone()["c"]

        # 按游戏
        by_game_rows = conn.execute(
            f"SELECT game, COUNT(*) AS c FROM deaths WHERE ts >= ? AND ts <= ?{game_clause} "
            "GROUP BY game",
            params,
        ).fetchall()
        by_game = {r["game"]: r["c"] for r in by_game_rows}

        # 时间线（按日期）
        tl_rows = conn.execute(
            f"SELECT substr(ts, 1, 10) AS d, COUNT(*) AS c FROM deaths "
            f"WHERE ts >= ? AND ts <= ?{game_clause} GROUP BY d",
            params,
        ).fetchall()
        tl_map = {r["d"]: r["c"] for r in tl_rows}

        # 按小时
        bh_rows = conn.execute(
            f"SELECT CAST(substr(ts, 12, 2) AS INTEGER) AS h, COUNT(*) AS c FROM deaths "
            f"WHERE ts >= ? AND ts <= ?{game_clause} GROUP BY h ORDER BY h",
            params,
        ).fetchall()
        by_hour = [{"hour": r["h"], "count": r["c"]} for r in bh_rows]

        # 最近
        recent_rows = conn.execute(
            f"SELECT id, game, ts, metadata_json FROM deaths "
            f"WHERE ts >= ? AND ts <= ?{game_clause} ORDER BY ts DESC LIMIT 50",
            params,
        ).fetchall()
        recent = [
            {
                "id": r["id"],
                "game": r["game"],
                "timestamp": r["ts"],
                "metadata": json.loads(r["metadata_json"] or "{}"),
            }
            for r in recent_rows
        ]

    # 填充时间轴
    if buckets is not None:
        timeline = [{"date": d, "count": tl_map.get(d, 0)} for d in buckets]
    else:
        timeline = [{"date": d, "count": c} for d, c in sorted(tl_map.items())]

    return {
        "period": period,
        "total": total,
        "by_game": by_game,
        "timeline": timeline,
        "by_hour": by_hour,
        "recent": recent,
    }


# ------------------------------------------------------------------
# 观看统计
# ------------------------------------------------------------------
def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0分钟"
    total_min = seconds // 60
    h = total_min // 60
    m = total_min % 60
    if h > 0:
        return f"{h}小时{m}分钟"
    return f"{m}分钟"


def get_watch_stats(period: str) -> dict:
    start, end, _ps, _pe, buckets = compute_period_range(period)

    with get_conn() as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) AS s FROM watch_sessions "
            "WHERE start_time >= ? AND start_time <= ?",
            (start, end),
        ).fetchone()
        total_seconds = int(total_row["s"])

        # 按 url
        url_rows = conn.execute(
            "SELECT url, SUM(duration_seconds) AS s FROM watch_sessions "
            "WHERE start_time >= ? AND start_time <= ? GROUP BY url ORDER BY s DESC",
            (start, end),
        ).fetchall()

        # 时间线
        tl_rows = conn.execute(
            "SELECT substr(start_time, 1, 10) AS d, SUM(duration_seconds) AS s "
            "FROM watch_sessions WHERE start_time >= ? AND start_time <= ? GROUP BY d",
            (start, end),
        ).fetchall()
        tl_map = {r["d"]: int(r["s"]) for r in tl_rows}

        # 会话列表
        sess_rows = conn.execute(
            "SELECT session_id, duration_seconds, url, start_time, end_time "
            "FROM watch_sessions WHERE start_time >= ? AND start_time <= ? "
            "ORDER BY start_time DESC LIMIT 100",
            (start, end),
        ).fetchall()
        sessions = [
            {
                "session_id": r["session_id"],
                "duration_seconds": int(r["duration_seconds"] or 0),
                "url": r["url"] or "",
                "start_time": r["start_time"] or "",
                "end_time": r["end_time"] or "",
            }
            for r in sess_rows
        ]

    # url 名称解析（用预设匹配，找不到用 url 兜底）
    config = load_config()
    presets = config.get("presets", [])
    url_name_map = {p["url"]: p.get("name", p["url"]) for p in presets}

    by_url = [
        {
            "url": r["url"] or "",
            "name": url_name_map.get(r["url"] or "", r["url"] or "未知"),
            "seconds": int(r["s"] or 0),
        }
        for r in url_rows
    ]

    if buckets is not None:
        timeline = [{"date": d, "seconds": tl_map.get(d, 0)} for d in buckets]
    else:
        timeline = [{"date": d, "seconds": s} for d, s in sorted(tl_map.items())]

    return {
        "period": period,
        "total_seconds": total_seconds,
        "total_formatted": _format_duration(total_seconds),
        "by_url": by_url,
        "timeline": timeline,
        "sessions": sessions,
    }


# ------------------------------------------------------------------
# 概览
# ------------------------------------------------------------------
def get_overview_stats(period: str, current_game: Optional[str]) -> dict:
    start, end, prev_start, prev_end, _buckets = compute_period_range(period)

    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM deaths WHERE ts >= ? AND ts <= ?",
            (start, end),
        ).fetchone()["c"]

        if prev_start and prev_end:
            prev = conn.execute(
                "SELECT COUNT(*) AS c FROM deaths WHERE ts >= ? AND ts <= ?",
                (prev_start, prev_end),
            ).fetchone()["c"]
            deaths_delta = cur - prev
        else:
            deaths_delta = 0

        watch_cur = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) AS s FROM watch_sessions "
            "WHERE start_time >= ? AND start_time <= ?",
            (start, end),
        ).fetchone()["s"]
        watch_cur = int(watch_cur)

        if prev_start and prev_end:
            watch_prev = conn.execute(
                "SELECT COALESCE(SUM(duration_seconds), 0) AS s FROM watch_sessions "
                "WHERE start_time >= ? AND start_time <= ?",
                (prev_start, prev_end),
            ).fetchone()["s"]
            watch_delta = watch_cur - int(watch_prev)
        else:
            watch_delta = 0

        last_row = conn.execute(
            "SELECT ts FROM deaths WHERE ts >= ? AND ts <= ? ORDER BY ts DESC LIMIT 1",
            (start, end),
        ).fetchone()
        last_death_at = last_row["ts"] if last_row else None

    return {
        "period": period,
        "deaths_total": int(cur),
        "deaths_delta": int(deaths_delta),
        "watch_seconds": watch_cur,
        "watch_delta": int(watch_delta),
        "current_game": current_game,
        "last_death_at": last_death_at,
    }


def get_default_games() -> List[dict]:
    """返回默认游戏定义的深拷贝。"""
    return json.loads(json.dumps(DEFAULT_GAMES))


# ------------------------------------------------------------------
# 比赛记录 (matches)
# ------------------------------------------------------------------
def insert_match(
    map_name: str = "",
    mode: str = "",
    player_name: str = "",
    player_steamid: str = "",
) -> str:
    """创建一条新的比赛记录，返回 match_id。"""
    match_id = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO matches(id, game, map_name, mode, status, start_time, "
            "player_name, player_steamid, metadata_json, created_at) "
            "VALUES (?, 'csgo', ?, ?, 'live', ?, ?, ?, '{}', ?)",
            (
                match_id, map_name, mode, now_iso(),
                player_name, player_steamid, now_iso(),
            ),
        )
    return match_id


def update_match(match_id: str, **fields) -> None:
    """更新比赛记录的指定字段。"""
    if not fields:
        return
    allowed = {
        "map_name", "mode", "status", "end_time", "score_ct", "score_t",
        "rounds_played", "kills", "deaths", "assists", "mvps", "score",
    }
    sets = []
    params: List[Any] = []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return
    params.append(match_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE matches SET {', '.join(sets)} WHERE id = ?", params
        )


def get_match(match_id: str) -> Optional[dict]:
    """获取单场比赛。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
    return d


def get_current_match() -> Optional[dict]:
    """获取当前正在进行的比赛。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM matches WHERE status = 'live' ORDER BY start_time DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_matches(limit: int = 20) -> List[dict]:
    """列出最近的比赛。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM matches ORDER BY start_time DESC LIMIT ?", (limit,)
        ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
        results.append(d)
    return results


# ------------------------------------------------------------------
# 比赛事件 (match_events)
# ------------------------------------------------------------------
def insert_match_event(
    match_id: str,
    event_type: str,
    timestamp: str,
    round_number: Optional[int] = None,
    data: Optional[dict] = None,
) -> str:
    """插入一条比赛事件，返回 event_id。"""
    event_id = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO match_events(id, match_id, event_type, round_number, "
            "timestamp, data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id, match_id, event_type, round_number,
                normalize_ts(timestamp),
                json.dumps(data or {}, ensure_ascii=False),
                now_iso(),
            ),
        )
    return event_id


def get_match_events(match_id: str) -> List[dict]:
    """获取一场比赛的所有事件，按时间正序。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_events WHERE match_id = ? ORDER BY timestamp ASC",
            (match_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "match_id": r["match_id"],
            "event_type": r["event_type"],
            "round_number": r["round_number"],
            "timestamp": r["timestamp"],
            "data": json.loads(r["data_json"] or "{}"),
        }
        for r in rows
    ]


def get_match_events_by_type(
    match_id: str, event_type: str
) -> List[dict]:
    """获取一场比赛中某种类型的所有事件，按时间倒序（最新在最上面）。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM match_events WHERE match_id = ? AND event_type = ? "
            "ORDER BY timestamp DESC",
            (match_id, event_type),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "match_id": r["match_id"],
            "event_type": r["event_type"],
            "round_number": r["round_number"],
            "timestamp": r["timestamp"],
            "data": json.loads(r["data_json"] or "{}"),
        }
        for r in rows
    ]


# ------------------------------------------------------------------
# AI 复盘 (match_reviews)
# ------------------------------------------------------------------
def save_match_review(match_id: str, review: dict) -> None:
    """保存或更新比赛的 AI 复盘。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO match_reviews(match_id, review_json, generated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(match_id) DO UPDATE SET "
            "review_json = excluded.review_json, generated_at = excluded.generated_at",
            (
                match_id,
                json.dumps(review, ensure_ascii=False),
                now_iso(),
            ),
        )


def get_match_review(match_id: str) -> Optional[dict]:
    """获取比赛的 AI 复盘。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT review_json, generated_at FROM match_reviews WHERE match_id = ?",
            (match_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "match_id": match_id,
        "review": json.loads(row["review_json"] or "{}"),
        "generated_at": row["generated_at"],
    }


# ------------------------------------------------------------------
# 外设配置 (gear_config)
# ------------------------------------------------------------------
def get_gear_config() -> dict:
    """获取外设配置（单行表，id=1）。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM gear_config WHERE id = 1"
        ).fetchone()
    if row is None:
        # 首次访问，插入默认行
        _init_gear_config()
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM gear_config WHERE id = 1"
            ).fetchone()
    if row is None:
        return {}
    return dict(row)


def _init_gear_config() -> None:
    """初始化外设配置默认行。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO gear_config(id, game, mouse_dpi, mouse_polling_rate, "
            "sensitivity, edpi, keyboard_polling_rate, keyboard_actuation, "
            "volume, playstyle, rank, updated_at) "
            "VALUES (1, 'csgo', 800, 1000, 2.0, 1600.0, 1000, 2.0, 50, 'balanced', 'gold', ?)",
            (now_iso(),),
        )


def update_gear_config(**fields) -> None:
    """更新外设配置。"""
    allowed = {
        "game", "mouse_dpi", "mouse_polling_rate", "sensitivity", "edpi",
        "keyboard_polling_rate", "keyboard_actuation", "volume",
        "playstyle", "rank",
    }
    sets = []
    params: List[Any] = []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return
    sets.append("updated_at = ?")
    params.append(now_iso())
    params.append(1)  # id = 1
    with get_conn() as conn:
        conn.execute(
            f"UPDATE gear_config SET {', '.join(sets)} WHERE id = ?", params
        )


# ------------------------------------------------------------------
# 性能监控指标 (perf_metrics)
# ------------------------------------------------------------------
def insert_perf_metric(
    metric_type: str,
    value: float,
    detail: Optional[dict] = None,
) -> str:
    """插入一条性能指标记录。"""
    metric_id = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO perf_metrics(id, metric_type, value, detail_json, ts, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                metric_id, metric_type, value,
                json.dumps(detail or {}, ensure_ascii=False),
                now_iso(), now_iso(),
            ),
        )
    return metric_id


def get_perf_metrics(
    metric_type: str = "",
    limit: int = 60,
) -> List[dict]:
    """获取最近的性能指标记录。"""
    if metric_type:
        sql = (
            "SELECT * FROM perf_metrics WHERE metric_type = ? "
            "ORDER BY ts DESC LIMIT ?"
        )
        params: tuple = (metric_type, limit)
    else:
        sql = "SELECT * FROM perf_metrics ORDER BY ts DESC LIMIT ?"
        params = (limit,)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            "id": r["id"],
            "metric_type": r["metric_type"],
            "value": r["value"],
            "detail": json.loads(r["detail_json"] or "{}"),
            "ts": r["ts"],
        }
        for r in rows
    ]


def get_latest_perf() -> dict:
    """获取每种指标的最新一条记录。返回 {latency, fps, stutter}。"""
    result: Dict[str, Optional[dict]] = {"latency": None, "fps": None, "stutter": None}
    with get_conn() as conn:
        for mt in ("latency", "fps", "stutter"):
            row = conn.execute(
                "SELECT * FROM perf_metrics WHERE metric_type = ? "
                "ORDER BY ts DESC LIMIT 1",
                (mt,),
            ).fetchone()
            if row:
                result[mt] = {
                    "value": row["value"],
                    "detail": json.loads(row["detail_json"] or "{}"),
                    "ts": row["ts"],
                }
    return result
