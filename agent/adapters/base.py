"""游戏适配器基类。"""
import threading
from typing import Callable, Dict, Optional


class BaseAdapter:
    """游戏适配器基类。子类需实现 start/stop/parse_death_line。

    子类需要设置类属性 game_id 与 game_name，并在 start 中启动监听，
    在 stop 中清理资源。parse_death_line 用于解析一行日志/输出。
    """

    game_id: str = ""
    game_name: str = ""

    def __init__(self, exe_path: str, on_death: Callable[[Dict], None]):
        self.exe_path = exe_path
        # 死亡回调，传入 {"game":..., "timestamp":..., "metadata":...}
        self.on_death = on_death
        # 通用事件回调（比赛事件：回合、击杀等），传入 {"event_type":..., "timestamp":..., "data":...}
        self.on_event: Optional[Callable[[Dict], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """启动日志监听线程。子类可覆盖。"""
        self._running = True

    def stop(self) -> None:
        """停止并清理。子类可覆盖。"""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def is_alive(self) -> bool:
        """进程/监听是否还在运行。"""
        return self._running

    def parse_death_line(self, line: str) -> Optional[Dict]:
        """解析一行日志，返回死亡事件 dict 或 None。子类实现。

        返回结构：{"game":..., "timestamp":..., "metadata":...}
        """
        return None
