"""AI 复盘生成引擎。

基于比赛事件数据，通过规则分析 + 模板生成比赛复盘报告。
如果配置了 LLM API，则调用 LLM 增强文本输出。

复盘内容：
- MVP：全场最佳表现描述
- 最大失误：关键失误分析
- 最佳操作：高光时刻（含武器信息）
- 死亡原因：死亡模式分析（含武器/护甲信息）
- 武器使用：击杀武器分布分析
- 经济分析：经济策略评估
- 购买建议：基于经济和武器配置的购买建议
- AI点评：综合评价与建议
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import database

logger = logging.getLogger(__name__)


def _group_events_by_round(events: List[dict]) -> Dict[int, List[dict]]:
    """将事件按回合分组。"""
    rounds: Dict[int, List[dict]] = {}
    for e in events:
        rn = e.get("round_number") or 0
        rounds.setdefault(rn, []).append(e)
    return rounds


def _count_kills_per_round(events: List[dict]) -> Dict[int, int]:
    """统计每回合击杀数。"""
    kills_per_round: Dict[int, int] = {}
    for e in events:
        if e.get("event_type") == "kill":
            rn = e.get("round_number") or 0
            kills_per_round[rn] = kills_per_round.get(rn, 0) + 1
    return kills_per_round


def _count_deaths_per_round(events: List[dict]) -> Dict[int, int]:
    """统计每回合死亡（每回合最多 1 次）。"""
    deaths_per_round: Dict[int, int] = {}
    for e in events:
        if e.get("event_type") == "death":
            rn = e.get("round_number") or 0
            deaths_per_round[rn] = 1
    return deaths_per_round


def _get_round_results(events: List[dict]) -> List[dict]:
    """获取所有回合结束事件。"""
    return [
        e for e in events if e.get("event_type") == "round_end"
    ]


def _get_round_starts(events: List[dict]) -> List[dict]:
    """获取所有回合开始事件（含经济数据）。"""
    return [
        e for e in events if e.get("event_type") == "round_start"
    ]


def _detect_ace(kills_per_round: Dict[int, int]) -> Optional[int]:
    """检测 ACE 回合（单回合 5 杀）。"""
    for rn, kills in kills_per_round.items():
        if kills >= 5:
            return rn
    return None


def _detect_multi_kills(kills_per_round: Dict[int, int]) -> List[dict]:
    """检测多杀回合（3+ 杀）。"""
    result = []
    for rn, kills in sorted(kills_per_round.items()):
        if kills >= 3:
            label = "ACE" if kills >= 5 else f"{kills}杀"
            result.append({"round": rn, "kills": kills, "label": label})
    return result


def _analyze_economy(round_starts: List[dict]) -> str:
    """分析经济策略。"""
    if not round_starts:
        return "未能获取经济数据。"

    money_list = []
    eco_rounds = 0
    force_rounds = 0
    full_buy_rounds = 0

    for rs in round_starts:
        money = rs.get("data", {}).get("money")
        if money is not None:
            try:
                m = int(money)
                money_list.append(m)
                if m < 2000:
                    eco_rounds += 1
                elif m < 4000:
                    force_rounds += 1
                else:
                    full_buy_rounds += 1
            except (TypeError, ValueError):
                pass

    if not money_list:
        return "未能获取经济数据。"

    avg_money = sum(money_list) / len(money_list)
    total_rounds = len(money_list)

    parts = []
    parts.append(
        f"本局共 {total_rounds} 个回合，平均起手资金 ${int(avg_money)}。"
    )

    if eco_rounds > 0:
        parts.append(f"Eco 回合 {eco_rounds} 次，")
    if force_rounds > 0:
        parts.append(f"半甲/强起 {force_rounds} 次，")
    if full_buy_rounds > 0:
        parts.append(f"全甲全枪 {full_buy_rounds} 次。")

    if avg_money < 3000:
        parts.append("整体经济偏紧，建议合理规划 Eco 节奏，避免连续强起导致经济崩盘。")
    elif avg_money < 5000:
        parts.append("经济状况中等，有部分回合可以全甲全枪。")
    else:
        parts.append("经济状况良好，大部分回合可以保持全甲全枪。")

    return "".join(parts)


def _analyze_deaths(events: List[dict], total_rounds: int) -> str:
    """分析死亡模式（含武器和护甲信息）。"""
    death_events = [e for e in events if e.get("event_type") == "death"]
    if not death_events:
        return "本局无死亡记录（可能数据不完整）。"

    death_rounds = set()
    for e in death_events:
        rn = e.get("round_number") or 0
        death_rounds.add(rn)

    death_count = len(death_rounds)
    if total_rounds > 0:
        survival_rate = (1 - death_count / total_rounds) * 100
    else:
        survival_rate = 0

    parts = []
    parts.append(
        f"本局 {total_rounds} 回合中死亡 {death_count} 次，存活率 {survival_rate:.0f}%。"
    )

    if survival_rate >= 70:
        parts.append("存活能力优秀，走位和意识都很到位。")
    elif survival_rate >= 50:
        parts.append("存活能力中等，注意在关键回合保留经济和位置。")
    else:
        parts.append("死亡次数偏多，建议加强走位意识和预瞄点位管理。")

    # 分析死亡时的武器和护甲情况
    no_armor_deaths = 0
    weapon_deaths: Dict[str, int] = {}
    for e in death_events:
        data = e.get("data", {})
        armor = data.get("armor")
        if armor is not None:
            try:
                if int(armor) == 0:
                    no_armor_deaths += 1
            except (TypeError, ValueError):
                pass
        weapon = data.get("active_weapon_name", "")
        if weapon:
            weapon_deaths[weapon] = weapon_deaths.get(weapon, 0) + 1

    if no_armor_deaths > 0:
        parts.append(
            f"其中 {no_armor_deaths} 次死亡时无护甲，"
            "建议在经济允许时优先购买护甲以提高生存能力。"
        )

    if weapon_deaths:
        top_death_weapon = max(weapon_deaths.items(), key=lambda x: x[1])
        if top_death_weapon[1] >= 2:
            parts.append(
                f"死亡时最常手持 {top_death_weapon[0]}（{top_death_weapon[1]}次），"
                "注意在使用该武器时选择更有利的交战距离和位置。"
            )

    # 分析死亡时所在回合的胜负
    round_ends = _get_round_results(events)
    lost_rounds_with_death = 0
    won_rounds_with_death = 0
    for re in round_ends:
        rn = re.get("round_number") or 0
        if rn in death_rounds:
            win_team = re.get("data", {}).get("win_team", "")
            if win_team == "CT":
                won_rounds_with_death += 1
            elif win_team == "T":
                lost_rounds_with_death += 1

    if lost_rounds_with_death > won_rounds_with_death:
        parts.append(
            f"死亡回合中输了 {lost_rounds_with_death} 次，"
            "说明存活对回合胜负影响较大，减少不必要的死亡可以提升胜率。"
        )

    return "".join(parts)


def _analyze_best_play(events: List[dict]) -> str:
    """分析最佳操作（含武器信息）。"""
    kills_per_round = _count_kills_per_round(events)
    multi_kills = _detect_multi_kills(kills_per_round)
    ace_round = _detect_ace(kills_per_round)

    def _get_round_kill_weapon(rn: int) -> str:
        """获取某回合击杀使用的武器名。"""
        for e in events:
            if e.get("event_type") == "kill" and (e.get("round_number") or 0) == rn:
                w = e.get("data", {}).get("weapon_name", "")
                if w:
                    return w
        return ""

    if ace_round is not None:
        weapon = _get_round_kill_weapon(ace_round)
        w_text = f"（使用 {weapon}）" if weapon else ""
        return (
            f"第 {ace_round} 回合完成 ACE（5杀）{w_text}，"
            "这是本局最亮眼的操作！在高压下连续击杀全部对手，"
            "展现了出色的枪法和心理素质。"
        )

    if multi_kills:
        best = multi_kills[-1]  # 取最高的
        weapon = _get_round_kill_weapon(best["round"])
        w_text = f"（使用 {weapon}）" if weapon else ""
        if best["kills"] >= 4:
            return (
                f"第 {best['round']} 回合拿下 {best['label']}{w_text}，"
                "近乎 ACE 的表现，枪法状态极佳。"
            )
        elif best["kills"] >= 3:
            return (
                f"第 {best['round']} 回合 {best['label']}{w_text}，"
                "在关键回合连续击杀多名对手，为团队打开局面。"
            )

    # 如果没有多杀，找第一个击杀
    kill_events = [e for e in events if e.get("event_type") == "kill"]
    if kill_events:
        first_kill = kill_events[0]
        rn = first_kill.get("round_number", "?")
        weapon = first_kill.get("data", {}).get("weapon_name", "")
        w_text = f"（{weapon}）" if weapon else ""
        return f"第 {rn} 回合拿到首杀{w_text}，为团队创造了人数优势。"

    return "本局未能记录到显著的高光操作（可能数据不完整）。"


def _analyze_mvp(
    match: dict, events: List[dict]
) -> str:
    """分析 MVP。"""
    kills = match.get("kills", 0)
    deaths = match.get("deaths", 0)
    assists = match.get("assists", 0)
    mvps = match.get("mvps", 0)
    score = match.get("score", 0)
    player_name = match.get("player_name", "玩家")
    map_name = match.get("map_name", "未知地图")

    parts = []
    parts.append(f"{player_name} 在 {map_name} 上的表现：")

    if kills > 0 or deaths > 0:
        kd = kills / max(deaths, 1)
        parts.append(f"K/D = {kills}/{deaths} = {kd:.2f}。")
    else:
        parts.append("K/D 数据不完整。")

    if mvps > 0:
        parts.append(f"获得 {mvps} 次 MVP，")

    kills_per_round = _count_kills_per_round(events)
    multi_kills = _detect_multi_kills(kills_per_round)
    if multi_kills:
        parts.append(f"有 {len(multi_kills)} 个多杀回合，")

    ace_round = _detect_ace(kills_per_round)
    if ace_round:
        parts.append(f"包含第 {ace_round} 回合的 ACE。")

    if score > 0:
        parts.append(f"总评分 {score}。")

    return "".join(parts)


def _analyze_mistake(
    events: List[dict], match: dict
) -> str:
    """分析最大失误。"""
    round_ends = _get_round_results(events)
    if not round_ends:
        return "回合数据不完整，无法分析失误。"

    # 连续输掉的回合
    losing_streak = 0
    max_losing_streak = 0
    max_streak_start = 0
    current_streak_start = 0

    for i, re in enumerate(round_ends):
        win_team = re.get("data", {}).get("win_team", "")
        # 假设玩家在 CT 方，win_team == "T" 表示输了
        if win_team == "T":
            if losing_streak == 0:
                current_streak_start = i
            losing_streak += 1
            if losing_streak > max_losing_streak:
                max_losing_streak = losing_streak
                max_streak_start = current_streak_start
        else:
            losing_streak = 0

    parts = []
    if max_losing_streak >= 3:
        start_round = round_ends[max_streak_start].get("round_number", "?")
        parts.append(
            f"第 {start_round} 回合起连续输了 {max_losing_streak} 回合，"
            "这是本局最大的失误区间。"
        )
        parts.append("连续失利可能源于经济管理不当或战术执行不到位，")
        parts.append("建议在连败后及时调整战术，必要时 Eco 重置经济。")
    elif max_losing_streak >= 2:
        start_round = round_ends[max_streak_start].get("round_number", "?")
        parts.append(
            f"第 {start_round} 回合起连续输了 {max_losing_streak} 回合，"
            "注意在连败后调整节奏。"
        )
    else:
        parts.append("没有明显的连败区间，整体节奏控制较好。")

    return "".join(parts)


def _generate_ai_commentary(
    match: dict, events: List[dict]
) -> str:
    """生成 AI 综合点评。"""
    kills = match.get("kills", 0)
    deaths = match.get("deaths", 0)
    assists = match.get("assists", 0)
    mvps = match.get("mvps", 0)
    rounds = match.get("rounds_played", 0)
    score_ct = match.get("score_ct", 0)
    score_t = match.get("score_t", 0)
    map_name = match.get("map_name", "")

    parts = []

    # 整体评价
    if rounds > 0:
        kd = kills / max(deaths, 1)
        if kd >= 2.0:
            parts.append("本局表现非常出色，carry 全场级别的发挥。")
        elif kd >= 1.2:
            parts.append("本局表现稳定，对团队贡献明显。")
        elif kd >= 0.8:
            parts.append("本局表现中规中矩，有提升空间。")
        else:
            parts.append("本局状态不佳，需要调整心态和策略。")

    # 比分分析
    if score_ct > 0 or score_t > 0:
        parts.append(f"最终比分 CT {score_ct} : {score_t} T。")
        if score_ct > score_t:
            parts.append("CT 侧表现更好，")
        elif score_t > score_ct:
            parts.append("T 侧表现更好，")

    # MVP 分析
    if mvps > 0:
        parts.append(f"{mvps} 次 MVP 说明在关键回合发挥了决定性作用。")

    # 建议
    parts.append("建议：")
    if deaths > kills:
        parts.append("减少不必要的激进 push，优先保证存活；")
    if assists > 0 and assists >= kills * 0.5:
        parts.append("助攻数较高，团队配合意识好，继续保持；")
    if rounds > 15:
        parts.append("长局比赛注意体力管理和节奏调整。")

    # 武器使用建议
    kill_events = [e for e in events if e.get("event_type") == "kill"]
    weapon_kills: Dict[str, int] = {}
    for e in kill_events:
        w = e.get("data", {}).get("weapon_name", "")
        if w:
            weapon_kills[w] = weapon_kills.get(w, 0) + 1
    if weapon_kills:
        top_weapon = max(weapon_kills.items(), key=lambda x: x[1])
        if top_weapon[1] >= 3:
            parts.append(f"本局 {top_weapon[0]} 击杀最多，")
            if top_weapon[0] == "AWP":
                parts.append("狙击发挥稳定但一旦阵亡经济压力较大，建议搭配步枪手掩护；")
            elif top_weapon[0] in ("AK-47", "M4A1-S"):
                parts.append("步枪主力武器使用得当，注意控制后坐力和预瞄点位；")
            elif top_weapon[0] in ("Desert Eagle",):
                parts.append("沙鹰击杀效率高，可在 Eco 回合作为翻盘利器；")

    return "".join(parts)


# 主武器集合（用于区分主武器与手枪/道具）
_PRIMARY_WEAPONS_SET = {
    "AK-47", "M4A1-S", "AUG", "SG 553", "AWP", "SSG 08", "SCAR-20", "G3SG1",
    "Galil AR", "FAMAS", "MP9", "MAC-10", "MP7", "MP5-SD", "UMP-45", "P90",
    "PP-Bizon", "Nova", "XM1014", "Sawed-Off", "MAG-7", "M249", "Negev",
}


def _analyze_weapons(events: List[dict]) -> str:
    """分析击杀武器使用分布。"""
    kill_events = [e for e in events if e.get("event_type") == "kill"]
    if not kill_events:
        return "本局未能记录到武器使用数据。"

    weapon_kills: Dict[str, int] = {}
    for e in kill_events:
        data = e.get("data", {})
        weapon = data.get("weapon_name", "")
        if weapon:
            weapon_kills[weapon] = weapon_kills.get(weapon, 0) + 1

    parts = []
    if weapon_kills:
        sorted_weapons = sorted(weapon_kills.items(), key=lambda x: x[1], reverse=True)
        weapon_str = "、".join(f"{w}（{c}次击杀）" for w, c in sorted_weapons[:4])
        parts.append(f"本局击杀武器分布：{weapon_str}。")

        # 主武器偏好分析
        primary_kills = {w: c for w, c in weapon_kills.items() if w in _PRIMARY_WEAPONS_SET}
        if primary_kills:
            top_primary = max(primary_kills.items(), key=lambda x: x[1])
            parts.append(f"主武器击杀最多的是 {top_primary[0]}（{top_primary[1]}次击杀）。")

        # AWP 特殊分析
        awp_kills = weapon_kills.get("AWP", 0)
        if awp_kills > 0:
            total_kills = sum(weapon_kills.values())
            awp_ratio = awp_kills / total_kills * 100
            if awp_ratio >= 50:
                parts.append(f"AWP 击杀占比 {awp_ratio:.0f}%，狙击是主要打法。")
            elif awp_ratio >= 20:
                parts.append(f"AWP 击杀占比 {awp_ratio:.0f}%，兼顾狙击和步枪。")
    else:
        parts.append("本局未能识别到击杀使用的武器（需在 GSI 配置中启用 player_weapons）。")

    return "".join(parts)


def _analyze_purchase_advice(round_starts: List[dict], events: List[dict]) -> str:
    """分析武器购买情况并给出购买建议。"""
    if not round_starts:
        return "未能获取购买数据。"

    rounds_with_armor = 0
    rounds_no_armor = 0
    rounds_with_primary = 0
    rounds_no_primary = 0
    eco_with_deagle = 0
    eco_rounds = 0
    awp_rounds = 0
    low_money_awp = 0

    for rs in round_starts:
        data = rs.get("data", {})
        money = data.get("money")
        weapon_names = data.get("weapon_names", [])
        if not isinstance(weapon_names, list):
            weapon_names = []
        armor = data.get("armor")

        if money is not None:
            try:
                m = int(money)
            except (TypeError, ValueError):
                m = None
        else:
            m = None

        # 护甲分析
        if armor is not None:
            try:
                if int(armor) > 0:
                    rounds_with_armor += 1
                else:
                    rounds_no_armor += 1
            except (TypeError, ValueError):
                pass

        # 主武器分析
        has_primary = any(w in _PRIMARY_WEAPONS_SET for w in weapon_names)
        has_awp = "AWP" in weapon_names
        has_deagle = "Desert Eagle" in weapon_names

        if has_primary:
            rounds_with_primary += 1
        else:
            rounds_no_primary += 1

        if has_awp:
            awp_rounds += 1
            if m is not None and m < 4000:
                low_money_awp += 1

        if m is not None and m < 2000:
            eco_rounds += 1
            if has_deagle:
                eco_with_deagle += 1

    parts = []
    total = len(round_starts)

    # 护甲建议
    if rounds_no_armor > 0:
        armor_ratio = rounds_no_armor / total * 100 if total > 0 else 0
        if armor_ratio >= 30:
            parts.append(
                f"有 {rounds_no_armor} 个回合未购买护甲（占比 {armor_ratio:.0f}%），"
                "护甲能显著降低被击杀概率，建议在有经济时优先购买。"
            )

    # 武器购买建议
    if rounds_no_primary > 0:
        parts.append(f"有 {rounds_no_primary} 个回合未购买主武器，")
        if eco_rounds > 0 and eco_with_deagle == 0:
            parts.append("建议在 Eco 回合购买沙漠之鹰以增加翻盘能力。")
        else:
            parts.append("建议合理规划经济，确保关键回合有足够火力。")

    # AWP 购买风险建议
    if awp_rounds > 0 and low_money_awp > 0:
        parts.append(
            f"有 {low_money_awp} 个回合在经费不足 $4000 的情况下购买了 AWP，"
            "经济不足时购买 AWP 风险较大（一旦阵亡难以重购），"
            "建议改为 AK-47/M4A1-S + 全甲 + 道具的均衡配置。"
        )

    # Eco 策略建议
    if eco_rounds > total * 0.3:
        parts.append(
            f"本局 Eco 回合较多（{eco_rounds} 次），"
            "建议团队同步 Eco，积攒经济后在关键回合全甲全枪一波。"
        )

    if not parts:
        parts.append("购买策略整体合理，经济管理和武器配置无明显问题。")

    return "".join(parts)


def _get_enabled_agent(agent_id: str):
    """若该 AI Agent 已启用且共享 LLM 已配置，返回构建好的 Agent 实例，否则 None。"""
    try:
        cfg = database.load_config()
    except Exception:
        return None
    enabled = cfg.get("ai_agents", {}).get(agent_id, {}).get("enabled", False)
    llm = cfg.get("llm", {})
    if not enabled or not llm.get("api_key") or not llm.get("model"):
        return None
    try:
        from agent.ai_agents import build_agent
        return build_agent(agent_id, llm["api_key"], llm["model"], llm.get("base_url", ""))
    except Exception as e:
        logger.warning("构建 Agent %s 失败: %s", agent_id, e)
        return None


def generate_review(match_id: str) -> dict:
    """为一场比赛生成 AI 复盘报告。

    Args:
        match_id: 比赛 ID

    Returns:
        AI 复盘字典，包含 mvp / biggest_mistake / best_play /
        death_analysis / economy_analysis / weapon_analysis /
        purchase_advice / ai_commentary / sections
    """
    match = database.get_match(match_id)
    if match is None:
        return {}

    events = database.get_match_events(match_id)

    # 统计
    kills_per_round = _count_kills_per_round(events)
    death_rounds = _count_deaths_per_round(events)
    round_ends = _get_round_results(events)
    round_starts = _get_round_starts(events)
    total_rounds = len(round_ends)

    # 更新比赛统计
    total_kills = sum(kills_per_round.values())
    total_deaths = len(death_rounds)
    database.update_match(
        match_id,
        kills=total_kills,
        deaths=total_deaths,
        rounds_played=total_rounds,
    )
    # 重新获取更新后的 match
    match = database.get_match(match_id)

    # 生成各部分
    mvp = _analyze_mvp(match, events)
    biggest_mistake = _analyze_mistake(events, match)
    best_play = _analyze_best_play(events)
    death_analysis = _analyze_deaths(events, total_rounds or len(kills_per_round))
    economy_analysis = _analyze_economy(round_starts)
    weapon_analysis = _analyze_weapons(events)
    purchase_advice = _analyze_purchase_advice(round_starts, events)
    ai_commentary = _generate_ai_commentary(match, events)

    # AI Agent 增强（启用且配置了 Key 时用 LLM 增强，失败回退规则草稿）
    review_agent = _get_enabled_agent("review")
    if review_agent is not None:
        try:
            enhanced = review_agent.invoke({
                "match": match,
                "events": events,
                "draft": {
                    "mvp": mvp,
                    "best_play": best_play,
                    "biggest_mistake": biggest_mistake,
                    "economy_analysis": economy_analysis,
                    "weapon_analysis": weapon_analysis,
                    "purchase_advice": purchase_advice,
                    "ai_commentary": ai_commentary,
                },
            })
            if enhanced and enhanced.strip():
                ai_commentary = enhanced.strip()
        except Exception as e:
            logger.warning("ReviewAgent 增强失败: %s", e)

    death_agent = _get_enabled_agent("death_analyst")
    if death_agent is not None:
        try:
            enhanced_death = death_agent.invoke({
                "match": match,
                "events": events,
                "draft": death_analysis,
            })
            if enhanced_death and enhanced_death.strip():
                death_analysis = enhanced_death.strip()
        except Exception as e:
            logger.warning("DeathAnalystAgent 增强失败: %s", e)

    # 组装 sections（前端按顺序展示）
    sections = [
        {"title": "MVP", "content": mvp, "tag": "mvp", "icon": "crown"},
        {"title": "最佳操作", "content": best_play, "tag": "best_play", "icon": "star"},
        {"title": "最大失误", "content": biggest_mistake, "tag": "mistake", "icon": "alert"},
        {"title": "死亡分析", "content": death_analysis, "tag": "death_analysis", "icon": "skull"},
        {"title": "武器使用", "content": weapon_analysis, "tag": "weapon_analysis", "icon": "crosshair"},
        {"title": "经济分析", "content": economy_analysis, "tag": "economy", "icon": "dollar"},
        {"title": "购买建议", "content": purchase_advice, "tag": "purchase_advice", "icon": "shopping"},
        {"title": "AI 点评", "content": ai_commentary, "tag": "summary", "icon": "brain"},
    ]

    review = {
        "mvp": mvp,
        "biggest_mistake": biggest_mistake,
        "best_play": best_play,
        "death_analysis": death_analysis,
        "economy_analysis": economy_analysis,
        "weapon_analysis": weapon_analysis,
        "purchase_advice": purchase_advice,
        "ai_commentary": ai_commentary,
        "sections": sections,
    }

    # 保存到数据库
    database.save_match_review(match_id, review)

    return review
