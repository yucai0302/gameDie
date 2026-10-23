"""死亡分析 Agent：分析死亡模式与原因，给出改进建议。

在 ai_review.generate_review 中被调用，当该 Agent 启用且配置了 Key 时，
用 LLM 增强规则引擎生成的死亡分析草稿。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import BaseAgent


class DeathAnalystAgent(BaseAgent):
    agent_id = "death_analyst"
    name = "死亡分析 Agent"
    description = "分析死亡模式与原因，给出改进建议"

    def invoke(self, context: Dict[str, Any]) -> str:
        """context: {match: dict, events: List[dict], draft: str}。"""
        match = context.get("match", {}) or {}
        events = context.get("events", []) or []
        draft = context.get("draft", "") or ""

        system = (
            "你是一名 CS2 数据分析师，专注分析玩家死亡模式。"
            "根据数据给出简洁、可执行的改进建议，中文输出，仅输出文本。"
        )
        rounds = sum(1 for e in events if e.get("event_type") == "round_end")
        kills = sum(1 for e in events if e.get("event_type") == "kill")
        deaths = sum(1 for e in events if e.get("event_type") == "death")
        death_events = [e for e in events if e.get("event_type") == "death"][:20]
        user = (
            f"地图：{match.get('map_name', '')}，回合数 {rounds}，"
            f"击杀 {kills} / 死亡 {deaths}。\n"
            f"死亡事件样本（含武器、护甲信息）：{json.dumps(death_events, ensure_ascii=False)}\n"
            f"规则引擎草稿：{draft}\n"
            "请输出 100-200 字的死亡分析，指出死亡模式、死亡时手持武器与护甲情况、"
            "高风险回合与具体改进建议。"
        )
        return self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
