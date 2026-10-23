"""外设配置 / AI 推荐 / 商品推荐路由。"""
from __future__ import annotations

from fastapi import APIRouter, Query

import database
from ai_gear_advisor import generate_recommendation, get_products
from models import (
    GearConfig,
    GearConfigUpdate,
    GearRecommendationItem,
    GearRecommendationResponse,
    ProductItem,
    ProductListResponse,
    VolumeReport,
    PerfMetricReport,
    PerfMetricItem,
    PerfLatestResponse,
)

router = APIRouter()


@router.get("/gear/config", response_model=GearConfig)
def get_gear_config() -> GearConfig:
    """获取当前外设配置。"""
    config = database.get_gear_config()
    # 计算 eDPI
    config["edpi"] = round(config.get("mouse_dpi", 800) * config.get("sensitivity", 2.0), 1)
    return GearConfig(**config)


@router.put("/gear/config", response_model=GearConfig)
def update_gear_config(payload: GearConfigUpdate) -> GearConfig:
    """更新外设配置。"""
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if fields:
        database.update_gear_config(**fields)
    config = database.get_gear_config()
    # 如果 DPI 或灵敏度变了，更新 eDPI
    config["edpi"] = round(config.get("mouse_dpi", 800) * config.get("sensitivity", 2.0), 1)
    return GearConfig(**config)


@router.post("/gear/recommend", response_model=GearRecommendationResponse)
def get_gear_recommendation() -> GearRecommendationResponse:
    """AI 推荐外设配置。"""
    config = database.get_gear_config()
    result = generate_recommendation(config)
    return GearRecommendationResponse(
        config=GearConfig(**result["config"]),
        recommendations=[
            GearRecommendationItem(**r) for r in result["recommendations"]
        ],
        summary=result["summary"],
        edpi_analysis=result["edpi_analysis"],
    )


@router.get("/gear/products", response_model=ProductListResponse)
def get_gear_products(
    category: str = Query("", description="商品分类：mouse/keyboard/headset/mousepad")
) -> ProductListResponse:
    """获取推荐商品列表。"""
    products = get_products(category)
    return ProductListResponse(
        products=[ProductItem(**p) for p in products]
    )


@router.post("/gear/volume", response_model=dict)
def report_volume(payload: VolumeReport) -> dict:
    """Agent 上报当前系统音量。"""
    database.update_gear_config(volume=payload.volume)
    return {"ok": True, "volume": payload.volume}


# ---- 性能监控 ----
@router.post("/gear/perf", response_model=dict)
def report_perf_metric(payload: PerfMetricReport) -> dict:
    """Agent 上报性能指标（延迟/帧率/卡顿）。"""
    metric_id = database.insert_perf_metric(
        metric_type=payload.metric_type,
        value=payload.value,
        detail=payload.detail,
    )
    return {"ok": True, "id": metric_id}


@router.get("/gear/perf/latest", response_model=PerfLatestResponse)
def get_latest_perf() -> PerfLatestResponse:
    """获取每种指标的最新一条记录。"""
    data = database.get_latest_perf()
    return PerfLatestResponse(**data)


@router.get("/gear/perf/history", response_model=list)
def get_perf_history(
    metric_type: str = Query("", description="指标类型：latency/fps/stutter"),
    limit: int = Query(60, description="返回条数"),
) -> list:
    """获取性能指标历史记录。"""
    return database.get_perf_metrics(metric_type, limit)
