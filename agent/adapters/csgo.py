"""CSGO/CS2 死亡检测适配器。

采用双重检测策略，GSI 为主、控制台日志为辅：

1. **GSI（Game State Integration）—— 主策略**（可靠）
   - 在 CS2 cfg 目录写入 ``gamestate_integration_dieplay.cfg``
   - 启动本地 HTTP 服务器接收 CS2 推送的游戏状态 JSON
   - 通过 ``player.match_stats.deaths`` 计数器递增精确判断本地玩家死亡
   - 无需手动开启控制台日志，只要 CS2 加载了配置文件即可

2. **控制台日志解析 —— 兜底策略**
   - 当 GSI 不可用时（如旧版 CS:GO），回退到读取 console.log
   - 需要在游戏控制台执行 ``con_logfile "console.log"; con_log 1``
   - 通过正则匹配击杀行，推断本地玩家死亡

死亡事件触发后，调用 ``on_death`` 回调 → 上报后端 → 打开重定向页面。
"""
import os
import re
import logging
import threading
from datetime import datetime
from typing import Dict, Optional

from adapters.base import BaseAdapter
from gsi_server import setup_gsi, GSIServer

logger = logging.getLogger(__name__)

# ======================== 日志解析（兜底） ========================

# 由 setup-csgo.ps1 写入的"动态日志路径"文件（绝对路径）。
_LOG_PATH_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".csgo-log-path",
)

# CSGO/CS2 日志文件常见路径（按优先级尝试）
CSGO_LOG_CANDIDATES = [
    os.path.expandvars(r"%USERPROFILE%\Documents\Counter-Strike Global Offensive\csgo.log"),
    os.path.expandvars(r"%USERPROFILE%\Documents\Counter-Strike Global Offensive\console.log"),
    os.path.expandvars(r"%USERPROFILE%\Documents\csgo\csgo.log"),
    os.path.expandvars(r"%USERPROFILE%\Documents\csgo\console.log"),
    os.path.expandvars(r"%USERPROFILE%\Documents\cs2\console.log"),
    os.path.expandvars(r"%PROGRAMFILES(x86)%\Steam\logs\console.log"),
]

# 死亡事件正则（宽松匹配）
KILL_PATTERN_1 = re.compile(r"Player\s+\S+\s+killed\s+\S+\s+with", re.IGNORECASE)
KILL_PATTERN_2 = re.compile(
    r".*<.*><.*><.*>\s+killed\s+.*<.*><.*><.*>\s+with\s+.*"
)
KILL_PATTERN_3 = re.compile(
    r"killed\s+(?P<victim>.+?)\s+with\s+(?P<weapon>.+)", re.IGNORECASE
)

# 兜底关键词（中英文），命中即视为死亡事件
DEATH_KEYWORDS = [
    "you died", "you were killed", "you have died",
    "你死了", "阵亡", "已淘汰",
]

# 读取文件末尾的轮询间隔（秒）
_TAIL_INTERVAL = 0.5


class CSGOAdapter(BaseAdapter):
    """CSGO/CS2 死亡检测适配器（GSI 为主 + 日志解析兜底）。"""

    game_id = "csgo"
    game_name = "CSGO/CS2"

    def __init__(self, exe_path: str, on_death, on_event=None, on_gsi_payload=None):
        super().__init__(exe_path, on_death)
        # GSI 服务器（主策略）
        self._gsi_server: Optional[GSIServer] = None
        # 日志监听（兜底策略）
        self._log_file: Optional[str] = None
        self._offset = 0
        self._log_thread: Optional[threading.Thread] = None
        # 通用事件回调（比赛事件：回合、击杀等）
        self.on_event = on_event
        # GSI 原始帧回调（用于性能采集：FPS/卡顿检测）
        self.on_gsi_payload = on_gsi_payload

    # ---- 生命周期 ----
    def start(self) -> None:
        """启动死亡检测：优先 GSI，GSI 不可用才回退日志解析。"""
        # 1. 尝试 GSI（主策略）
        self._gsi_server = setup_gsi(
            self.exe_path, on_death=self.on_death, on_event=self.on_event,
            on_gsi_payload=self.on_gsi_payload,
        )
        gsi_ok = self._gsi_server and self._gsi_server.is_running
        if gsi_ok:
            logger.info("CS2 GSI 死亡检测已启动（主策略），跳过日志兜底")
        else:
            logger.warning(
                "GSI 启动失败，回退到控制台日志解析（兜底策略）。"
                "建议确保 CS2 已启动并通过地图加载触发 GSI 配置加载。"
            )
            # 2. GSI 不可用时才启动日志解析
            self._start_log_tailer()

        self._running = True
        self._stop_event.clear()

    def stop(self) -> None:
        """停止所有监听。"""
        self._running = False
        self._stop_event.set()

        # 停止 GSI 服务器
        if self._gsi_server:
            self._gsi_server.stop()
            self._gsi_server = None

        # 停止日志监听线程
        if self._log_thread and self._log_thread.is_alive():
            self._log_thread.join(timeout=2.0)
            self._log_thread = None

    def is_alive(self) -> bool:
        """检测是否仍在正常工作。"""
        if not self._running:
            return False
        # GSI 服务器在运行，或日志线程在运行，都算 alive
        if self._gsi_server and self._gsi_server.is_running:
            return True
        if self._log_thread and self._log_thread.is_alive():
            return True
        # 即使两者都不在，只要标记为 running 就算 alive（等待 CS2 加载 GSI 配置）
        return self._running

    # ======================== 日志解析（兜底） ========================

    def _start_log_tailer(self) -> None:
        """启动日志文件监听（兜底策略）。"""
        self._log_file = self._locate_log_file()
        if not self._log_file:
            logger.info("未找到 CSGO/CS2 控制台日志文件，跳过日志兜底监听")
            return

        if os.path.exists(self._log_file):
            logger.info("CSGO 日志文件已就绪: %s", self._log_file)
            # 从文件末尾开始读，避免历史日志触发事件
            try:
                with open(self._log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(0, 2)
                    self._offset = f.tell()
            except Exception as e:
                logger.warning("初始化日志偏移失败: %s", e)
                self._offset = 0
        else:
            logger.info("日志路径已记录但文件尚未生成: %s", self._log_file)
            self._offset = 0

        self._log_thread = threading.Thread(
            target=self._tail_loop, daemon=True, name="csgo-log-tail"
        )
        self._log_thread.start()

    def _locate_log_file(self) -> Optional[str]:
        """尝试在候选路径中定位最新的日志文件。"""
        # 1. 环境变量
        env_path = os.environ.get("CSGO_LOG_PATH", "").strip()
        if env_path and os.path.exists(env_path):
            return env_path

        # 2. 动态路径文件
        try:
            if os.path.exists(_LOG_PATH_FILE):
                with open(_LOG_PATH_FILE, "r", encoding="utf-8") as f:
                    dyn_path = f.read().strip()
                if dyn_path and os.path.exists(dyn_path):
                    return dyn_path
        except Exception as e:
            logger.warning("读取动态日志路径文件失败: %s", e)

        # 3. 内置候选列表
        candidates = [p for p in CSGO_LOG_CANDIDATES if os.path.exists(p)]
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]

    def _tail_loop(self) -> None:
        """后台循环读取日志新增行。"""
        while not self._stop_event.is_set():
            try:
                self._read_new_lines()
            except Exception as e:
                logger.warning("读取 CSGO 日志出错: %s", e)
            self._stop_event.wait(timeout=_TAIL_INTERVAL)

    def _read_new_lines(self) -> None:
        if not self._log_file or not os.path.exists(self._log_file):
            return
        try:
            size = os.path.getsize(self._log_file)
        except OSError:
            return
        if size < self._offset:
            logger.info("检测到日志文件轮转/截断，重置 offset")
            self._offset = 0
        try:
            with open(self._log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._offset)
                for line in f:
                    line = line.rstrip("\n")
                    if line:
                        self._process_line(line)
                self._offset = f.tell()
        except Exception as e:
            logger.warning("读取日志行失败: %s", e)

    def _process_line(self, line: str) -> None:
        event = self.parse_death_line(line)
        if event and self.on_death:
            try:
                self.on_death(event)
            except Exception as e:
                logger.warning("on_death 回调异常: %s", e)

    def parse_death_line(self, line: str) -> Optional[Dict]:
        """解析一行日志，返回死亡事件 dict 或 None。"""
        low = line.lower()
        for kw in DEATH_KEYWORDS:
            if kw in low:
                return self._make_event(source="keyword", keyword=kw, raw=line)
        if not (KILL_PATTERN_1.search(line) or KILL_PATTERN_2.match(line)):
            return None
        m = KILL_PATTERN_3.search(line)
        if not m:
            return None
        victim = m.group("victim").strip()
        weapon = m.group("weapon").strip()
        if self._is_local_player(victim, line):
            return self._make_event(
                source="kill", victim=victim, weapon=weapon, raw=line
            )
        return None

    def _is_local_player(self, victim: str, line: str) -> bool:
        """推断受害者是否为本地玩家（宽松版）。"""
        v = victim.lower()
        if "you" in v or "local" in v:
            return True
        return False

    def _make_event(self, **metadata) -> Dict:
        """构造死亡事件 dict。"""
        return {
            "game": self.game_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata,
        }
