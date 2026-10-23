"""复盘点评 Agent：基于比赛事件生成智能复盘点评文本。

在 ai_review.generate_review 中被调用，当该 Agent 启用且配置了 Key 时，
用 LLM 增强规则引擎生成的草稿，生成更自然专业的综合复盘点评。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import BaseAgent


class ReviewAgent(BaseAgent):
    agent_id = "review"
    name = "复盘点评 Agent"
    description = "基于比赛事件生成智能复盘点评"

    def invoke(self, context: Dict[str, Any]) -> str:
        """context: {match: dict, events: List[dict], draft: dict}。"""
        match = context.get("match", {}) or {}
        events = context.get("events", []) or []
        draft = context.get("draft", {}) or {}

        system = (
            "你是一名 CS2 职业复盘分析师。根据比赛事件数据生成专业、简洁的中文复盘点评。"
            "只输出分析文本，不要输出 JSON 或代码块。"
        )
        summary = self._summarize(events)
        user = (
            f"比赛信息：地图 {match.get('map_name', '')}，"
            f"比分 CT {match.get('score_ct', 0)} : {match.get('score_t', 0)} T，"
            f"击杀 {summary['kills']} / 死亡 {summary['deaths']} / 回合 {summary['rounds']}。\n"
            f"规则引擎草稿（参考，可改写增强）：\n"
            f"- MVP: {draft.get('mvp', '')}\n"
            f"- 最佳操作: {draft.get('best_play', '')}\n"
            f"- 最大失误: {draft.get('biggest_mistake', '')}\n"
            f"- 武器使用: {draft.get('weapon_analysis', '')}\n"
            f"- 经济分析: {draft.get('economy_analysis', '')}\n"
            f"- 购买建议: {draft.get('purchase_advice', '')}\n"
            f"- AI点评: {draft.get('ai_commentary', '')}\n"
            "请输出一段 150-300 字的综合复盘点评，涵盖整体表现、高光时刻、"
            "武器使用、关键失误与可执行的购买/战术建议，语气专业且口语化。"
        )
        return self.llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])

    @staticmethod
    def _summarize(events: List[dict]) -> Dict[str, int]:
        kills = sum(1 for e in events if e.get("event_type") == "kill")
        deaths = sum(1 for e in events if e.get("event_type") == "death")
        rounds = sum(1 for e in events if e.get("event_type") == "round_end")
        return {"kills": kills, "deaths": deaths, "rounds": rounds}
