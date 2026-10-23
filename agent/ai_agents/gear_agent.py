"""外设推荐 Agent：个性化外设配置推荐增强。

在 ai_gear_advisor.generate_recommendation 中被调用，当该 Agent 启用且
配置了 Key 时，用 LLM 生成更贴合玩家段位与打法的个性化推荐总结。
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import BaseAgent


class GearAdvisorAgent(BaseAgent):
    agent_id = "gear_advisor"
    name = "外设推荐 Agent"
    description = "根据玩家段位与打法个性化推荐外设配置"

    def invoke(self, context: Dict[str, Any]) -> str:
        """context: {config: dict, summary: str, edpi_analysis: str}。"""
        config = context.get("config", {}) or {}
        rule_summary = context.get("summary", "") or ""
        rule_edpi = context.get("edpi_analysis", "") or ""

        system = (
            "你是一名外设配置顾问，精通 CS2 职业选手外设参数。"
            "根据玩家配置输出个性化建议，中文，仅输出文本。"
        )
        user = (
            f"玩家配置：{json.dumps(config, ensure_ascii=False)}\n"
            f"规则引擎总结：{rule_summary}\n"
            f"eDPI 分析：{rule_edpi}\n"
            "请输出 100-200 字的个性化外设建议，强调与该玩家段位/打法的匹配，"
            "可给出具体的 DPI、灵敏度、触发距离调整方向。"
        )
        return self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
