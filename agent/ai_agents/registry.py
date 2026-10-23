"""AI Agent 注册表。

集中管理所有可用的 LLM Agent 元信息，支持未来编码扩充。
新增 Agent 只需：
1. 在本目录编写继承 BaseAgent 的子类
2. 在下方 REGISTRY 中注册一条 AgentMeta
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from .base import BaseAgent, LLMClient
from .death_agent import DeathAnalystAgent
from .gear_agent import GearAdvisorAgent
from .review_agent import ReviewAgent


@dataclass
class AgentMeta:
    """单个 Agent 的元信息。"""

    agent_id: str
    name: str
    description: str
    agent_class: Type[BaseAgent]
    # 后台写死的默认生成参数（不暴露给用户配置）
    default_temperature: float = 0.7
    default_max_tokens: int = 1024


# agent_id -> 元信息
REGISTRY: Dict[str, AgentMeta] = {
    "review": AgentMeta(
        agent_id="review",
        name="复盘点评 Agent",
        description="基于比赛事件生成智能复盘点评，替代纯规则模板",
        agent_class=ReviewAgent,
        default_temperature=0.7,
        default_max_tokens=1536,
    ),
    "gear_advisor": AgentMeta(
        agent_id="gear_advisor",
        name="外设推荐 Agent",
        description="根据玩家段位与打法个性化推荐外设配置",
        agent_class=GearAdvisorAgent,
        default_temperature=0.6,
        default_max_tokens=1024,
    ),
    "death_analyst": AgentMeta(
        agent_id="death_analyst",
        name="死亡分析 Agent",
        description="分析死亡模式与原因，给出针对性改进建议",
        agent_class=DeathAnalystAgent,
        default_temperature=0.6,
        default_max_tokens=1024,
    ),
}


def list_agents() -> List[AgentMeta]:
    """返回所有已注册 Agent 的元信息。"""
    return list(REGISTRY.values())


def get_meta(agent_id: str) -> Optional[AgentMeta]:
    """按 id 查询 Agent 元信息。"""
    return REGISTRY.get(agent_id)


def build_agent(
    agent_id: str,
    api_key: str,
    model: str,
    base_url: str = "",
) -> Optional[BaseAgent]:
    """根据配置构建一个 Agent 实例。未知 id 返回 None。"""
    meta = REGISTRY.get(agent_id)
    if meta is None:
        return None
    client = LLMClient(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=meta.default_temperature,
        max_tokens=meta.default_max_tokens,
    )
    return meta.agent_class(client)
