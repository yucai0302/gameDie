"""进程检测：用 psutil 遍历所有进程，匹配游戏进程名。

提供简单的时间缓存，避免在单次轮询周期内重复遍历全部进程。
"""
import time
import logging
from typing import Dict, List, Optional

import psutil

from config import GAME_REGISTRY

logger = logging.getLogger(__name__)

# 进程快照缓存：避免一次轮询内多次调用都去遍历全部进程
_process_snapshot: Optional[List[Dict]] = None
_snapshot_ts: float = 0.0
# 缓存有效期（秒）
_CACHE_TTL = 0.5


def _get_process_snapshot() -> List[Dict]:
    """获取进程快照（带缓存）。"""
    global _process_snapshot, _snapshot_ts
    now = time.time()
    if _process_snapshot is not None and (now - _snapshot_ts) < _CACHE_TTL:
        return _process_snapshot
    procs: List[Dict] = []
    # process_iter 配合 attrs 参数会自动捕获 AccessDenied 等异常，info 中对应字段为 None
    for p in psutil.process_iter(["pid", "name", "exe"]):
        procs.append(p.info)
    _process_snapshot = procs
    _snapshot_ts = now
    return procs


def list_game_processes() -> List[Dict]:
    """返回正在运行的游戏列表。

    每项结构：{"game_id": "csgo", "pid": 1234, "exe_path": "C:/..."}
    """
    result: List[Dict] = []
    snapshot = _get_process_snapshot()
    for game_id, info in GAME_REGISTRY.items():
        # 进程名统一小写匹配
        proc_names = {n.lower() for n in info["process_names"]}
        for pinfo in snapshot:
            name = (pinfo.get("name") or "").lower()
            if name and name in proc_names:
                result.append({
                    "game_id": game_id,
                    "pid": pinfo.get("pid"),
                    "exe_path": pinfo.get("exe") or "",
                })
                # 同一游戏的多个进程只记录一次，跳出内层循环
                break
    return result


def get_current_game() -> Optional[Dict]:
    """返回当前正在运行的游戏（如有多个取第一个）。"""
    games = list_game_processes()
    return games[0] if games else None
