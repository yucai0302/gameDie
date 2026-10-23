"""Agent 配置常量。

集中管理后端地址、轮询间隔、日志目录以及支持的游戏注册表。
所有模块通过 ``import config`` 或 ``from config import ...`` 读取这些常量。
"""
import os

# 后端服务地址
BACKEND_URL = "http://localhost:8000"

# 进程检测轮询间隔（秒）
POLLING_INTERVAL = 2.0

# 上报游戏状态间隔（秒）
HEARTBEAT_INTERVAL = 5.0

# Agent 自身日志目录（运行时自动创建）
AGENT_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 默认重定向 URL（后端未返回 / 拉取失败时使用）
DEFAULT_REDIRECT_URL = "http://localhost:8000/watch"

# 网络请求超时（秒）
REQUEST_TIMEOUT = 3.0

# GSI（Game State Integration）HTTP 服务器配置
# CS2 会向该地址 POST 游戏状态 JSON，用于可靠检测死亡事件
GSI_HOST = "127.0.0.1"
GSI_PORT = 3100
GSI_AUTH_TOKEN = "dieplay-gsi-token"

# 支持的游戏注册表：game_id -> {name, process_names, adapter_class}
# adapter_class 用字符串形式记录（模块路径.类名），运行时动态导入，避免循环依赖
GAME_REGISTRY = {
    "csgo": {
        "name": "CSGO/CS2",
        "process_names": ["csgo.exe", "cs2.exe"],
        "adapter_class": "adapters.csgo.CSGOAdapter",
    },
    "pubg": {
        "name": "PUBG",
        "process_names": ["TslGame.exe", "PUBG.exe"],
        "adapter_class": "adapters.pubg.PUBGAdapter",
    },
    "apex": {
        "name": "Apex Legends",
        "process_names": ["r5apex.exe", "r5apex_bin.exe"],
        "adapter_class": "adapters.apex.ApexAdapter",
    },
    "overwatch": {
        "name": "Overwatch 2",
        "process_names": ["Overwatch.exe", "Overwatch2.exe"],
        "adapter_class": "adapters.overwatch.OverwatchAdapter",
    },
}
