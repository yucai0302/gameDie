"""Apex Legends 适配器（占位实现）。

Apex 有 r5apex.log 日志，但内容有限，基本不包含可解析的死亡信息。
死亡检测建议使用 OCR 识别 "YOU DIED" / "已被击杀" 等屏幕文本，
或通过解析 Respawn 的回放/网络包（实现难度大，不推荐）。
"""
import logging

from adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class ApexAdapter(BaseAdapter):
    """Apex 占位适配器：仅上报运行状态，不识别死亡事件。"""

    game_id = "apex"
    game_name = "Apex Legends"

    def start(self) -> None:
        logger.info("[Apex Adapter] 该游戏暂无日志解析能力，仅上报运行状态")
        self._running = True

    def stop(self) -> None:
        self._running = False
