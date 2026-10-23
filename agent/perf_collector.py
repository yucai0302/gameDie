"""性能数据采集器。

采集三类指标：
- latency:  网络延迟（ms），优先 ping 游戏实际服务器 IP（通过进程网络连接发现），
            检测加速器状态；兜底 ping Steam 公共服务器
- fps:      游戏帧率，从 GSI payload 读取或从 GSI 帧间隔估算
- stutter:  卡顿率（%），基于 GSI 回调间隔不均匀性检测

使用方式：
    collector = PerfCollector()
    collector.start()           # 启动后台采集线程
    collector.feed_gsi(payload)  # 每次收到 GSI 数据时喂入，用于帧率/卡顿检测
    metrics = collector.collect(game_pid=1234)  # 采集一次，传入游戏进程 PID 用于服务器发现
    collector.stop()
"""
import logging
import platform
import subprocess
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# CS2 常用服务器 IP（用于 ping 测试，兜底方案）
PING_TARGETS = [
    "104.16.191.197",   # Steam CDN (Cloudflare)
    "155.133.224.20",   # Steam 典中继服务器
    "23.63.73.100",     # Akamai（Steam CDN 备用）
]

# 常见游戏加速器进程名 → 友好名称
ACCELERATOR_PROCESSES = {
    # UU 加速器（网易）
    "uu.exe": "UU加速器",
    "uugameaccelerator.exe": "UU加速器",
    "uuservice.exe": "UU加速器",
    "uuserver.exe": "UU加速器",
    "uutray.exe": "UU加速器",
    # 迅游加速器
    "xunyou.exe": "迅游加速器",
    "xunyouaccel.exe": "迅游加速器",
    "xunyouservice.exe": "迅游加速器",
    # 雷神加速器
    "leigod.exe": "雷神加速器",
    "leishen.exe": "雷神加速器",
    "leigodservice.exe": "雷神加速器",
    # 腾讯加速器
    "tgpaccel.exe": "腾讯加速器",
    "qqaccel.exe": "腾讯加速器",
    # 奇游加速器
    "qiyou.exe": "奇游加速器",
    "qy.exe": "奇游加速器",
    # 海豚加速器
    "haitun.exe": "海豚加速器",
    # AK 加速器
    "akaccel.exe": "AK加速器",
    # 小黑盒加速器
    "xiaohei.exe": "小黑盒加速器",
    # NN 加速器
    "nn.exe": "NN加速器",
}

# 私有/本地 IP 前缀，发现游戏服务器 IP 时排除
_PRIVATE_IP_PREFIXES = ("127.", "192.168.", "10.", "169.254.", "172.16.", "172.17.",
                        "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
                        "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                        "172.30.", "172.31.", "::1", "fe80:", "0.0.0.0")

# GSI 帧间隔阈值（ms）：超过此值视为一次卡顿
STUTTER_THRESHOLD_MS = 50.0

# FPS 计算窗口：最近 N 个 GSI 帧的时间差
FPS_WINDOW_SIZE = 30


class PerfCollector:
    """性能数据采集器。"""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # GSI 帧时间戳列表（用于帧率/卡顿计算）
        self._gsi_timestamps: List[float] = []
        self._gsi_lock = threading.Lock()
        self._gsi_fps: Optional[float] = None
        self._gsi_stutter_pct: float = 0.0

        # 缓存最近一次 ping 结果
        self._last_latency: Optional[float] = None
        # 缓存最近一次加速器检测结果
        self._last_accelerator: Optional[str] = None
        # 缓存最近一次游戏服务器 IP
        self._last_server_ip: Optional[str] = None

    # ---- 加速器检测 ----
    def detect_accelerator(self) -> Optional[str]:
        """扫描运行中的进程，检测是否开了游戏加速器。

        Returns:
            检测到的加速器友好名称（如 "UU加速器"），未检测到返回 None。
        """
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                name = (p.info.get("name") or "").lower()
                if name in ACCELERATOR_PROCESSES:
                    self._last_accelerator = ACCELERATOR_PROCESSES[name]
                    return self._last_accelerator
        except Exception as e:
            logger.debug("加速器进程扫描异常: %s", e)
        self._last_accelerator = None
        return None

    # ---- 游戏服务器 IP 发现 ----
    def _get_game_server_ip(self, game_pid: Optional[int]) -> Optional[str]:
        """从游戏进程的网络连接中发现游戏服务器 IP。

        通过 psutil 获取进程的 UDP/TCP 远程连接地址，
        排除私有/本地 IP，返回第一个公网远程 IP。

        Args:
            game_pid: 游戏进程 PID

        Returns:
            游戏服务器 IP 字符串，未找到返回 None
        """
        if not game_pid:
            return None
        try:
            import psutil
            import socket
            proc = psutil.Process(game_pid)
            connections = proc.net_connections(kind="inet")
            for conn in connections:
                raddr = conn.raddr
                if not raddr:
                    continue
                ip = raddr[0] if isinstance(raddr, tuple) else str(raddr)
                # 排除私有/本地 IP
                if ip and not ip.startswith(_PRIVATE_IP_PREFIXES):
                    self._last_server_ip = ip
                    return ip
        except Exception as e:
            logger.debug("获取游戏服务器 IP 失败: %s", e)
        return None

    # ---- GSI 帧率/卡顿检测 ----
    def feed_gsi(self, _payload: Optional[dict] = None) -> None:
        """每次收到 GSI 数据时调用，记录时间戳用于帧率/卡顿计算。"""
        now = time.time()
        with self._gsi_lock:
            self._gsi_timestamps.append(now)
            # 保持窗口大小
            if len(self._gsi_timestamps) > FPS_WINDOW_SIZE * 2:
                self._gsi_timestamps = self._gsi_timestamps[-FPS_WINDOW_SIZE * 2 :]

            # 计算帧率
            if len(self._gsi_timestamps) >= 2:
                window = self._gsi_timestamps[-FPS_WINDOW_SIZE:]
                duration = window[-1] - window[0]
                if duration > 0:
                    self._gsi_fps = (len(window) - 1) / duration

            # 计算卡顿率
            if len(self._gsi_timestamps) >= 3:
                intervals = []
                for i in range(1, len(self._gsi_timestamps)):
                    dt = (self._gsi_timestamps[i] - self._gsi_timestamps[i - 1]) * 1000
                    intervals.append(dt)
                stutter_count = sum(1 for dt in intervals if dt > STUTTER_THRESHOLD_MS)
                self._gsi_stutter_pct = round(stutter_count / len(intervals) * 100, 1)

    # ---- 网络延迟检测 ----
    def _ping_once(self, target: str) -> Optional[float]:
        """执行一次 ping，返回延迟 ms。"""
        is_win = platform.system() == "Windows"
        try:
            cmd = ["ping", "-n", "1", "-w", "2000", target] if is_win else ["ping", "-c", "1", "-W", "2", target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = result.stdout
            if is_win:
                # Windows: "时间=23ms" or "time=23ms"
                import re
                match = re.search(r"(?:时间|time)[=<](\d+)ms", output)
                if match:
                    return float(match.group(1))
            else:
                # Linux/macOS: "time=23.4 ms"
                import re
                match = re.search(r"time=([\d.]+)\s*ms", output)
                if match:
                    return float(match.group(1))
        except Exception as e:
            logger.debug("ping %s 失败: %s", target, e)
        return None

    def measure_latency(self, game_pid: Optional[int] = None) -> Optional[float]:
        """测量网络延迟，返回 ms。

        优先级：
        1. 若传入 game_pid，通过进程网络连接发现游戏服务器 IP，ping 游戏服务器（最能反映实际游戏延迟）
        2. 兜底：动态解析 Steam 域名并 ping
        3. 兜底：ping PING_TARGETS 中的 Steam CDN IP
        """
        # 优先：从游戏进程网络连接发现游戏服务器 IP
        if game_pid:
            server_ip = self._get_game_server_ip(game_pid)
            if server_ip:
                lat = self._ping_once(server_ip)
                if lat is not None:
                    self._last_latency = lat
                    return lat

        # 兜底：ping Steam 公共服务器
        targets = list(PING_TARGETS)
        # 动态解析 Steam 域名，获取真实可达 IP
        for domain in ("store.steampowered.com", "api.steampowered.com"):
            try:
                import socket
                ip = socket.gethostbyname(domain)
                if ip and ip not in targets:
                    targets.insert(0, ip)
            except Exception:
                pass

        for target in targets:
            lat = self._ping_once(target)
            if lat is not None:
                self._last_latency = lat
                return lat
        return self._last_latency

    # ---- 采集 ----
    def collect(self, game_pid: Optional[int] = None) -> Dict[str, Optional[float]]:
        """采集一次全部指标。

        Args:
            game_pid: 当前游戏进程 PID，用于发现游戏服务器 IP 和获取真实游戏延迟。
                      传入后 latency 会优先 ping 游戏服务器而非 Steam CDN。

        Returns:
            {
                "latency": ...,       # 网络延迟 ms
                "fps": ...,           # 游戏帧率
                "stutter": ...,       # 卡顿率 %
                "accelerator": ...,   # 加速器名称（如 "UU加速器"），无则 None
                "server_ip": ...,     # 游戏服务器 IP（如 "1.2.3.4"），未发现则 None
            }
        """
        accelerator = self.detect_accelerator()
        latency = self.measure_latency(game_pid=game_pid)

        with self._gsi_lock:
            fps = self._gsi_fps
            stutter = self._gsi_stutter_pct

        return {
            "latency": latency,
            "fps": fps,
            "stutter": stutter if fps is not None else None,
            "accelerator": accelerator,
            "server_ip": self._last_server_ip,
        }

    # ---- 后台采集线程 ----
    def start(self, interval: float = 10.0) -> None:
        """启动后台采集线程。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(interval,), daemon=True, name="perf-collector"
        )
        self._thread.start()
        logger.info("性能采集器已启动，间隔 %.0fs", interval)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _loop(self, interval: float) -> None:
        while self._running:
            time.sleep(interval)
