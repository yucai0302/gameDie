"""配置相关路由：GET/PUT /api/config。"""
from __future__ import annotations

from fastapi import APIRouter

import database
from models import AppConfig, ConfigUpdateRequest

router = APIRouter()


@router.get("/config", response_model=AppConfig)
def get_config() -> AppConfig:
    """获取当前配置。"""
    data = database.load_config()
    return AppConfig(**data)


@router.put("/config", response_model=AppConfig)
def update_config(payload: ConfigUpdateRequest) -> AppConfig:
    """部分更新配置，返回完整配置回显。"""
    current = database.load_config()
    update = payload.model_dump(exclude_unset=True)
    # 合并 agent 子字段，避免整体覆盖
    if "agent" in update and update["agent"] is not None:
        merged_agent = dict(current.get("agent", {}))
        merged_agent.update(update["agent"])
        update["agent"] = merged_agent
    # 合并 llm 子字段，避免整体覆盖
    if "llm" in update and update["llm"] is not None:
        merged_llm = dict(current.get("llm", {}))
        for k, v in update["llm"].items():
            if v is not None:
                merged_llm[k] = v
        update["llm"] = merged_llm
    # 合并 ai_agents 各 Agent 开关，按 agent_id 逐项合并
    if "ai_agents" in update and update["ai_agents"] is not None:
        merged_ai = dict(current.get("ai_agents", {}))
        for aid, cfg in update["ai_agents"].items():
            existing = dict(merged_ai.get(aid, {}))
            for k, v in cfg.items():
                if v is not None:
                    existing[k] = v
            merged_ai[aid] = existing
        update["ai_agents"] = merged_ai
    # 合并 overlay 子字段，避免整体覆盖
    if "overlay" in update and update["overlay"] is not None:
        merged_overlay = dict(current.get("overlay", {}))
        for k, v in update["overlay"].items():
            if v is not None:
                merged_overlay[k] = v
        update["overlay"] = merged_overlay
    current.update(update)
    database.save_config(current)
    return AppConfig(**current)
