"""与后端通信：上报死亡、上报观看、上报游戏状态、拉取配置。

所有调用失败都不抛异常，仅打 warning，避免 Agent 主循环崩溃。
使用 requests.Session 复用连接。
"""
import logging
from typing import Dict, List, Optional

import requests

from config import BACKEND_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class BackendClient:
    """封装所有后端调用。失败返回空值/False，由调用方自行降级。"""

    def __init__(self, base_url: str = BACKEND_URL, timeout: float = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _warn(self, action: str, exc: Exception) -> None:
        logger.warning("后端调用失败 [%s]: %s", action, exc)

    def get_config(self) -> Dict:
        """GET /api/config 拉取配置。"""
        url = f"{self.base_url}/api/config"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._warn("get_config", e)
            return {}

    def report_death(
        self, game: str, timestamp: str, metadata: Optional[Dict] = None
    ) -> Dict:
        """POST /api/death 上报死亡事件。

        返回 {"event_id":..., "watch_session_id":...}，失败返回 {}。
        """
        url = f"{self.base_url}/api/death"
        payload = {
            "game": game,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._warn("report_death", e)
            return {}

    def report_watch(
        self,
        session_id: str,
        start_time: str,
        end_time: str,
        duration_seconds: int,
        url: str,
    ) -> bool:
        """POST /api/watch 上报观看时长。返回后端是否确认 ok。"""
        api_url = f"{self.base_url}/api/watch"
        payload = {
            "session_id": session_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration_seconds,
            "url": url,
        }
        try:
            resp = self.session.post(api_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("ok", False))
        except Exception as e:
            self._warn("report_watch", e)
            return False

    def report_games_status(
        self,
        games: List[Dict],
        current_game: Optional[str],
        current_game_pid: Optional[int] = None,
    ) -> bool:
        """POST /api/games/status 上报当前游戏状态。"""
        url = f"{self.base_url}/api/games/status"
        payload = {
            "games": games,
            "current_game": current_game,
            "current_game_pid": current_game_pid,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("report_games_status", e)
            return False

    # ---- 比赛事件上报 ----

    def report_match_start(
        self, map_name: str = "", mode: str = "",
        player_name: str = "", player_steamid: str = "",
    ) -> Dict:
        """POST /api/match/start 创建新比赛，返回 {"match_id":...}。"""
        url = f"{self.base_url}/api/match/start"
        payload = {
            "map_name": map_name,
            "mode": mode,
            "player_name": player_name,
            "player_steamid": player_steamid,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._warn("report_match_start", e)
            return {}

    def report_match_end(self, match_id: str, **stats) -> bool:
        """POST /api/match/end 结束比赛。"""
        url = f"{self.base_url}/api/match/end"
        payload = {"match_id": match_id, **stats}
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("report_match_end", e)
            return False

    def report_match_event(
        self, match_id: str, event_type: str, timestamp: str,
        round_number: Optional[int] = None, data: Optional[Dict] = None,
    ) -> Dict:
        """POST /api/match/event 上报比赛事件。"""
        url = f"{self.base_url}/api/match/event"
        payload = {
            "match_id": match_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "round_number": round_number,
            "data": data or {},
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._warn("report_match_event", e)
            return {}

    def report_volume(self, volume: int) -> bool:
        """POST /api/gear/volume 上报系统音量。"""
        url = f"{self.base_url}/api/gear/volume"
        payload = {"volume": volume}
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("report_volume", e)
            return False

    def report_perf(self, metric_type: str, value: float, detail: Optional[Dict] = None) -> bool:
        """POST /api/gear/perf 上报性能指标。"""
        url = f"{self.base_url}/api/gear/perf"
        payload = {
            "metric_type": metric_type,
            "value": value,
            "detail": detail or {},
        }
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("report_perf", e)
            return False

    # ---- 录屏 / 精彩片段（Media 模块，独立于现有功能，失败静默降级）----

    # 视频文件上传超时（秒）——大于普通请求
    _UPLOAD_TIMEOUT = 60.0

    def get_media_settings(self) -> Dict:
        """GET /api/media/settings 拉取录屏配置。失败返回 {}。"""
        url = f"{self.base_url}/api/media/settings"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self._warn("get_media_settings", e)
            return {}

    def report_recording_status(self, recording: bool, match_id: str = "") -> bool:
        """POST /api/media/recording/status 上报录屏状态。"""
        url = f"{self.base_url}/api/media/recording/status"
        payload = {"recording": recording, "match_id": match_id}
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("report_recording_status", e)
            return False

    def upload_clip(
        self,
        match_id: str,
        clip_id: str,
        event_type: str,
        label: str,
        severity: int,
        round_number: Optional[int],
        timestamp: str,
        map_name: str,
        file_path: str,
    ) -> bool:
        """POST /api/media/clips/upload 上传精彩片段视频（raw body + query 元数据）。

        失败返回 False，由调用方决定是否重试。
        """
        url = f"{self.base_url}/api/media/clips/upload"
        params = {
            "match_id": match_id,
            "clip_id": clip_id,
            "event_type": event_type,
            "label": label,
            "severity": severity,
            "round_number": round_number if round_number is not None else 0,
            "timestamp": timestamp,
            "map_name": map_name,
        }
        try:
            with open(file_path, "rb") as f:
                resp = self.session.post(
                    url,
                    params=params,
                    data=f,
                    headers={"Content-Type": "video/mp4"},
                    timeout=self._UPLOAD_TIMEOUT,
                )
            resp.raise_for_status()
            return True
        except Exception as e:
            self._warn("upload_clip", e)
            return False
