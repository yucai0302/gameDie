"""Windows 系统音量读取与调节。

通过 Windows Core Audio API (pycaw) 读取/设置系统主音量。
如果 pycaw 不可用，回退到 ctypes 调用。
"""
import logging
import platform

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        _PYCAW_AVAILABLE = True
    except ImportError:
        _PYCAW_AVAILABLE = False
        logger.info("pycaw 未安装，音量读取功能不可用")
else:
    _PYCAW_AVAILABLE = False


def get_volume() -> int:
    """读取当前系统主音量（0~100），失败返回 -1。"""
    if not _PYCAW_AVAILABLE:
        return -1
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        # scalar volume (0.0 ~ 1.0)
        current = volume.GetMasterVolumeLevelScalar()
        return round(current * 100)
    except Exception as e:
        logger.warning("读取音量失败: %s", e)
        return -1


def set_volume(vol: int) -> bool:
    """设置系统主音量（0~100），返回是否成功。"""
    if not _PYCAW_AVAILABLE:
        return False
    vol = max(0, min(100, vol))
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(vol / 100.0, None)
        return True
    except Exception as e:
        logger.warning("设置音量失败: %s", e)
        return False
