"""录屏控制器：把 GSI 事件映射为录屏动作，管理片段提取与上传生命周期。

注入方式（agent/main.py）：
    # __init__ 中
    self.recorder = RecordingController(
        client=self.client,
        get_match_id=lambda: self.current_match_id,
        get_game_pid=lambda: (self.current_game or {}).get("pid"),
    )
    # on_match_event 顶部
    self.recorder.on_event(event)

事件 → 动作映射（与功能范畴文档 §2.2 对齐）：
    match_start → 拉取 settings / 解析窗口标题 / 启动 ffmpeg 录屏
    death       → 回捞死亡前 30s 片段（后台提取）/ 暂停录屏
    respawn     → 恢复录屏
    kill        → 单回合击杀达 3/4/5 → 回捞精彩片段（后台提取），继续录屏
    match_end   → 停止录屏 / 后台上传所有片段 / 清理临时目录

并发模型：提取与上传交给单线程执行器，on_event 立即返回，不阻塞 GSI 回调。
所有异常被吞掉并打 warning —— 录屏任何一步失败都不影响现有事件采集 / 复盘。
"""
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from . import config as rec_cfg
from .recorder import Recorder, get_window_title_by_pid

logger = logging.getLogger("agent.recording")


class RecordingController:
    """事件驱动的录屏控制器。可插拔：失败时静默降级，不影响宿主 Agent。"""

    def __init__(
        self,
        client,
        get_match_id: Callable[[], Optional[str]],
        get_game_pid: Callable[[], Optional[int]],
    ):
        self._client = client
        self._get_match_id = get_match_id
        self._get_game_pid = get_game_pid

        self._recorder: Optional[Recorder] = None
        self._session_dir: Optional[str] = None
        self._window_title: Optional[str] = None
        self._match_active = False
        self._map_name: str = ""
        self._settings: Dict = {}

        # 已提取、待上传的片段
        self._pending_clips: List[Dict] = []
        self._pending_lock = threading.Lock()
        # 单线程执行器：保证提取/上传任务串行，避免并发读写分段
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="recording-worker")
        self._inflight = 0
        self._inflight_lock = threading.Lock()

    # ---------------- 对外入口 ----------------

    def on_event(self, event: Dict) -> None:
        """GSI 事件入口。安全包装：任何异常不外泄。"""
        try:
            self._dispatch(event)
        except Exception as e:
            logger.warning("录屏控制器处理事件异常: %s", e)

    def shutdown(self) -> None:
        """Agent 退出 / 游戏关闭时调用：收尾并尽量完成上传。"""
        try:
            self._finalize_match(wait=True)
            self._executor.shutdown(wait=True, timeout=30)
        except Exception as e:
            logger.warning("录屏控制器关闭异常: %s", e)

    # ---------------- 事件分发 ----------------

    def _dispatch(self, event: Dict) -> None:
        etype = event.get("event_type", "")
        data = event.get("data", {}) or {}

        if etype == "match_start":
            self._on_match_start(data)
        elif etype == "match_end":
            self._on_match_end()
        elif etype == "death":
            self._on_death(event)
        elif etype == "respawn":
            self._on_respawn()
        elif etype == "kill":
            self._on_kill(event)

    def _on_match_start(self, data: Dict) -> None:
        # 上一场未正常结束则先收尾
        if self._match_active:
            self._finalize_match(wait=False)
        self._map_name = data.get("map", "") or ""

        # 拉取录屏配置（失败用默认值）
        self._settings = self._fetch_settings()

        # 录屏总开关：关闭则完全不启动 ffmpeg，仅标记比赛进行中
        # 事件采集 / 复盘等现有功能不受影响，死亡/多杀也不会触发回捞
        if not bool(self._settings.get("recording_enabled", True)):
            logger.info("录屏已关闭（recording_enabled=False），本场跳过录屏")
            self._match_active = True
            self._recorder = None
            self._session_dir = None
            self._window_title = None
            self._report_status(recording=False)
            return

        # 解析游戏窗口标题
        pid = self._get_game_pid()
        window_title = get_window_title_by_pid(pid) if pid else None
        if not window_title:
            logger.warning("录屏：未找到游戏窗口 (pid=%s)，本场跳过录屏", pid)
            self._window_title = None
            self._match_active = True
            return
        self._window_title = window_title

        # 建立本场会话目录
        session_id = time.strftime("%Y%m%d%H%M%S")
        self._session_dir = os.path.join(rec_cfg.RECORDING_ROOT, session_id)
        os.makedirs(self._session_dir, exist_ok=True)

        rollback = int(self._settings.get("rollback_seconds", rec_cfg.DEFAULT_ROLLBACK_SECONDS))
        capture_audio = bool(self._settings.get("capture_audio", rec_cfg.CAPTURE_AUDIO_DEFAULT))
        audio_device = self._settings.get("audio_device", "") or ""
        ffmpeg_bin = self._settings.get("ffmpeg_path") or rec_cfg.FFMPEG_BIN

        self._recorder = Recorder(
            session_dir=self._session_dir,
            ffmpeg_bin=ffmpeg_bin,
            rollback_seconds=rollback,
            capture_audio=capture_audio,
            audio_device=audio_device,
        )
        self._recorder.start(window_title)
        self._match_active = True
        self._report_status(recording=self._recorder.is_recording)

    def _on_match_end(self) -> None:
        # 后台收尾：停止录屏 → 等待提取完成 → 上传 → 清理
        self._executor.submit(self._finalize_match, True)
        self._match_active = False
        self._report_status(recording=False)

    def _on_death(self, event: Dict) -> None:
        if not self._match_active:
            return
        match_id = self._get_match_id()
        round_number = event.get("round_number")
        timestamp = event.get("timestamp", "")
        self._submit_extraction(
            event_type="death",
            label="死亡回放",
            severity=0,
            match_id=match_id,
            round_number=round_number,
            timestamp=timestamp,
        )
        # 暂停录屏（死亡观战阶段不录，省资源）。复活时恢复
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop()

    def _on_respawn(self) -> None:
        if not self._match_active or not self._window_title:
            return
        if self._recorder and not self._recorder.is_recording:
            self._recorder.start(self._window_title)
            self._report_status(recording=self._recorder.is_recording)

    def _on_kill(self, event: Dict) -> None:
        if not self._match_active:
            return
        data = event.get("data", {}) or {}
        round_kills = data.get("round_kills")
        try:
            rk = int(round_kills) if round_kills is not None else 0
        except (TypeError, ValueError):
            rk = 0
        if rk < rec_cfg.MULTIKILL_THRESHOLD:
            return

        # 里程碑：3=三杀 / 4=四杀 / 5=ACE
        if rk >= rec_cfg.ACE_THRESHOLD:
            label, severity, etype = "ACE", rk, "ace"
        elif rk == 4:
            label, severity, etype = "四杀", rk, "multi_kill"
        else:  # rk == 3
            label, severity, etype = "三杀", rk, "multi_kill"

        match_id = self._get_match_id()
        self._submit_extraction(
            event_type=etype,
            label=label,
            severity=severity,
            match_id=match_id,
            round_number=event.get("round_number"),
            timestamp=event.get("timestamp", ""),
        )

    # ---------------- 提取任务 ----------------

    def _submit_extraction(
        self,
        event_type: str,
        label: str,
        severity: int,
        match_id: Optional[str],
        round_number: Optional[int],
        timestamp: str,
    ) -> None:
        if self._recorder is None or self._session_dir is None:
            return
        clip_id = uuid.uuid4().hex
        out_path = os.path.join(self._session_dir, f"clip_{clip_id}.mp4")
        meta = {
            "clip_id": clip_id,
            "match_id": match_id or "",
            "event_type": event_type,
            "label": label,
            "severity": severity,
            "round_number": round_number,
            "timestamp": timestamp,
            "map_name": self._map_name,
            "file_path": out_path,
        }
        with self._inflight_lock:
            self._inflight += 1

        def _task():
            try:
                ok = self._recorder.extract_clip(out_path)
                if ok:
                    with self._pending_lock:
                        self._pending_clips.append(meta)
                    logger.info("片段已提取待上传: %s (%s)", label, clip_id)
            except Exception as e:
                logger.warning("提取片段异常 %s: %s", label, e)
            finally:
                with self._inflight_lock:
                    self._inflight -= 1

        self._executor.submit(_task)

    # ---------------- 收尾 / 上传 ----------------

    def _finalize_match(self, wait: bool) -> None:
        """停止录屏，等待所有提取完成，上传所有片段，清理会话目录。"""
        if self._recorder:
            self._recorder.stop()
            self._report_status(recording=False)

        # 等待在途提取任务完成
        if wait:
            deadline = time.time() + 30
            while time.time() < deadline:
                with self._inflight_lock:
                    if self._inflight == 0:
                        break
                time.sleep(0.3)
        else:
            # 非阻塞模式：给一点时间让在途任务排进执行器
            time.sleep(0.1)

        # 取出待上传片段
        with self._pending_lock:
            clips_to_upload = list(self._pending_clips)
            self._pending_clips.clear()

        for clip in clips_to_upload:
            self._upload_clip(clip)

        # 清理会话目录（分段 + 已上传片段）
        self._cleanup_session_dir()

        self._recorder = None
        self._session_dir = None
        self._window_title = None
        self._match_active = False

    def _upload_clip(self, clip: Dict) -> None:
        path = clip.get("file_path")
        if not path or not os.path.exists(path):
            logger.warning("片段文件不存在，跳过上传: %s", path)
            return
        # 仅上传与当前比赛关联的片段；match_id 缺失则仍上传（标记为无比赛）
        for attempt in range(rec_cfg.UPLOAD_RETRIES + 1):
            try:
                ok = self._client.upload_clip(
                    match_id=clip.get("match_id", ""),
                    clip_id=clip["clip_id"],
                    event_type=clip["event_type"],
                    label=clip["label"],
                    severity=clip["severity"],
                    round_number=clip.get("round_number"),
                    timestamp=clip.get("timestamp", ""),
                    map_name=clip.get("map_name", ""),
                    file_path=path,
                )
                if ok:
                    logger.info("片段上传成功: %s (%s)", clip["label"], clip["clip_id"])
                    return
            except Exception as e:
                logger.warning("片段上传异常 (尝试 %d): %s", attempt + 1, e)
        logger.warning("片段上传最终失败: %s", clip["clip_id"])

    def _cleanup_session_dir(self) -> None:
        if not self._session_dir:
            return
        try:
            for name in os.listdir(self._session_dir):
                p = os.path.join(self._session_dir, name)
                try:
                    os.remove(p)
                except OSError:
                    pass
            os.rmdir(self._session_dir)
        except OSError:
            pass

    # ---------------- 辅助 ----------------

    def _fetch_settings(self) -> Dict:
        getter = getattr(self._client, "get_media_settings", None)
        if not callable(getter):
            return {}
        try:
            return getter() or {}
        except Exception as e:
            logger.debug("拉取录屏配置失败，用默认值: %s", e)
            return {}

    def _report_status(self, recording: bool) -> None:
        """向后端上报录屏状态（失败静默）。"""
        reporter = getattr(self._client, "report_recording_status", None)
        if not callable(reporter):
            return
        try:
            reporter(recording=recording, match_id=self._get_match_id() or "")
        except Exception:
            pass
