"""PUBG 适配器（占位实现）。

PUBG 没有官方日志输出，无法通过日志解析死亡事件。
建议后续扩展：用 OCR 识别屏幕上的 "你已淘汰" / "YOU DIED" 文本，
或读取游戏回放文件解析淘汰事件。
"""
import logging

from adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class PUBGAdapter(BaseAdapter):
    """PUBG 占位适配器：仅上报运行状态，不识别死亡事件。"""

    game_id = "pubg"
    game_name = "PUBG"

    def start(self) -> None:
        logger.info("[PUBG Adapter] 该游戏暂无日志解析能力，仅上报运行状态")
        self._running = True

    def stop(self) -> None:
        self._running = False
