"""守望先锋 2 适配器（占位实现）。

守望先锋 2 没有可用的本地日志，死亡事件无法通过日志解析。
建议使用 OCR 识别死亡回放界面（屏幕中央大字 "DEAD" / 阵亡提示），
或通过游戏内录像文件解析。
"""
import logging

from adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class OverwatchAdapter(BaseAdapter):
    """守望先锋 2 占位适配器：仅上报运行状态，不识别死亡事件。"""

    game_id = "overwatch"
    game_name = "Overwatch 2"

    def start(self) -> None:
        logger.info("[Overwatch Adapter] 该游戏暂无日志解析能力，仅上报运行状态")
        self._running = True

    def stop(self) -> None:
        self._running = False
