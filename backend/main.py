"""FastAPI 入口：挂载路由、WebSocket、CORS、启动服务。"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

# 将项目根目录加入 sys.path，以便后端导入 agent.ai_agents 子包
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import database
import media_database
from config import HOST, PORT
from routers import config as config_router
from routers import events as events_router
from routers import games as games_router
from routers import gear as gear_router
from routers import matches as matches_router
from routers import media as media_router
from routers import stats as stats_router
from routers import agents as agents_router
from state import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gamedie")

app = FastAPI(title="GameDie Backend", version="1.0.0")

# CORS 全开（开发期）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Media 模块自动清理守护线程 ----------------
# 独立 daemon 线程：每 24h 清理一次「未保留且超过配置天数」的片段。
# 任何异常都被吞掉 —— 清理失败不影响主服务。独立性约束 §7.2：本段
# 代码随 media 模块存在，删除 media 模块时连 init_media_db 一起移除即可。
def _media_cleanup_loop() -> None:
    """周期性清理未保留的旧片段。"""
    # 延迟 60s 首次执行，避免与 startup 抢资源
    time.sleep(60)
    while True:
        try:
            settings = media_database.load_media_settings()
            if settings.get("auto_cleanup_enabled", True):
                days = int(settings.get("cleanup_days", 3) or 3)
                from services import clip_service
                result = clip_service.cleanup_temp_clips(days_old=days)
                if result.get("deleted", 0) > 0:
                    logger.info(
                        "Media 自动清理: 删除 %s 个未保留片段（>=%s 天）",
                        result["deleted"], days,
                    )
        except Exception as e:
            logger.warning("Media 自动清理异常（不影响主功能）: %s", e)
        # 24h 一次
        time.sleep(24 * 3600)


@app.on_event("startup")
def on_startup() -> None:
    database.init_db()
    logger.info("数据库初始化完成: %s", database.DB_PATH)
    # Media 模块独立数据库（独立于现有 database，失败不影响主库）
    try:
        media_database.init_media_db()
        logger.info("Media 数据库初始化完成: %s", media_database.MEDIA_DB_PATH)
        # 启动自动清理守护线程（随 media 模块，失败静默）
        t = threading.Thread(
            target=_media_cleanup_loop, daemon=True, name="media-cleanup"
        )
        t.start()
    except Exception as e:
        logger.warning("Media 数据库初始化失败（不影响主功能）: %s", e)


@app.get("/")
def root() -> dict:
    return {"service": "GameDie Backend", "docs": "/docs"}


# ---------------- WebSocket ----------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # 持续读取以维持连接并感知断开；服务端主要推送
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ---------------- 路由挂载（统一前缀 /api） ----------------
app.include_router(config_router.router, prefix="/api")
app.include_router(events_router.router, prefix="/api")
app.include_router(games_router.router, prefix="/api")
app.include_router(gear_router.router, prefix="/api")
app.include_router(matches_router.router, prefix="/api")
app.include_router(stats_router.router, prefix="/api")
app.include_router(agents_router.router, prefix="/api")
# Media 模块独立路由（精彩片段库 + 录屏配置），一行挂载
app.include_router(media_router.router, prefix="/api/media")


if __name__ == "__main__":
    import uvicorn

    logger.info("GameDie Backend 启动中 → http://%s:%s", HOST, PORT)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
