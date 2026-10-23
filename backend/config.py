"""应用配置：端口、数据库路径、时区、默认配置项。"""
from __future__ import annotations

from pathlib import Path

# 服务监听
HOST = "0.0.0.0"
PORT = 8000

# 项目根目录与数据库路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "gamedie.db"

# 统一时区
TIMEZONE = "Asia/Shanghai"

# 默认支持的游戏列表（id / 显示名 / 进程名）
DEFAULT_GAMES = [
    {"id": "csgo", "name": "CSGO / CS2", "process_names": ["csgo.exe", "cs2.exe"]},
    {"id": "pubg", "name": "PUBG", "process_names": ["TslGame.exe"]},
    {"id": "apex", "name": "Apex Legends", "process_names": ["r5apex.exe"]},
    {"id": "overwatch", "name": "守望先锋 2", "process_names": ["Overwatch 2.exe"]},
]

# 默认重定向与预设站点
DEFAULT_REDIRECT_URL = "https://www.douyin.com"
DEFAULT_PRESETS = [
    {"name": "抖音", "url": "https://www.douyin.com", "icon": "douyin"},
    {"name": "哔哩哔哩", "url": "https://www.bilibili.com", "icon": "bilibili"},
    {"name": "YouTube", "url": "https://www.youtube.com", "icon": "youtube"},
]

# 默认 Agent 行为
DEFAULT_AGENT = {
    "polling_interval": 2.0,
    "screenshot_enabled": False,
}

# 共享 LLM 模型配置（所有 AI Agent 共用，用户在页面填写一次）
DEFAULT_LLM = {
    "api_key": "",
    "model": "",
    "base_url": "",
}

# 默认 AI Agent 开关（仅 enabled，模型配置走共享的 llm）
DEFAULT_AI_AGENTS = {
    "review": {"enabled": False},
    "gear_advisor": {"enabled": False},
    "death_analyst": {"enabled": False},
}

# 自动返回游戏配置
DEFAULT_OVERLAY = {
    "auto_return_enabled": False,  # 默认关闭，避免改变既有行为
    "auto_return_seconds": 30,     # 兜底超时秒数（未检测到复活时强制返回）
    "auto_return_on_respawn": True,  # 检测到复活/新回合时立即返回（事件驱动）
}

# 完整默认配置（写入 config 表单记录）
DEFAULT_CONFIG = {
    "redirect_url": DEFAULT_REDIRECT_URL,
    "presets": DEFAULT_PRESETS,
    "agent": DEFAULT_AGENT,
    "llm": DEFAULT_LLM,
    "ai_agents": DEFAULT_AI_AGENTS,
    "overlay": DEFAULT_OVERLAY,
}

# config 表中的主键（单行配置存储）
CONFIG_KEY = "app"
