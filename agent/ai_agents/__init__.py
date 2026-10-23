"""AI Agent 子包：LLM 驱动的智能体实现。

自包含模块（仅依赖 Python 标准库），不引用 agent 文件夹其它模块，
因此可被后端独立导入：

    from agent.ai_agents import registry, build_agent, list_agents

新增 Agent 流程：
1. 编写继承 BaseAgent 的子类（放在本目录下）
2. 在 registry.py 的 REGISTRY 中注册一条 AgentMeta
"""
from .base import BaseAgent, LLMClient
from .registry import (
    REGISTRY,
    AgentMeta,
    list_agents,
    get_meta,
    build_agent,
)

__all__ = [
    "BaseAgent",
    "LLMClient",
    "AgentMeta",
    "REGISTRY",
    "list_agents",
    "get_meta",
    "build_agent",
]
