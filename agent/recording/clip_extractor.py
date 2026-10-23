"""片段回捞：从环形缓冲的分段文件中拼出指定时长的精彩片段。

独立于 Recorder 之外，便于单独测试与替换回捞策略。
策略：选取最近 N 秒的分段 → 写 concat 列表 → 重编码为独立 mp4。
重编码（而非 -c copy）更稳健，能容忍正在写入的末段。
"""
import logging
import os
import subprocess
from typing import List, Optional

from . import config as rec_cfg

logger = logging.getLogger(__name__)

# Windows 下隐藏 ffmpeg 控制台窗口
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def list_segments(session_dir: str) -> List[str]:
    """返回会话目录下按时间排序的分段文件绝对路径。"""
    try:
        names = [n for n in os.listdir(session_dir) if n.endswith("_seg.mp4")]
    except OSError:
        return []
    names.sort()
    return [os.path.join(session_dir, n) for n in names]


def select_recent_segments(segments: List[str], duration_seconds: int) -> List[str]:
    """选取覆盖 duration_seconds 秒所需的最近分段（多取 1 段余量）。"""
    if not segments:
        return []
    need = max(1, int(duration_seconds // rec_cfg.SEGMENT_SECONDS) + 1)
    return segments[-need:]


def extract_clip(
    ffmpeg_bin: str,
    session_dir: str,
    output_path: str,
    duration_seconds: int,
    has_audio: bool,
) -> Optional[str]:
    """从最近分段中回捞一个精彩片段。

    Args:
        ffmpeg_bin: ffmpeg 可执行文件路径
        session_dir: 会话目录（含 _seg.mp4 分段）
        output_path: 输出 mp4 路径
        duration_seconds: 回捞时长
        has_audio: 源是否含音频（决定输出是否带音频流）

    Returns:
        成功返回 output_path，失败返回 None
    """
    segments = list_segments(session_dir)
    selected = select_recent_segments(segments, duration_seconds)
    if not selected:
        logger.warning("无可用分段，无法提取片段")
        return None

    list_path = os.path.join(session_dir, "_concat_list.txt")
    try:
        with open(list_path, "w", encoding="utf-8") as f:
            for seg in selected:
                safe = seg.replace("\\", "/").replace("'", r"'\''")
                f.write(f"file '{safe}'\n")
    except Exception as e:
        logger.warning("写入 concat 列表失败: %s", e)
        return None

    cmd = [
        ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-t", str(duration_seconds),
        "-c:v", rec_cfg.FALLBACK_ENCODER,
        "-preset", "ultrafast",
        "-movflags", "+faststart",
    ]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-an"]
    cmd.append(output_path)

    try:
        r = subprocess.run(
            cmd, capture_output=True, timeout=60,
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception as e:
        logger.warning("提取片段执行失败: %s", e)
        return None
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "ignore")[-300:] if r.stderr else ""
        logger.warning("提取片段失败 (rc=%s): %s", r.returncode, err)
        return None

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
        logger.warning("提取片段输出无效: %s", output_path)
        return None

    logger.info("片段已提取: %s <- %d 段 (%ss)", output_path, len(selected), duration_seconds)
    return output_path
