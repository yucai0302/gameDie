"""打开默认浏览器到指定 URL；监听浏览器关闭以计算观看时长。

由于准确监听浏览器关闭非常复杂，默认采用「简单模式」：
- 每次死亡都打开新标签页（不主动关闭旧的）
- 观看时长用「下一次死亡 / 游戏退出 的时间 - 上次死亡时间」近似

「准确模式」实现思路（可选，本模块未默认启用）：
- 通过 ctypes 调用 Windows user32 API 获取浏览器窗口句柄（HWND）
- 轮询 IsWindow(HWND) / GetWindowText，当窗口消失即视为关闭
- 或监听 Windows UI Automation 的 WindowClosed 事件
由于不同浏览器标签页生命周期难以统一捕获，准确模式实现成本高、可靠性低，
故默认使用简单模式。
"""
import logging
import webbrowser
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 全局当前观看会话状态
# 结构: {"session_id":..., "start_time":..., "url":..., "alive":True}
current_watch_session: Optional[Dict] = None


def open_browser(url: str) -> Dict:
    """用默认浏览器打开 URL，返回 {"start_time": "<ISO8601>"}。"""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning("打开浏览器失败: %s", e)
    start_time = datetime.utcnow().isoformat() + "Z"
    return {"start_time": start_time}


def start_watch_session(session_id: str, url: str) -> Dict:
    """开始一个新的观看会话。

    如果当前已有进行中的会话，先结束并上报旧的，再开新的。
    """
    global current_watch_session
    if current_watch_session and current_watch_session.get("alive"):
        logger.info("已有观看会话进行中，先结束旧会话")
        end_watch_session()
    info = open_browser(url)
    current_watch_session = {
        "session_id": session_id,
        "start_time": info["start_time"],
        "url": url,
        "alive": True,
    }
    logger.info("开始观看会话 session_id=%s url=%s", session_id, url)
    return current_watch_session


def end_watch_session(reporter=None) -> Dict:
    """结束当前观看会话，计算时长并上报。

    Args:
        reporter: 可选的 BackendClient 实例，传入则上报观看记录。

    返回刚结束的会话信息（无会话时返回 {}）。
    """
    global current_watch_session
    if not current_watch_session:
        return {}
    session = current_watch_session
    end_time = datetime.utcnow().isoformat() + "Z"
    duration = 0
    try:
        # 延迟导入避免循环依赖
        from dateutil.parser import isoparse

        start = isoparse(session["start_time"])
        end = isoparse(end_time)
        duration = max(0, int((end - start).total_seconds()))
    except Exception as e:
        logger.warning("计算观看时长失败: %s", e)
        duration = 0

    if reporter is not None:
        reporter.report_watch(
            session_id=session["session_id"],
            start_time=session["start_time"],
            end_time=end_time,
            duration_seconds=duration,
            url=session["url"],
        )

    session["alive"] = False
    logger.info(
        "结束观看会话 session_id=%s duration=%ss", session["session_id"], duration
    )
    current_watch_session = None
    return session
