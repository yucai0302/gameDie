"""自动录屏 + AI 精彩片段 —— Agent 侧独立录屏模块。

本目录是一个**可插拔**模块：即使整个目录被删除，现有 Agent 也能正常运行
（只需移除 agent/main.py 中对 RecordingController 的注入）。

模块组成：
- config.py        录屏配置常量与默认值
- recorder.py      ffmpeg 环形缓冲录屏器（segment 滑动窗口）
- clip_extractor.py 从分段中回捞指定时长的精彩片段
- controller.py    事件 → 录屏动作控制器（注入到 Agent 回调）

设计原则：
1. 任何一步失败（ffmpeg 缺失 / 窗口找不到 / 提取失败）只打 warning，不抛异常，
   不影响 GSI 采集、上报、复盘等现有功能。
2. 与现有 agent 代码零耦合：controller 仅暴露 on_event(event) 一个入口。
"""
from .controller import RecordingController

__all__ = ["RecordingController"]
