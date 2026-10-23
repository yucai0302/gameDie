"""Windows 窗口管理：最小化游戏窗口，让浏览器显示在前台。

使用 ctypes 调用 user32 API，通过进程 PID 查找并最小化游戏窗口。
适用于窗口化 / 无边框窗口模式；独占全屏可能需要切换为无边框窗口。
"""
import ctypes
import logging
import time
from ctypes import wintypes
from typing import Optional

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32

# ShowWindow 常量
SW_MINIMIZE = 6
SW_FORCEMINIMIZE = 11
SW_RESTORE = 9

# 枚举窗口回调类型
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _find_window_by_pid(pid: int) -> Optional[int]:
    """通过进程 ID 查找可见的顶层窗口句柄。"""
    found_hwnd = None

    def _enum_callback(hwnd, lparam):
        nonlocal found_hwnd
        # 只处理可见窗口
        if not user32.IsWindowVisible(hwnd):
            return True  # 继续枚举
        wnd_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wnd_pid))
        if wnd_pid.value == pid:
            found_hwnd = hwnd
            return False  # 找到了，停止枚举
        return True

    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)
    return found_hwnd


def minimize_window_by_pid(pid: int) -> bool:
    """最小化指定进程的窗口。

    Args:
        pid: 游戏进程 ID

    Returns:
        是否成功最小化
    """
    hwnd = _find_window_by_pid(pid)
    if not hwnd:
        logger.warning("未找到 PID=%s 的可见窗口，无法最小化", pid)
        return False

    # 先尝试 SW_FORCEMINIMIZE（即使窗口不属于当前线程也能最小化）
    ok = user32.ShowWindow(hwnd, SW_FORCEMINIMIZE)
    if not ok:
        # 回退到 SW_MINIMIZE
        ok = user32.ShowWindow(hwnd, SW_MINIMIZE)

    if ok:
        logger.info("已最小化游戏窗口 PID=%s hwnd=%s", pid, hwnd)
    else:
        logger.warning("最小化窗口失败 PID=%s hwnd=%s", pid, hwnd)
    return bool(ok)


def minimize_game_and_open_browser(pid: int, open_browser_func, url: str) -> None:
    """最小化游戏窗口后打开浏览器。

    Args:
        pid: 游戏进程 ID
        open_browser_func: 打开浏览器的函数，接受 url 参数
        url: 要打开的 URL
    """
    # 1. 最小化游戏窗口
    if pid:
        minimize_window_by_pid(pid)
        # 等待窗口最小化动画完成，确保浏览器能显示在前台
        time.sleep(0.5)

    # 2. 打开浏览器
    open_browser_func(url)


def focus_window_by_pid(pid: int) -> bool:
    """将指定进程的窗口还原并拉到前台（自动返回游戏）。

    使用 AttachThreadInput 技巧绕过 SetForegroundWindow 的焦点限制，
    确保游戏窗口能真正被激活而非仅在任务栏闪烁。

    Args:
        pid: 游戏进程 ID

    Returns:
        是否成功聚焦
    """
    hwnd = _find_window_by_pid(pid)
    if not hwnd:
        logger.warning("未找到 PID=%s 的可见窗口，无法聚焦", pid)
        return False

    # 还原（如果被最小化）
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.1)

    # 使用 AttachThreadInput 绕过 SetForegroundWindow 限制
    fg_hwnd = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
    cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    attached = False
    if fg_tid and fg_tid != cur_tid:
        attached = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
    try:
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_tid, fg_tid, False)

    # 兜底：再次还原并尝试置顶
    user32.ShowWindow(hwnd, SW_RESTORE)
    try:
        user32.BringWindowToTop(hwnd)
    except Exception:
        pass

    logger.info("已聚焦游戏窗口 PID=%s hwnd=%s", pid, hwnd)
    return True
