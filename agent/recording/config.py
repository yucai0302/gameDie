"""录屏模块配置常量。

所有路径默认放在 agent 临时目录下，避免污染项目其它部分。
运行时实际使用的回捞时长 / 编码器等以「后端 media_settings」为准，
controller 会在每场比赛开始时拉取并覆盖这里的默认值。
"""
import os

# ---- 临时录屏目录（环形缓冲分段文件存放处）----
# 每场比赛一个子目录，比赛结束后整目录清理
RECORDING_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs", "recording",
)

# ---- 环形缓冲参数 ----
# 单个分段时长（秒）。segment muxer 每段写一个文件
SEGMENT_SECONDS = 5
# 分段保留时长（秒）。超过该时长的旧分段被清理线程删除，
# 需 ≥ 回捞时长，留足余量避免在提取时被删
RETENTION_SECONDS = 90
# 清理线程检查间隔（秒）
CLEANUP_INTERVAL = 10

# ---- 默认回捞时长（秒），可被后端 media_settings 覆盖 ----
DEFAULT_ROLLBACK_SECONDS = 30

# ---- 视频编码参数 ----
# 自动检测硬件编码器顺序：nvenc → qsv → amf → 软编
ENCODER_PROBE_ORDER = ["h264_nvenc", "h264_qsv", "h264_amf", "libx264"]
# 各编码器的预设参数
ENCODER_PRESETS = {
    "h264_nvenc": ["-preset", "p4", "-b:v", "4M", "-rc", "cbr"],
    "h264_qsv": ["-preset", "veryfast", "-b:v", "4M"],
    "h264_amf": ["-quality", "speed", "-b:v", "4M"],
    "libx264": ["-preset", "ultrafast", "-b:v", "4M", "-tune", "zerolatency"],
}
# 备选软编（探测失败兜底）
FALLBACK_ENCODER = "libx264"

# 帧率与分辨率
FRAMERATE = 30

# ---- 音频 ----
# 是否尝试采集系统音频（WASAPI loopback）。采集失败自动降级为纯视频
CAPTURE_AUDIO_DEFAULT = True

# ---- ffmpeg 可执行文件路径 ----
# 优先从环境变量 FFMPEG_PATH 读取，其次用 PATH 上的 ffmpeg
FFMPEG_BIN = os.environ.get("FFMPEG_PATH", "ffmpeg")

# ---- 片段上传 ----
# 单个片段上传失败的重试次数
UPLOAD_RETRIES = 2
# 上传超时（秒）——视频文件可能较大
UPLOAD_TIMEOUT = 60.0

# ---- 精彩事件判定 ----
# 单回合击杀数达到该值即触发多杀回捞
MULTIKILL_THRESHOLD = 3
# ACE 阈值
ACE_THRESHOLD = 5
