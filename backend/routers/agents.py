"""AI Agent 配置查询与连通性测试路由。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

import database
from agent.ai_agents import list_agents
from agent.ai_agents.base import LLMClient

router = APIRouter()


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str
    enabled: bool


class AgentsListResponse(BaseModel):
    agents: List[AgentInfo]
    llm_configured: bool


class AgentTestResult(BaseModel):
    ok: bool
    message: str


@router.get("/agents", response_model=AgentsListResponse)
def get_agents() -> AgentsListResponse:
    """列出所有 AI Agent 及其启用状态，并返回共享 LLM 是否已配置。"""
    config = database.load_config()
    ai_agents = config.get("ai_agents", {})
    llm = config.get("llm", {})
    result = []
    for meta in list_agents():
        toggle = ai_agents.get(meta.agent_id, {})
        result.append(
            AgentInfo(
                agent_id=meta.agent_id,
                name=meta.name,
                description=meta.description,
                enabled=bool(toggle.get("enabled", False)),
            )
        )
    return AgentsListResponse(
        agents=result,
        llm_configured=bool(llm.get("api_key")) and bool(llm.get("model")),
    )


@router.post("/agents/test", response_model=AgentTestResult)
def test_llm() -> AgentTestResult:
    """用共享 LLM 配置测试连通性。"""
    config = database.load_config()
    llm = config.get("llm", {})
    client = LLMClient(
        api_key=llm.get("api_key", ""),
        model=llm.get("model", ""),
        base_url=llm.get("base_url", ""),
    )
    ok, msg = client.test_connection()
    return AgentTestResult(ok=ok, message=msg)
