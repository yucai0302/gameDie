"""ffmpeg 环形缓冲录屏器。

策略：用 ffmpeg 的 segment muxer 把画面按固定时长切成一系列 mp4 分段文件，
配合后台清理线程只保留最近 RETENTION_SECONDS 秒的分段，构成滑动窗口。
需要回捞精彩片段时，从分段目录中选出最近 N 秒的分段，concat 重编码为一个
独立 mp4。

录制内容：游戏窗口（gdigrab 按窗口标题）。系统音频为可选项：当 settings 中
配置了 audio_device 时附加 dshow 音频输入，否则纯视频（保证开箱即用）。

所有错误均被捕获并降级：ffmpeg 缺失 / 窗口找不到 / 启动失败 → is_recording=False，
不影响调用方。
"""
import ctypes
import logging
import os
import subprocess
import threading
import time
from ctypes import wintypes
from typing import Optional

from . import config as rec_cfg

logger = logging.getLogger(__name__)

# ---- Windows API 句柄 ----
_user32 = ctypes.windll.user32
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def get_window_title_by_pid(pid: int) -> Optional[str]:
    """通过进程 PID 查找其可见顶层窗口的标题（用于 gdigrab title= 捕获）。"""
    if not pid:
        return None
    found = {"title": None}

    def _cb(hwnd, lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True
        wnd_pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wnd_pid))
        if wnd_pid.value == pid:
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value:
                    found["title"] = buf.value
                    return False  # 找到，停止枚举
        return True

    try:
        _user32.EnumWindows(_WNDENUMPROC(_cb), 0)
    except Exception as e:
        logger.warning("EnumWindows 查找窗口标题失败 pid=%s: %s", pid, e)
    return found["title"]


def _ffmpeg_available(ffmpeg_bin: str) -> bool:
    """探测 ffmpeg 是否可调用。"""
    try:
        r = subprocess.run(
            [ffmpeg_bin, "-version"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


# 编码器探测结果缓存：避免每次录制都遍历 encoders 列表
_encoder_cache: Optional[str] = None


def _detect_encoder(ffmpeg_bin: str) -> str:
    """按顺序探测可用的视频编码器（硬件优先，软编兜底）。"""
    global _encoder_cache
    if _encoder_cache is not None:
        return _encoder_cache
    try:
        r = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        lines = r.stdout.splitlines()
    except Exception as e:
        logger.warning("编码器探测失败，使用软编 libx264: %s", e)
        _encoder_cache = rec_cfg.FALLBACK_ENCODER
        return _encoder_cache

    for enc in rec_cfg.ENCODER_PROBE_ORDER:
        # encoders 输出形如 " V..... h264_nvenc   NVIDIA NVENC H.264 encoder ..."
        for ln in lines:
            parts = ln.split()
            if len(parts) >= 2 and parts[0].startswith("V") and parts[1] == enc:
                _encoder_cache = enc
                logger.info("录屏编码器选用: %s", enc)
                return _encoder_cache
    _encoder_cache = rec_cfg.FALLBACK_ENCODER
    logger.info("未检测到硬件编码器，使用软编: %s", _encoder_cache)
    return _encoder_cache


class Recorder:
    """单场录制会话：管理 ffmpeg 进程 + 分段清理线程。

    生命周期：start() → (extract_clip 可多次) → stop()。
    一次实例对应一场比赛；新比赛应新建实例。
    """

    def __init__(
        self,
        session_dir: str,
        ffmpeg_bin: str = rec_cfg.FFMPEG_BIN,
        rollback_seconds: int = rec_cfg.DEFAULT_ROLLBACK_SECONDS,
        capture_audio: bool = rec_cfg.CAPTURE_AUDIO_DEFAULT,
        audio_device: str = "",
    ):
        self.session_dir = session_dir
        self.ffmpeg_bin = ffmpeg_bin
        self.rollback_seconds = rollback_seconds
        self.capture_audio = capture_audio and bool(audio_device)
        self.audio_device = audio_device

        self._proc: Optional[subprocess.Popen] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._window_title: Optional[str] = None
        os.makedirs(self.session_dir, exist_ok=True)

    # ---------------- 生命周期 ----------------

    @property
    def is_recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, window_title: str) -> bool:
        """启动 ffmpeg 录屏。返回是否成功启动。"""
        if self.is_recording:
            logger.warning("录屏已在进行中，忽略重复 start")
            return True

        if not _ffmpeg_available(self.ffmpeg_bin):
            logger.warning("ffmpeg 不可用 (%s)，跳过录屏。配置 FFMPEG_PATH 环境变量可启用", self.ffmpeg_bin)
            return False
        if not window_title:
            logger.warning("未获取到游戏窗口标题，跳过录屏")
            return False

        self._window_title = window_title
        encoder = _detect_encoder(self.ffmpeg_bin)
        preset = rec_cfg.ENCODER_PRESETS.get(encoder, rec_cfg.ENCODER_PRESETS[rec_cfg.FALLBACK_ENCODER])

        cmd = [
            self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "gdigrab",
            "-framerate", str(rec_cfg.FRAMERATE),
            "-draw_mouse", "1",
            "-i", f"title={window_title}",
        ]
        if self.capture_audio:
            cmd += ["-f", "dshow", "-i", f"audio={self.audio_device}"]

        cmd += ["-c:v", encoder] + preset
        if self.capture_audio:
            cmd += ["-c:a", "aac", "-b:a", "128k"]
        else:
            # 纯视频输入无音频流，显式 -an 避免无谓的音频映射警告
            cmd += ["-an"]

        # segment muxer：按 SEGMENT_SECONDS 切片，strftime 命名，每段重置时间戳
        seg_pattern = os.path.join(
            self.session_dir, "%Y%m%d%H%M%S_seg.mp4"
        )
        cmd += [
            "-f", "segment",
            "-segment_time", str(rec_cfg.SEGMENT_SECONDS),
            "-segment_format", "mp4",
            "-reset_timestamps", "1",
            "-strftime", "1",
            seg_pattern,
        ]

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=_CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            logger.warning("启动 ffmpeg 录屏失败: %s", e)
            self._proc = None
            return False

        # 启动清理线程
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="recording-cleanup"
        )
        self._cleanup_thread.start()

        logger.info(
            "录屏已启动: window=%s encoder=%s audio=%s dir=%s",
            window_title, encoder, self.capture_audio, self.session_dir,
        )
        return True

    def stop(self) -> None:
        """停止录屏并清理后台线程（保留已写入的分段文件供提取）。"""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            except Exception as e:
                logger.warning("停止 ffmpeg 异常: %s", e)
        self._proc = None

        self._stop_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2)
        self._cleanup_thread = None

    # ---------------- 分段清理 ----------------

    def _cleanup_loop(self) -> None:
        """定期删除超过保留时长的旧分段，控制磁盘占用。"""
        while not self._stop_event.is_set():
            try:
                self._purge_old_segments()
            except Exception as e:
                logger.debug("清理分段异常: %s", e)
            self._stop_event.wait(timeout=rec_cfg.CLEANUP_INTERVAL)

    def _purge_old_segments(self) -> None:
        now = time.time()
        cutoff = now - rec_cfg.RETENTION_SECONDS
        for name in os.listdir(self.session_dir):
            if not name.endswith("_seg.mp4"):
                continue
            path = os.path.join(self.session_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass

    # ---------------- 片段提取 ----------------

    def extract_clip(self, output_path: str, duration_seconds: Optional[int] = None) -> Optional[str]:
        """从最近分段中回捞指定时长的精彩片段，委托给 clip_extractor。

        Args:
            output_path: 输出 mp4 绝对路径
            duration_seconds: 回捞时长，默认使用 rollback_seconds

        Returns:
            成功返回 output_path，失败返回 None
        """
        # 延迟导入避免循环依赖
        from . import clip_extractor
        duration = duration_seconds or self.rollback_seconds
        return clip_extractor.extract_clip(
            ffmpeg_bin=self.ffmpeg_bin,
            session_dir=self.session_dir,
            output_path=output_path,
            duration_seconds=duration,
            has_audio=self.capture_audio,
        )


# Windows 下隐藏 ffmpeg 控制台窗口
if os.name == "nt":
    _CREATE_NO_WINDOW = 0x08000000
else:  # pragma: no cover
    _CREATE_NO_WINDOW = 0
