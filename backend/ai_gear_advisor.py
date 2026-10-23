"""AI 外设配置推荐引擎。

根据游戏类型、打法风格、段位推荐最优的鼠标 DPI、灵敏度、
键盘触发距离、耳机音量等设置，并输出推荐商品列表。

推荐逻辑基于 CS 职业选手的常用配置数据：
- 职业选手 eDPI 范围：400~1600（大多数集中在 800~1200）
- 低 eDPI 适合精准瞄头，高 eDPI 适合快速转身
- entry fragger 倾向高灵敏度，AWPer 倾向低灵敏度
"""
from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# 职业选手参考配置（eDPI = DPI × sensitivity）
PRO_REFERENCE = {
    "s1mple": {"dpi": 400, "sens": 3.09, "edpi": 1236, "playstyle": "awp"},
    "ZywOo": {"dpi": 400, "sens": 2.0, "edpi": 800, "playstyle": "awp"},
    "NiKo": {"dpi": 400, "sens": 1.45, "edpi": 580, "playstyle": "rifle"},
    "dev1ce": {"dpi": 400, "sens": 2.0, "edpi": 800, "playstyle": "awp"},
    "electroNic": {"dpi": 400, "sens": 2.0, "edpi": 800, "playstyle": "rifle"},
    "b1t": {"dpi": 400, "sens": 1.75, "edpi": 700, "playstyle": "rifle"},
    "ropz": {"dpi": 400, "sens": 2.0, "edpi": 800, "playstyle": "lurk"},
    "Ax1Le": {"dpi": 400, "sens": 1.4, "edpi": 560, "playstyle": "rifle"},
}

# 按段位的推荐 eDPI 范围
RANK_EDPI_RANGE = {
    "silver": (1200, 2000),      # 新手：偏高，方便转身
    "gold": (800, 1400),          # 中端：适中
    "dmg": (700, 1200),           # 进阶
    "le": (600, 1000),            # 高级
    "global": (400, 900),         # 大地球：精准为主
}

# 按打法的 eDPI 偏移
PLAYSTYLE_OFFSET = {
    "aggressive": 200,   # 突破手：偏高
    "balanced": 0,       # 均衡
    "defensive": -150,   # 狙手/防守：偏低
    "support": -100,     # 辅助：偏低
}

# 按段位的推荐音量
RANK_VOLUME = {
    "silver": 60,
    "gold": 55,
    "dmg": 50,
    "le": 45,
    "global": 40,
}

# 按打法的键盘触发距离推荐（mm）
PLAYSTYLE_ACTUATION = {
    "aggressive": 1.2,   # 快速触发
    "balanced": 2.0,
    "defensive": 2.5,     # 稳健，防误触
    "support": 2.0,
}

# 推荐商品目录
PRODUCTS = [
    {
        "id": "mouse-logitech-gprox",
        "name": "G PRO X Superlight 2",
        "brand": "Logitech G",
        "category": "mouse",
        "price": "¥899",
        "tag": "职业选手同款",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Logitech%20G%20PRO%20X%20Superlight%202%20wireless%20gaming%20mouse%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "60g 超轻量无线，职业赛场使用率最高",
    },
    {
        "id": "mouse-razer-viper",
        "name": "Razer Viper V3 Pro",
        "brand": "Razer",
        "category": "mouse",
        "price": "¥1199",
        "tag": "热门",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Razer%20Viper%20V3%20Pro%20wireless%20gaming%20mouse%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "54g 极轻机身，35000DPI 传感器",
    },
    {
        "id": "keyboard-wooting-60he",
        "name": "Wooting 60HE",
        "brand": "Wooting",
        "category": "keyboard",
        "price": "¥1899",
        "tag": "职业选手同款",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Wooting%2060HE%20magnetic%20gaming%20keyboard%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "磁轴可调触发距离 0.1~4.0mm，CS 职业首选",
    },
    {
        "id": "keyboard-razer-huntsman",
        "name": "Razer Huntsman V3 Pro",
        "brand": "Razer",
        "category": "keyboard",
        "price": "¥1599",
        "tag": "性价比",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Razer%20Huntsman%20V3%20Pro%20analog%20gaming%20keyboard%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "模拟光轴，可调触发点，适合 FPS",
    },
    {
        "id": "headset-hyperx-cloud3",
        "name": "HyperX Cloud III",
        "brand": "HyperX",
        "category": "headset",
        "price": "¥599",
        "tag": "热门",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=HyperX%20Cloud%20III%20gaming%20headset%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "53mm 驱动单元，金属框架，CS 选手常用",
    },
    {
        "id": "headset-logitech-gprox",
        "name": "G PRO X 2",
        "brand": "Logitech G",
        "category": "headset",
        "price": "¥999",
        "tag": "职业选手同款",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Logitech%20G%20PRO%20X%202%20gaming%20headset%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "PRO-G 50mm 驱动单元，被动降噪",
    },
    {
        "id": "mousepad-artisan-zero",
        "name": "Artisan Zero Mid",
        "brand": "Artisan",
        "category": "mousepad",
        "price": "¥399",
        "tag": "热门",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Artisan%20Zero%20gaming%20mousepad%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "布面控制型，职业选手首选鼠标垫",
    },
    {
        "id": "mousepad-logitech-g640",
        "name": "G640",
        "brand": "Logitech G",
        "category": "mousepad",
        "price": "¥199",
        "tag": "性价比",
        "image": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Logitech%20G640%20gaming%20mousepad%20black%20minimalist%20product%20photo%20on%20dark%20background&image_size=square",
        "url": "#",
        "desc": "中等摩擦布面，稳定顺滑",
    },
]


def _get_enabled_gear_agent():
    """若外设推荐 Agent 已启用且共享 LLM 已配置，返回构建好的 Agent 实例，否则 None。"""
    try:
        import database
        cfg = database.load_config()
    except Exception:
        return None
    enabled = cfg.get("ai_agents", {}).get("gear_advisor", {}).get("enabled", False)
    llm = cfg.get("llm", {})
    if not enabled or not llm.get("api_key") or not llm.get("model"):
        return None
    try:
        from agent.ai_agents import build_agent
        return build_agent("gear_advisor", llm["api_key"], llm["model"], llm.get("base_url", ""))
    except Exception as e:
        logger.warning("构建 GearAdvisorAgent 失败: %s", e)
        return None


def generate_recommendation(config: dict) -> dict:
    """根据当前配置生成 AI 推荐。

    Args:
        config: 当前外设配置字典

    Returns:
        {"config":..., "recommendations":[...], "summary":..., "edpi_analysis":...}
    """
    playstyle = config.get("playstyle", "balanced")
    rank = config.get("rank", "gold")
    current_dpi = config.get("mouse_dpi", 800)
    current_sens = config.get("sensitivity", 2.0)
    current_edpi = round(current_dpi * current_sens, 1)
    current_volume = config.get("volume", 50)
    current_actuation = config.get("keyboard_actuation", 2.0)

    recommendations: List[Dict] = []

    # === eDPI 推荐 ===
    edpi_range = RANK_EDPI_RANGE.get(rank, (800, 1400))
    offset = PLAYSTYLE_OFFSET.get(playstyle, 0)
    target_edpi_low = max(300, edpi_range[0] + offset)
    target_edpi_high = edpi_range[1] + offset
    target_edpi_mid = (target_edpi_low + target_edpi_high) // 2

    # 推荐 DPI + 灵敏度组合（优先 400 或 800 DPI）
    if target_edpi_mid <= 800:
        rec_dpi, rec_sens = 400, round(target_edpi_mid / 400, 2)
    elif target_edpi_mid <= 1600:
        rec_dpi, rec_sens = 800, round(target_edpi_mid / 800, 2)
    else:
        rec_dpi, rec_sens = 1600, round(target_edpi_mid / 1600, 2)

    rec_edpi = round(rec_dpi * rec_sens, 1)

    if abs(current_edpi - rec_edpi) > 50:
        edpi_reason = (
            f"你的 eDPI 为 {current_edpi}，"
            f"推荐范围 {target_edpi_low}~{target_edpi_high}（{rank} 段位 + {playstyle} 风格）。"
            f"参考职业选手：NiKo eDPI 580、s1mple eDPI 1236。"
        )
        recommendations.append({
            "label": "鼠标 DPI × 灵敏度",
            "current": f"{current_dpi} × {current_sens} = eDPI {current_edpi}",
            "recommended": f"{rec_dpi} × {rec_sens} = eDPI {rec_edpi}",
            "reason": edpi_reason,
            "icon": "mouse",
        })

    # === 回报率推荐 ===
    current_polling = config.get("mouse_polling_rate", 1000)
    if current_polling < 1000:
        recommendations.append({
            "label": "鼠标回报率",
            "current": f"{current_polling} Hz",
            "recommended": "1000 Hz",
            "reason": "1000Hz 回报率可将输入延迟降至 1ms，对 FPS 游戏至关重要。",
            "icon": "refresh",
        })

    # === 音量推荐 ===
    rec_volume = RANK_VOLUME.get(rank, 50)
    if abs(current_volume - rec_volume) >= 10:
        vol_reason = (
            f"当前音量 {current_volume}%，"
            f"推荐 {rec_volume}%（{rank} 段位标准）。"
            f"音量过高可能导致疲劳，过低会漏听脚步声。"
        )
        recommendations.append({
            "label": "耳机音量",
            "current": f"{current_volume}%",
            "recommended": f"{rec_volume}%",
            "reason": vol_reason,
            "icon": "volume",
        })

    # === 键盘触发距离推荐 ===
    rec_actuation = PLAYSTYLE_ACTUATION.get(playstyle, 2.0)
    if abs(current_actuation - rec_actuation) >= 0.5:
        act_reason = (
            f"当前触发距离 {current_actuation}mm，"
            f"推荐 {rec_actuation}mm（{playstyle} 风格）。"
            f"突破手建议短触发快速移动，狙手建议长触发防误触。"
        )
        recommendations.append({
            "label": "键盘触发距离",
            "current": f"{current_actuation}mm",
            "recommended": f"{rec_actuation}mm",
            "reason": act_reason,
            "icon": "keyboard",
        })

    # === eDPI 分析 ===
    if current_edpi > 2000:
        edpi_analysis = (
            f"你的 eDPI {current_edpi} 偏高，"
            "鼠标移动幅度大但精准度下降。"
            "建议降低 DPI 或灵敏度，练习用手臂大动作 + 手腕微调的控制方式。"
        )
    elif current_edpi < 400:
        edpi_analysis = (
            f"你的 eDPI {current_edpi} 很低，"
            "精准度很高但需要更大的鼠标垫和手臂移动空间。"
            "适合 AWP 选手，步枪手可能需要适当提高。"
        )
    else:
        edpi_analysis = (
            f"你的 eDPI {current_edpi} 在合理范围内。"
            f"职业选手常见区间为 400~1600，你的设置接近主流配置。"
        )

    # === 总结 ===
    if not recommendations:
        summary = "当前配置已经非常合理，无需大幅调整。继续保持练习即可。"
    else:
        summary = (
            f"基于你的 {rank} 段位和 {playstyle} 打法风格，"
            f"AI 推荐了 {len(recommendations)} 项配置优化。"
            "调整后建议先在死斗模式适应 10-15 分钟再进入竞技。"
        )

    # AI Agent 增强（启用且配置了 Key 时用 LLM 增强总结，失败回退规则）
    gear_agent = _get_enabled_gear_agent()
    if gear_agent is not None:
        try:
            enhanced = gear_agent.invoke({
                "config": config,
                "summary": summary,
                "edpi_analysis": edpi_analysis,
            })
            if enhanced and enhanced.strip():
                summary = enhanced.strip()
        except Exception as e:
            logger.warning("GearAdvisorAgent 增强失败: %s", e)

    # 更新 config 中的 eDPI
    config["edpi"] = current_edpi

    return {
        "config": config,
        "recommendations": recommendations,
        "summary": summary,
        "edpi_analysis": edpi_analysis,
    }


def get_products(category: str = "") -> list:
    """获取推荐商品列表。

    Args:
        category: 商品分类筛选，空字符串返回全部
    """
    if not category or category == "all":
        return PRODUCTS
    return [p for p in PRODUCTS if p["category"] == category]
